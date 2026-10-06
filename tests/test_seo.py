"""Search and sharing metadata (ticket #31): titles and descriptions, canonical and hreflang
links, Open Graph and X card tags with a share image per language, sitemap.xml and robots.txt.
Placeholder pages stay out of search until their ticket is done."""
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
from djsite.config import LANGS, SITE_URL  # noqa: E402
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
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def page(self, url: str) -> str:
        path = url.removeprefix(SITE_URL).lstrip('/')
        return (self.dist / path / 'index.html').read_text('utf-8')

    def indexed(self):
        """(route, lang, url, meta) for every page meant for search."""
        for route in ROUTES:
            for lang in LANGS:
                url = f'{SITE_URL}/{lang}/{route.path}'
                if route.indexed and (route.path == '' or route.path.endswith('/')):
                    m = meta(self.page(url))
                    if m.get('robots') != 'noindex':
                        yield route, lang, url, m

    def test_titles_and_descriptions(self):
        seen = {lang: {'title': set(), 'description': set()} for lang in LANGS}
        count = 0
        for route, lang, url, m in self.indexed():
            count += 1
            with self.subTest(page=url):
                self.assertTrue(10 <= len(m['title']) <= 70, m['title'])
                self.assertTrue(50 <= len(m['description']) <= 160, m['description'])
                for kind in ('title', 'description'):
                    self.assertNotIn(m[kind], seen[lang][kind], f'{kind} used twice')
                    seen[lang][kind].add(m[kind])
        self.assertEqual(count, 18, 'nine pages in two languages')

    def test_canonical_and_language_links(self):
        for route, lang, url, m in self.indexed():
            with self.subTest(page=url):
                self.assertEqual(m['canonical'], url)
                for other in LANGS:
                    self.assertEqual(m[f'alternate:{other}'], f'{SITE_URL}/{other}/{route.path}')
                self.assertEqual(m['alternate:x-default'], f'{SITE_URL}/' if route.key == 'home' else f'{SITE_URL}/en/{route.path}')

    def test_shared_links_show_a_card(self):
        for route, lang, url, m in self.indexed():
            with self.subTest(page=url):
                self.assertEqual(m['og:url'], url)
                self.assertEqual(m['og:title'], m['title'].removesuffix(' · djazair.dev'))
                self.assertEqual(m['og:description'], m['description'])
                self.assertEqual(m['og:locale'], {'en': 'en_GB', 'ar': 'ar_DZ'}[lang])
                self.assertEqual(m['twitter:card'], 'summary_large_image')
                self.assertRegex(m['og:image'], rf'^{re.escape(SITE_URL)}/assets/share-{lang}\.[0-9a-f]{{10}}\.png$')
                image = self.dist / m['og:image'].removeprefix(SITE_URL + '/')
                self.assertEqual(png_size(image), (1200, 630))
                self.assertLess(image.stat().st_size, 300 * 1024)
                self.assertTrue(m['og:image:alt'])
        root = meta((self.dist / 'index.html').read_text('utf-8'))
        self.assertEqual(root['og:url'], f'{SITE_URL}/')
        self.assertIn('/assets/share-en.', root['og:image'])

    def test_placeholders_stay_out_of_search(self):
        for lang in LANGS:
            for path in ('reports/', 'reports/2026-q1/'):
                html = (self.dist / lang / path / 'index.html').read_text('utf-8')
                with self.subTest(page=f'{lang}/{path}'):
                    self.assertIn('<meta name="robots" content="noindex">', html)
                    self.assertNotIn('rel="canonical"', html)
                    self.assertNotIn('og:title', html)
        self.assertIn('<meta name="robots" content="noindex">', (self.dist / 'en' / '404.html').read_text('utf-8'))

    def test_sitemap_lists_both_languages_of_every_page(self):
        tree = ET.parse(self.dist / 'sitemap.xml')
        urls = {u.findtext('s:loc', namespaces=NS): {a.get('hreflang'): a.get('href') for a in u.findall('x:link', NS)}
                for u in tree.getroot().findall('s:url', NS)}
        expected = {url for _, _, url, _ in self.indexed()} | {f'{SITE_URL}/'}
        self.assertEqual(set(urls), expected)
        for loc, alts in urls.items():
            with self.subTest(url=loc):
                self.assertEqual(set(alts), {'en', 'ar', 'x-default'})
                for href in alts.values():
                    self.assertIn(href, urls, 'every alternate is listed too')
                if loc != f'{SITE_URL}/':
                    self.assertEqual(meta(self.page(loc))['canonical'], loc)

    def test_robots_point_to_the_sitemap(self):
        robots = (self.dist / 'robots.txt').read_text('utf-8')
        self.assertIn('User-agent: *\nAllow: /\n', robots)
        self.assertIn(f'Sitemap: {SITE_URL}/sitemap.xml', robots)
        self.assertNotIn('Disallow: /\n', robots)


if __name__ == '__main__':
    unittest.main()
