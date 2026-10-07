"""Check a deployed copy of the site from the outside (ticket #35). Run it against the Pages
project's own address before djazair.dev points at it, and against djazair.dev after:

    python3 site/tools/smoke.py https://<project>.pages.dev
    python3 site/tools/smoke.py https://djazair.dev

It reads the sitemap the site publishes and checks that:

- every page in it answers 200 as HTML, in the language its address says, and isn't hidden
  from search engines;
- every link on those pages to the site itself answers 200: other pages, downloads, the
  press kit, fonts and scripts;
- the share images are PNG files, the press kit is a zip, the root page sends readers to
  /en/ or /ar/, robots.txt names the sitemap, and a missing page gets the site's 404 page;
- the chart embeds the Index pages link to answer, dark and light;
- when Cloudflare answers, the headers from site/dist/_headers are there (caching, CORS for
  the data and charts, nosniff), and only the chart embeds can be framed by other sites;
- on djazair.dev itself, http:// moves to https://.

Problems are listed, and the exit status is 1 if there is one. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

CANONICAL = 'https://djazair.dev'      # the address the sitemap and share tags use
AGENT = 'djazair.dev smoke check'
SITEMAP = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
LINK_TAGS = ('a', 'link', 'script', 'img', 'source')
LABELS = {'sitemap': 'page in the sitemap|pages in the sitemap', 'page': 'other page|other pages',
          'embed': 'chart embed|chart embeds', 'file': 'file|files', 'zip': 'zip file|zip files',
          'image': 'share image|share images'}
EMBED = re.compile(r'/(en|ar)/embed/[^/]+/')      # a chart's embed page; its light version is light/ under it


class Answer(NamedTuple):
    url: str           # where the request ended, after redirects
    status: int        # 0 when nothing answered
    headers: dict      # lower-case names
    body: bytes
    error: str = ''


def fetch(url: str, timeout: float = 30, tries: int = 2) -> Answer:
    """GET ``url``, following redirects. A request that gets no answer is tried again once."""
    request = Request(url, headers={'User-Agent': AGENT, 'Accept-Encoding': 'identity'})
    for attempt in range(tries):
        try:
            with urlopen(request, timeout=timeout) as r:
                return Answer(r.geturl(), r.status, {k.lower(): v for k, v in r.headers.items()}, r.read())
        except HTTPError as e:
            with e:
                return Answer(url, e.code, {k.lower(): v for k, v in e.headers.items()}, e.read())
        except (URLError, OSError) as e:          # no answer: DNS, refused, reset, timed out
            error = str(getattr(e, 'reason', e))
            time.sleep(1)
    return Answer(url, 0, {}, b'', error)


class Page(HTMLParser):
    """What the checks read from a page: its language, meta tags and links."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.lang, self.title, self.meta, self.links = None, '', {}, []
        self._in_title = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = a.get('lang')
        elif tag == 'title':
            self._in_title = True
        elif tag == 'meta' and (a.get('property') or a.get('name')):
            self.meta[a.get('property') or a.get('name')] = a.get('content') or ''
        if tag in LINK_TAGS:
            self.links += [a[name] for name in ('href', 'src') if a.get(name)]

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def frame_ancestors(csp: str) -> list:
    """The frame-ancestors sources of each policy in a Content-Security-Policy header (Cloudflare
    joins the policies of several _headers rules with commas, and browsers enforce them all)."""
    found = []
    for policy in csp.split(','):
        for directive in policy.split(';'):
            name, _, sources = directive.strip().partition(' ')
            if name.lower() == 'frame-ancestors':
                found.append(sources.split())
    return found


class Smoke:
    def __init__(self, base: str, workers: int = 8):
        self.base = base.rstrip('/')
        self.workers = workers
        self.problems: list = []       # (level, text): level is 'FAIL' or 'warn'
        self.notes: list = []
        self.counts: dict = {}         # how many of each kind in LABELS were checked
        self.cloudflare = False

    # ------------------------------------------------------------ helpers
    def fail(self, text: str):
        self.problems.append(('FAIL', text))

    def warn(self, text: str):
        self.problems.append(('warn', text))

    def local(self, link: str, page: str):
        """The address to check for ``link`` on ``page``, or None if it leads off the site."""
        url = urljoin(page, link)
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https'):
            return None
        origin = f'{parts.scheme}://{parts.netloc}'
        if origin == CANONICAL:                   # the site's own absolute links
            parts = urlsplit(self.base + url[len(CANONICAL):])
        elif origin != self.base:
            return None
        return urlunsplit(parts._replace(fragment=''))

    def path(self, url: str) -> str:
        return url[len(self.base):] or '/'

    def fetch_all(self, urls) -> dict:
        urls = sorted(set(urls))
        with ThreadPoolExecutor(self.workers) as pool:
            return dict(zip(urls, pool.map(fetch, urls)))

    def answered(self, answer: Answer, what: str, status: int = 200) -> bool:
        if 'cloudflare' in answer.headers.get('server', '').lower():
            self.cloudflare = True
        if answer.status == status:
            return True
        found = f'answered {answer.status}' if answer.status else f'did not answer ({answer.error})'
        self.fail(f'{what} {found}, not {status}')
        return False

    # ------------------------------------------------------------ the checks
    def run(self) -> 'Smoke':
        sitemap = fetch(self.base + '/sitemap.xml')
        if not self.answered(sitemap, '/sitemap.xml'):
            return self
        try:
            locs = [loc.text.strip() for loc in ET.fromstring(sitemap.body).iter(SITEMAP + 'loc')]
        except ET.ParseError as e:
            self.fail(f'/sitemap.xml is not valid XML ({e})')
            return self
        pages = self.fetch_all(self.local(loc, self.base + '/') for loc in locs)
        self.counts['sitemap'] = len(pages)
        links, images = set(), set()
        for url, answer in pages.items():
            path = self.path(url)
            if not self.answered(answer, path):
                continue
            page = self.html(path, answer)
            if page is None:
                self.fail(f'{path} is not served as HTML ({answer.headers.get("content-type")})')
                continue
            if 'noindex' in page.meta.get('robots', ''):
                self.fail(f'{path} is in the sitemap but asks search engines not to index it')
            if 'noindex' in answer.headers.get('x-robots-tag', ''):
                hidden = f'{path} is sent with "X-Robots-Tag: {answer.headers["x-robots-tag"]}"'
                if self.base == CANONICAL:
                    self.fail(hidden)
                elif not self.notes:      # Cloudflare hides preview addresses from search engines
                    self.notes.append(f'this address is hidden from search engines, as Cloudflare does for previews ({hidden}).')
            if path == '/':
                self.check_root(answer, page)
            image = page.meta.get('og:image')
            if image:
                images.add(self.local(image, url) or image)
            else:
                self.fail(f'{path} has no share image (og:image)')
            links |= self.links(page, url)
        self.check_links(links - images, seen=set(pages) | images)
        self.check_images(images)
        self.check_robots()
        self.check_missing()
        if self.base == CANONICAL:
            self.check_https()
        return self

    def html(self, path: str, answer: Answer):
        """The page in ``answer``, after the checks every page gets; None if it isn't HTML."""
        if not answer.headers.get('content-type', '').startswith('text/html'):
            return None
        page = Page(answer.body.decode('utf-8', 'replace'))
        lang = path.strip('/').split('/')[0]
        if lang in ('en', 'ar') and page.lang != lang:
            self.fail(f'{path} says it is in {page.lang!r}, not {lang!r}')
        self.check_headers(path, answer)
        return page

    def links(self, page: Page, url: str) -> set:
        return {target for target in (self.local(link, url) for link in page.links) if target}

    def check_root(self, answer: Answer, page: Page):
        text = answer.body.decode('utf-8', 'replace')
        if 'location.replace' not in text:
            self.fail('/ does not send readers to their language')
        for lang in ('en', 'ar'):
            if f'/{lang}/' not in page.links:
                self.fail(f'/ has no link to /{lang}/ for readers without JavaScript')

    def check_links(self, links: set, seen: set):
        """Every link to the site answers; pages found this way (a report still in draft, which
        stays out of the sitemap) are followed in turn."""
        while links - seen:
            answers = self.fetch_all(links - seen)
            seen |= set(answers)
            links = set()
            for url, answer in answers.items():
                path = self.path(url)
                if not self.answered(answer, path):
                    continue
                page = self.html(path, answer)
                if page is not None:
                    kind = 'embed' if '/embed/' in path else 'page'
                    self.counts[kind] = self.counts.get(kind, 0) + 1
                    links |= self.links(page, url)
                    if EMBED.fullmatch(path):
                        links.add(url + 'light/')
                    continue
                self.counts['file'] = self.counts.get('file', 0) + 1
                if path.endswith('.zip'):
                    self.counts['zip'] = self.counts.get('zip', 0) + 1
                    if not answer.body.startswith(b'PK\x03\x04'):
                        self.fail(f'{path} is not a zip file')
                self.check_headers(path, answer)

    def check_headers(self, path: str, answer: Answer):
        """The headers site/dist/_headers asks Cloudflare for; other servers don't read that file."""
        if not self.cloudflare:
            return
        headers = answer.headers
        if path.startswith('/assets/') and 'immutable' not in headers.get('cache-control', ''):
            self.fail(f'{path} is not cached as immutable (Cache-Control: {headers.get("cache-control")})')
        if path.startswith(('/data/', '/charts/')) and headers.get('access-control-allow-origin') != '*':
            self.fail(f'{path} cannot be read by other sites (no Access-Control-Allow-Origin: *)')
        if headers.get('x-content-type-options') != 'nosniff':
            self.fail(f'{path} lacks X-Content-Type-Options: nosniff')
        if not headers.get('content-type', '').startswith('text/html'):
            return
        framing = headers.get('x-frame-options', '')
        ancestors = frame_ancestors(headers.get('content-security-policy', ''))
        if '/embed/' in path:
            if framing or any(sources != ['*'] for sources in ancestors):
                self.fail(f'{path} cannot be embedded on other sites (X-Frame-Options: {framing or "none"}; '
                          f'frame-ancestors: {" / ".join(" ".join(s) for s in ancestors) or "none"})')
        elif framing.upper() not in ('SAMEORIGIN', 'DENY'):
            self.fail(f'{path} can be framed by any site (no X-Frame-Options: SAMEORIGIN)')

    def check_images(self, images):
        answers = self.fetch_all(images)
        self.counts['image'] = len(answers)
        for url, answer in answers.items():
            if self.answered(answer, f'share image {url}') and not answer.body.startswith(b'\x89PNG'):
                self.fail(f'share image {url} is not a PNG')

    def check_robots(self):
        answer = fetch(self.base + '/robots.txt')
        if self.answered(answer, '/robots.txt') and f'Sitemap: {CANONICAL}/sitemap.xml' not in answer.body.decode('utf-8', 'replace'):
            self.fail('/robots.txt does not name the sitemap')

    def check_missing(self):
        path = f'/smoke-check-{uuid.uuid4().hex[:8]}/'
        answer = fetch(self.base + path)
        if self.answered(answer, f'a missing page ({path})', status=404):
            if 'djazair.dev' not in Page(answer.body.decode('utf-8', 'replace')).title:
                self.fail("a missing page doesn't show the site's own 404 page")

    def check_https(self):
        answer = fetch('http://' + CANONICAL.split('://', 1)[1] + '/')
        if answer.status and not answer.url.startswith('https://'):
            self.warn('http://djazair.dev/ does not move to https:// (Cloudflare: SSL/TLS → Edge Certificates → Always Use HTTPS)')

    # ------------------------------------------------------------ report
    def report(self) -> str:
        found = ', '.join(f'{n} {LABELS[what].split("|")[n != 1]}' for what, n in self.counts.items())
        lines = [f'Checked {self.base}: {found or "nothing"}.']
        if self.counts and not self.cloudflare:
            self.notes.append('not served by Cloudflare, so the response headers were not checked.')
        lines += [f'Note: {note}' for note in self.notes]
        lines += [f'{level:4}  {text}' for level, text in self.problems]
        failures = sum(level == 'FAIL' for level, _ in self.problems)
        lines.append(f'{failures} problem{"s" * (failures != 1)}.' if failures else 'All good.')
        return '\n'.join(lines)

    @property
    def ok(self) -> bool:
        return not any(level == 'FAIL' for level, _ in self.problems)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('base', nargs='?', default=CANONICAL, help='the address to check (default: %(default)s)')
    parser.add_argument('--workers', type=int, default=8, help='requests at a time (default: %(default)s)')
    args = parser.parse_args(argv)
    smoke = Smoke(args.base, args.workers).run()
    print(smoke.report())
    return 0 if smoke.ok else 1


if __name__ == '__main__':
    sys.exit(main())
