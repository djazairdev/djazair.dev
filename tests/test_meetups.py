"""The meetups page (ticket #43, PRD D11): what a meetup is and how to host one, with links to
founders.coffee, where the meetups are organised, in the page's language; no meetups, dates or
names copied from it; reached from the footer and the sitemap; content/meetups/meetups.json
checked."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite.build import build  # noqa: E402
from djsite.pages import meetups  # noqa: E402
from djsite.pages.meetups import MeetupsError, load  # noqa: E402

DATA = load()


class MeetupsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.html = {lang: (cls.dist / lang / 'meetups' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}
        cls.main = {lang: re.search(r'<main.*?</main>', html, re.S).group(0) for lang, html in cls.html.items()}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_finding_and_hosting_happen_on_founders_coffee_in_the_same_language(self):
        for lang in ('en', 'ar'):
            main = self.main[lang]
            head = re.search(r'<section class="page-head.*?</section>', main, re.S).group(0)
            self.assertIn(f'<a class="btn btn-primary btn-out" href="https://founders.coffee/{lang}/algeria">', head)
            self.assertIn(f'<a class="btn btn-secondary btn-out" href="https://founders.coffee/{lang}/algeria/host/create">', head)
            host = re.search(r'<section class="section section-m" id="host".*?</section>', main, re.S).group(0)
            self.assertEqual(host.count('<li class="step card"><span class="step-n num">'), 3)
            self.assertIn(f'href="https://founders.coffee/{lang}/algeria/host/create"', host)
            outside = sorted(set(re.findall(r'href="(https?://[^"]+)"', main)))
            self.assertEqual(outside, sorted({url for _, l, url in meetups.links(DATA) if l == lang}),
                             'founders.coffee in the page’s language, and nowhere else')

    def test_it_says_founders_coffee_is_another_site(self):
        for lang, words in (('en', ('is a separate site', 'terms of use', 'privacy policy')),
                            ('ar', ('موقع مستقل', 'شروط الاستخدام', 'سياسة الخصوصية'))):
            note = re.search(r'<aside class="callout mt-note" role="note">.*?</aside>', self.main[lang], re.S).group(0)
            for word in words:
                self.assertIn(word, note)
            self.assertIn(f'href="https://founders.coffee/{lang}/privacy"', note)
            self.assertIn(f'href="https://founders.coffee/{lang}/terms"', note)

    def test_it_copies_no_meetups(self):
        """Dates, places and hosts live on founders.coffee, so the page can't go out of date."""
        for lang in ('en', 'ar'):
            self.assertNotIn('<time', self.main[lang])
            self.assertNotRegex(self.main[lang], r'\d{1,2}:\d{2}')

    def test_it_links_to_the_hub_and_the_reports(self):
        for lang in ('en', 'ar'):
            bring = re.search(r'<ul class="mt-bring" role="list">.*?</ul>', self.main[lang], re.S).group(0)
            self.assertEqual(re.findall(r'href="([^"]+)"', bring), [f'/{lang}/hub/', f'/{lang}/reports/'])

    def test_reached_from_the_footer_and_the_sitemap(self):
        sitemap = (self.dist / 'sitemap.xml').read_text()
        for lang in ('en', 'ar'):
            self.assertIn(f'<loc>https://djazair.dev/{lang}/meetups/</loc>', sitemap)
            for page in ('index.html', 'hub/index.html', 'about/index.html'):
                footer = re.search(r'<footer.*?</footer>', (self.dist / lang / page).read_text('utf-8'), re.S).group(0)
                self.assertIn(f'href="/{lang}/meetups/"', footer, page)
        self.assertIn('<title>Meetups · djazair.dev</title>', self.html['en'])
        self.assertIn('<title>اللقاءات · djazair.dev</title>', self.html['ar'])
        self.assertIn('<html lang="ar" dir="rtl">', self.html['ar'])


class TheLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def write(self, change) -> Path:
        data = json.loads(json.dumps(DATA))
        change(data)
        path = self.tmp / 'meetups.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return path

    def test_every_link_in_both_languages(self):
        self.assertEqual(len(meetups.links(DATA)), 8)
        for key, lang, url in meetups.links(DATA):
            self.assertTrue(url.startswith(f'https://founders.coffee/{lang}/'), url)

    def test_mistakes_are_named(self):
        cases = [
            (lambda d: d.pop('title'), 'has no title'),
            (lambda d: d.update(url='http://founders.coffee'), 'url must be an https address'),
            (lambda d: d.update(url='https://founders.coffee/ar/algeria'), 'with no path'),
            (lambda d: d['links'].update(host='/ar/algeria/host/create'), r'links.host must be a path that starts with /\{lang\}/'),
            (lambda d: d['links'].pop('privacy'), r'links.privacy must be a path'),
        ]
        for change, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(MeetupsError, message):
                    load(self.write(change))
        with self.assertRaises(ValueError):
            load(self.write(lambda d: d.update(checked='7 October')))


if __name__ == '__main__':
    unittest.main()
