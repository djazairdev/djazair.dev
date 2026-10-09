"""Open every link the site curates: the translation teams in content/localisation.json
(ticket #40), founders.coffee pages in content/meetups/meetups.json (ticket #43), and public
project contribution guides in content/community-projects.json. A link
works when it answers 200 at the same address with a page whose title names what it should: a
team's language, or Founders Coffee. So a team that moved, closed or turned into a sign-in
page is caught, and so is a founders.coffee page that moved.

    python3 site/tools/links.py                  # check every link
    python3 site/tools/links.py --report FILE    # also write the broken ones as Markdown

A site that turns robots away or doesn't answer (401, 403, 429, 5xx, a timeout) is listed as
not checked, which doesn't fail the run. The exit status is 1 when a link is broken. The Link
check workflow runs this every Monday and opens an issue for broken links. Standard library
only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
from typing import Callable, NamedTuple, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
LIST = ROOT / 'content' / 'localisation.json'
MEETUPS = ROOT / 'content' / 'meetups' / 'meetups.json'
DISCOVERY = ROOT / 'content' / 'community-projects.json'
PAGES = {'localisation': 'https://djazair.dev/en/hub/localisation/', 'meetups': 'https://djazair.dev/en/meetups/', 'projects': 'https://djazair.dev/en/#public-projects-h'}
# Some platforms challenge browser-like agents; this one says what it is.
AGENT = 'djazair.dev link check (+https://github.com/djazairdev/djazair.dev)'
LANGUAGES = {'ar': 'Arabic', 'kab': 'Kabyle', 'zgh': 'Tamazight'}   # what each team's page calls its language
UNCHECKED = (401, 403, 429)


class Answer(NamedTuple):
    url: str          # where the request ended, after redirects
    status: int       # 0 when nothing answered
    title: str = ''
    error: str = ''


class Link(NamedTuple):
    page: str         # the page it is on: localisation or meetups
    name: str         # the team, or the founders.coffee page
    lang: str
    url: str
    expect: str       # what the title of the page it opens must name


class Result(NamedTuple):
    page: str
    team: str
    lang: str
    url: str
    verdict: str      # ok, broken or unchecked
    reason: str = ''


def fetch(url: str, timeout: float = 30) -> Answer:
    """GET ``url`` in English, following redirects, and read the page's title."""
    request = Request(url, headers={'User-Agent': AGENT, 'Accept-Language': 'en', 'Accept-Encoding': 'identity'})
    try:
        with urlopen(request, timeout=timeout) as r:
            return Answer(r.geturl(), r.status, title(r.read(500_000)))
    except HTTPError as e:
        with e:
            return Answer(url, e.code)
    except (URLError, OSError) as e:
        return Answer(url, 0, error=str(getattr(e, 'reason', e)))


def title(body: bytes) -> str:
    found = re.search(rb'<title[^>]*>(.*?)</title>', body, re.S | re.I)
    return ' '.join(unescape(found.group(1).decode('utf-8', 'replace')).split()) if found else ''


def same(a: str, b: str) -> bool:
    return a.split('#')[0].rstrip('/') == b.split('#')[0].rstrip('/')


def verdict(url: str, expect: str, answer: Answer) -> tuple:
    """(``ok``, ``broken`` or ``unchecked``, why). ``expect``: what the page's title must name."""
    if answer.status == 0:
        return 'unchecked', f'no answer ({answer.error})'
    if answer.status in UNCHECKED or answer.status >= 500:
        return 'unchecked', f'answered {answer.status}'
    if answer.status in (404, 410):
        return 'broken', f'not found ({answer.status})'
    if answer.status != 200:
        return 'broken', f'answered {answer.status}'
    if not same(answer.url, url):
        return 'broken', f'now opens {answer.url}'
    if expect.lower() not in answer.title.lower():
        return 'broken', f'the page doesn’t name {expect}: “{answer.title or "no title"}”'
    return 'ok', ''


def curated(localisation: Path = LIST, meetups: Path = MEETUPS, discovery: Path = DISCOVERY) -> list:
    """Every Link the site curates, in the order of the files."""
    teams = json.loads(Path(localisation).read_text('utf-8'))['teams']
    out = [Link('localisation', t['name'], code, url, LANGUAGES[code]) for t in teams for code, url in t['links'].items()]
    m = json.loads(Path(meetups).read_text('utf-8'))
    out += [Link('meetups', f'{m["platform"]}: {key}', lang, m['url'].rstrip('/') + path.replace('{lang}', lang), m['title'])
            for key, path in m['links'].items() for lang in ('en', 'ar')]
    projects = json.loads(Path(discovery).read_text('utf-8'))['projects']
    for p in projects:
        urls = {'https://github.com/' + p['repository'], p['contribute']}
        out += [Link('projects', p['repository'], 'en', url, p['repository']) for url in sorted(urls)]
    return out


def check(links: Optional[list] = None, get: Optional[Callable[[str], Answer]] = None) -> list:
    """A Result for every link (by default, every link the site curates), opened six at a time."""
    get = get or fetch
    links = curated() if links is None else links
    with ThreadPoolExecutor(max_workers=6) as pool:
        answers = list(pool.map(lambda link: get(link.url), links))
    return [Result(link.page, link.name, link.lang, link.url, *verdict(link.url, link.expect, answer))
            for link, answer in zip(links, answers)]


def report(results: list) -> str:
    """The broken links as a Markdown table, for the alert issue."""
    broken = [r for r in results if r.verdict == 'broken']
    rows = ''.join(f'| [{r.page}]({PAGES[r.page]}) | {r.team} | `{r.lang}` | {r.url} | {r.reason.replace("|", "/")} |\n'
                   for r in broken)
    return (f'{len(broken)} of {len(results)} links the site curates are broken:\n\n'
            '| Page | Link to | Language | Address | Problem |\n|---|---|---|---|---|\n' + rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--list', type=Path, default=LIST, help='the translation teams (default: content/localisation.json)')
    parser.add_argument('--meetups', type=Path, default=MEETUPS, help='the meetups links (default: content/meetups/meetups.json)')
    parser.add_argument('--projects', type=Path, default=DISCOVERY, help='public project discovery links')
    parser.add_argument('--report', type=Path, help='write the broken links here as Markdown')
    args = parser.parse_args(argv)
    results = check(curated(args.list, args.meetups, args.projects))
    for r in results:
        print(f'{r.verdict:9} {r.team} · {r.lang}  {r.url}' + (f'  ({r.reason})' if r.reason else ''))
    counts = {v: sum(r.verdict == v for r in results) for v in ('ok', 'broken', 'unchecked')}
    print(f'\n{len(results)} links: {counts["ok"]} work, {counts["broken"]} broken, {counts["unchecked"]} not checked.')
    if args.report and counts['broken']:
        args.report.write_text(report(results), 'utf-8')
    return 1 if counts['broken'] else 0


if __name__ == '__main__':
    sys.exit(main())
