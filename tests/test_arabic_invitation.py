"""Arabic waits for its review (D28, #61): every /ar/ address shows one page that invites people
to translate the site, instead of the draft translation, and nothing else Arabic is published.
English is unchanged, and the search and discovery files name English only."""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite.build import build, main as build_main, output_path  # noqa: E402
from djsite.config import LANGS, PUBLISHED, SITE_URL  # noqa: E402
from djsite.routes import ROUTES  # noqa: E402
from htmlcheck import Doc  # noqa: E402

ISSUE = 'https://github.com/djazairdev/djazair.dev/issues/62'
ARABIC = re.compile(r'[؀-ۿ][؀-ۿ ]*')     # the block holds the harakat and punctuation too
STRINGS = {lang: json.loads((ROOT / 'site' / 'i18n' / f'{lang}.json').read_text('utf-8'))['invite'] for lang in LANGS}


def main(html: str) -> str:
    return re.search(r'<main id="main" tabindex="-1">(.*)</main>', html, re.S).group(1)


def body(html: str) -> str:
    return re.search(r'<body>.*</body>', html, re.S).group(0)


class Invitation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.full = cls.tmp / 'full'
        cls.site = build(cls.dist, quiet=True)
        build(cls.full, quiet=True, published=LANGS)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_arabic_is_not_published(self):
        self.assertEqual(PUBLISHED, ('en',), 'Arabic comes back once #33 signs it off: update this test then')
        self.assertEqual(self.site.published, ('en',))

    def addresses(self) -> dict:
        """/ar/ file -> the English address its invitation links to: every page and chart embed."""
        out = {output_path(self.dist, 'ar', r.path): f'/en/{r.path}' if r.switchable else '/en/' for r in ROUTES}
        for page in (self.dist / 'en' / 'embed').rglob('index.html'):
            rel = page.relative_to(self.dist / 'en').as_posix()
            out[self.dist / 'ar' / rel] = f'/en/{rel.removesuffix("index.html")}'
        return out

    def test_every_arabic_address_serves_the_invitation_and_nothing_else(self):
        addresses = self.addresses()
        self.assertGreater(len(addresses), len(ROUTES), 'the chart embeds too')
        self.assertIn(self.dist / 'ar' / '404.html', addresses, 'unknown /ar/ addresses get it from the nearest 404.html')
        self.assertEqual(sorted(p for p in (self.dist / 'ar').rglob('*') if p.is_file()), sorted(addresses),
                         'no other file under /ar/: no draft page, no index.md')
        allowed = {text for value in STRINGS['ar'].values() for text in ARABIC.findall(value)}
        home = main((self.dist / 'ar' / 'index.html').read_text('utf-8')).replace('href="/en/"', '')
        for path, english in addresses.items():
            html = path.read_text('utf-8')
            doc = Doc(html)
            with self.subTest(page=str(path.relative_to(self.dist))):
                self.assertEqual((doc.html.get('lang'), doc.html.get('dir')), ('ar', 'rtl'))
                self.assertIn('<meta name="robots" content="noindex">', html)
                self.assertFalse([l for l in doc.links if l.get('rel') in ('canonical', 'alternate')], 'no canonical or hreflang')
                self.assertNotIn('property="og:', html, 'no share card')
                self.assertNotIn('application/ld+json', html)
                self.assertFalse(doc.find('div', class_='notice'), 'no draft notice: there is no draft')
                self.assertTrue(doc.find('header', class_='site-header') and doc.find('footer', class_='site-footer'))
                hrefs = [a.get('href') for a in Doc(main(html)).anchors]
                self.assertIn(ISSUE, hrefs)
                self.assertIn(english, hrefs)
                self.assertNotIn('<script', main(html), 'it works without JavaScript')
                # The page's only Arabic is the invitation's own strings: the draft stays in ar.json.
                self.assertEqual(set(ARABIC.findall(main(html))) - allowed, set())
                self.assertEqual(main(html).replace(f'href="{english}"', ''), home, 'the same page, but for its English link')

    def test_arabic_first_then_english(self):
        page = main((self.dist / 'ar' / 'hub' / 'index.html').read_text('utf-8'))
        ar, en = STRINGS['ar'], STRINGS['en']
        self.assertIn(f'<h1>{ar["title"]}</h1>', page)
        self.assertLess(page.index(ar['title']), page.index('<div lang="en" dir="ltr">'))
        english = page[page.index('<div lang="en" dir="ltr">'):]
        for key in ('title', 'text', 'issue', 'english'):
            self.assertIn(en[key], english)
            self.assertIn(ar[key], page[:page.index('<div lang="en" dir="ltr">')])
        self.assertEqual(page.count('href="/en/hub/"'), 2)
        self.assertEqual(page.count(f'href="{ISSUE}"'), 4, 'the #62 link and the button, in each language')

    def test_the_language_switch_leads_to_it(self):
        for route in ROUTES:
            doc = Doc(output_path(self.dist, 'en', route.path).read_text('utf-8'))
            switch = {a['data-lang']: a['href'] for a in doc.find('a') if 'data-lang' in a}
            with self.subTest(route=route.key):
                self.assertEqual(switch['ar'], f'/ar/{route.path}' if route.switchable else '/ar/')
                self.assertTrue(output_path(self.dist, 'ar', switch['ar'].removeprefix('/ar/')).is_file())

    def test_its_links_lead_to_the_english_pages(self):
        """The header and footer would lead from one invitation to another: they go to English."""
        for page in self.addresses():
            doc = Doc(page.read_text('utf-8'))
            with self.subTest(page=page.relative_to(self.dist).as_posix()):
                local = [a['href'] for a in doc.find('a') if a.get('href', '').startswith('/') and 'data-lang' not in a]
                self.assertTrue(local)
                self.assertEqual([h for h in local if not h.startswith('/en/')], [])
                switch = {a['data-lang']: a['href'] for a in doc.find('a') if 'data-lang' in a}
                self.assertTrue(switch['ar'].startswith('/ar/'), 'the switch still names Arabic')

    def test_no_arabic_files_or_signals(self):
        self.assertFalse([path for path in self.site.files if '/ar/' in path], 'no Arabic SVG, embed or press kit')
        self.assertFalse(list((self.dist / 'assets').glob('share-*ar*.png')), 'no Arabic share card')
        self.assertTrue(list((self.full / 'assets').glob('share-*ar*.png')))
        for name in ('sitemap.xml', 'sitemap.txt', 'llms.txt', 'index.html', '_headers'):
            text = (self.dist / name).read_text('utf-8')
            with self.subTest(file=name):
                self.assertNotIn(f'{SITE_URL}/ar/', text)
                self.assertNotIn('hreflang="ar"', text)
                self.assertNotIn('/ar/data/index.md', text)
        for page in (self.dist / 'en').rglob('*.html'):
            html = page.read_text('utf-8')
            with self.subTest(page=str(page.relative_to(self.dist))):
                self.assertNotIn('hreflang="ar" href="https://', html)
                self.assertNotIn('og:locale:alternate', html)
                self.assertNotIn('"inLanguage":["en","ar"]', html)
        self.assertIn('"inLanguage":["en"]', (self.dist / 'en' / 'index.html').read_text('utf-8'))
        self.assertIn('"inLanguage":["en","ar"]', (self.full / 'en' / 'index.html').read_text('utf-8'))

    def test_english_pages_are_unchanged(self):
        """Every English page and file is the same as in a build with Arabic: only the head's
        language links differ."""
        for page in sorted((self.full / 'en').rglob('*')):
            if not page.is_file():
                continue
            ours = self.dist / page.relative_to(self.full)
            with self.subTest(page=str(page.relative_to(self.full))):
                if page.suffix == '.html':
                    self.assertEqual(body(ours.read_text('utf-8')), body(page.read_text('utf-8')))
                else:
                    self.assertEqual(ours.read_bytes(), page.read_bytes())
        for path in sorted(self.site.files):        # downloads, embeds: the same bytes
            with self.subTest(file=path):
                self.assertEqual((self.dist / path.lstrip('/')).read_bytes(), (self.full / path.lstrip('/')).read_bytes())

    def test_translators_can_build_every_language(self):
        out = self.tmp / 'review'
        with contextlib.redirect_stdout(io.StringIO()):
            build_main(['--out', str(out), '--all-languages'])
        self.assertEqual(main((out / 'ar' / 'index.html').read_text('utf-8')), main((self.full / 'ar' / 'index.html').read_text('utf-8')))


if __name__ == '__main__':
    unittest.main()
