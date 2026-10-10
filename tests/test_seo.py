"""Search and sharing metadata (ticket #31): titles and descriptions, canonical and hreflang
links, Open Graph and X card tags with a share image per language, sitemap.xml and robots.txt.
Placeholder pages, report drafts and the invitations to translate (#61) stay out of search."""
import json
import re
import shutil
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite.build import build  # noqa: E402
from djsite.config import LANGS, PUBLISHED, SITE_URL, STATIC_DIR  # noqa: E402
from djsite.reports import all_reports  # noqa: E402
from djsite.routes import ROUTES  # noqa: E402

NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'x': 'http://www.w3.org/1999/xhtml'}


def meta(html: str) -> dict:
    """<meta name|property=... content=...> and <link rel=... href=...> values."""
    out = {}
    for name, value in re.findall(r'<meta (?:name|property)="([^"]+)" content="([^"]*)"', html):
        out.setdefault(name, value)
    for rel, lang, href in re.findall(r'<link rel="(canonical|alternate)"(?: hreflang="([^"]+)")? href="([^"]+)"', html):
        out[f'{rel}:{lang}' if lang else rel] = href
    out['title'] = re.search(r'<title>(.*?)</title>', html).group(1)
    return out


def png_size(path: Path) -> tuple:
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    return struct.unpack('>II', data[16:24])


class Metadata(unittest.TestCase):
    """The site as it ships, in its published languages."""
    PUBLISHED = PUBLISHED

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, quiet=True, published=cls.PUBLISHED)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def page(self, url: str) -> str:
        path = url.removeprefix(SITE_URL).lstrip('/')
        return (self.dist / path / 'index.html').read_text('utf-8')

    def indexed(self):
        """(route, lang, url, meta) for every page meant for search."""
        for route in ROUTES:
            for lang in self.PUBLISHED:
                url = f'{SITE_URL}/{lang}/{route.path}'
                if route.indexed and (route.path == '' or route.path.endswith('/')):
                    m = meta(self.page(url))
                    if m.get('robots') != 'noindex':
                        yield route, lang, url, m

    def test_titles_and_descriptions(self):
        seen = {lang: {'title': set(), 'description': set()} for lang in self.PUBLISHED}
        count = 0
        for route, lang, url, m in self.indexed():
            count += 1
            with self.subTest(page=url):
                self.assertTrue(10 <= len(m['title']) <= 70, m['title'])
                self.assertTrue(50 <= len(m['description']) <= 160, m['description'])
                for kind in ('title', 'description'):
                    self.assertNotIn(m[kind], seen[lang][kind], f'{kind} used twice')
                    seen[lang][kind].add(m[kind])
        self.assertEqual(count, 13 * len(self.PUBLISHED), 'thirteen public pages in each language; retired routes stay out')

    def test_canonical_and_language_links(self):
        for route, lang, url, m in self.indexed():
            with self.subTest(page=url):
                self.assertEqual(m['canonical'], url)
                for other in LANGS:
                    self.assertEqual(m.get(f'alternate:{other}'), f'{SITE_URL}/{other}/{route.path}' if other in self.PUBLISHED else None)
                chooser = route.key == 'home' and len(self.PUBLISHED) > 1     # / chooses only between several languages
                self.assertEqual(m['alternate:x-default'], f'{SITE_URL}/' if chooser else f'{SITE_URL}/en/{route.path}')

    def test_shared_links_show_a_card(self):
        """The site's card, or on Home and the Index pages the card of the quarter they show
        (ticket #42), once site/tools/share.py --release has drawn it."""
        folder = self.site.data.folder.name
        for route, lang, url, m in self.indexed():
            release = (route.key == 'home' or route.section == 'index') and (STATIC_DIR / 'share' / folder / f'{lang}.png').is_file()
            card = f'share-{folder}-{lang}' if release else f'share-{lang}'
            with self.subTest(page=url):
                self.assertEqual(m['og:url'], url)
                self.assertEqual(m['og:title'], m['title'].removesuffix(' · djazair.dev'))
                self.assertEqual(m['og:description'], m['description'])
                self.assertEqual(m['og:locale'], {'en': 'en_GB', 'ar': 'ar_DZ'}[lang])
                self.assertEqual(m.get('og:locale:alternate'), {'en': 'ar_DZ', 'ar': 'en_GB'}[lang] if len(self.PUBLISHED) > 1 else None)
                self.assertEqual(m['twitter:card'], 'summary_large_image')
                self.assertRegex(m['og:image'], rf'^{re.escape(SITE_URL)}/assets/{card}\.[0-9a-f]{{10}}\.png$')
                image = self.dist / m['og:image'].removeprefix(SITE_URL + '/')
                self.assertEqual(png_size(image), (1200, 630))
                self.assertLess(image.stat().st_size, 300 * 1024)
                self.assertTrue(m['og:image:alt'])
                if release:
                    self.assertRegex(m['og:image:alt'], r'(Q\d \d{4}|الربع .+ \d{4}): [\d,.]+ ')
        root = meta((self.dist / 'index.html').read_text('utf-8'))
        self.assertEqual(root['og:url'], f'{SITE_URL}/')
        self.assertIn('/assets/share-en.', root['og:image'])

    def test_removed_routes_stay_out_of_output_and_search(self):
        sitemap = (self.dist / 'sitemap.xml').read_text('utf-8')
        for lang in LANGS:
            for route in ('reports', 'methodology'):
                self.assertFalse((self.dist / lang / route).exists())
                self.assertNotIn(f'/{lang}/{route}/', sitemap)
        self.assertFalse((self.dist / 'reports').exists(), 'no public report press kits')
        self.assertIn('<meta name="robots" content="noindex">', (self.dist / 'en' / '404.html').read_text('utf-8'))

    def test_sitemap_lists_every_published_language_of_every_page(self):
        tree = ET.parse(self.dist / 'sitemap.xml')
        urls = {u.findtext('s:loc', namespaces=NS): {a.get('hreflang'): a.get('href') for a in u.findall('x:link', NS)}
                for u in tree.getroot().findall('s:url', NS)}
        expected = {url for _, _, url, _ in self.indexed()} | ({f'{SITE_URL}/'} if len(self.PUBLISHED) > 1 else set())
        self.assertEqual(set(urls), expected)
        for loc, alts in urls.items():
            with self.subTest(url=loc):
                self.assertEqual(set(alts), {*self.PUBLISHED, 'x-default'})
                for href in alts.values():
                    self.assertIn(href, urls, 'every alternate is listed too')
                if loc != f'{SITE_URL}/':
                    self.assertEqual(meta(self.page(loc))['canonical'], loc)

    def test_sitemap_dates_say_when_the_content_changed(self):
        dates = {u.findtext('s:loc', namespaces=NS): u.findtext('s:lastmod', namespaces=NS)
                 for u in ET.parse(self.dist / 'sitemap.xml').getroot().findall('s:url', NS)}
        release = self.site.data.release_date
        for route, lang, url, _ in self.indexed():
            with self.subTest(page=url):
                if route.section == 'index':
                    self.assertEqual(dates[url], release)
                elif route.key in ('home', 'data'):
                    self.assertGreaterEqual(dates[url], release)
                elif route.key in ('about', 'meetups', 'localisation'):
                    self.assertIsNone(dates[url], 'no date rather than one that changes with every build')

    def test_redirects(self):
        rules = [line.split() for line in (self.dist / '_redirects').read_text('utf-8').splitlines() if line and not line.startswith('#')]
        expected = [[f'/{lang}/index', f'/{lang}/index/', '301'] for lang in LANGS]
        if len(self.PUBLISHED) == 1:
            expected.insert(0, ['/', f'/{self.PUBLISHED[0]}/', '301'])
        self.assertEqual(rules, expected)

    def test_the_organisation_has_a_logo_and_its_profiles(self):
        found = re.search(r'<script type="application/ld\+json">(.*?)</script>', self.page(f'{SITE_URL}/en/')).group(1)
        org = next(g for g in json.loads(found)['@graph'] if g['@type'] == 'Organization')
        self.assertEqual(org['logo']['url'], f'{SITE_URL}/logo.png')
        self.assertEqual(png_size(self.dist / 'logo.png'), (org['logo']['width'], org['logo']['height']))
        self.assertGreaterEqual(org['logo']['width'], 112, "Google's minimum")
        self.assertEqual(org['sameAs'], ['https://github.com/djazairdev', 'https://x.com/djazairdev', 'https://www.facebook.com/djazairdev'])

    def test_robots_point_to_the_sitemap(self):
        robots = (self.dist / 'robots.txt').read_text('utf-8')
        self.assertIn('User-agent: *\nAllow: /\n', robots)
        self.assertIn(f'Sitemap: {SITE_URL}/sitemap.xml', robots)
        self.assertNotIn('Disallow: /\n', robots)


class MetadataWithArabic(Metadata):
    """The same checks with the Arabic pages built, as they will be once reviewed."""
    PUBLISHED = LANGS


if __name__ == '__main__':
    unittest.main()
