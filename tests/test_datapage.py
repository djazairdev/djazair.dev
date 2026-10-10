"""Data page (ticket #24): every download link works and matches data/derived/latest, every
chart's data is listed, and the changelog and corrections log are there to link to."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite import data, logs  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import LANGS  # noqa: E402
from djsite.context import Ctx  # noqa: E402
from djsite.fmt import fsize  # noqa: E402
from djsite.markup import Markup  # noqa: E402


class DataPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, quiet=True, published=LANGS)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'data' / 'index.html').read_text('utf-8') for lang in LANGS}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_every_download_link_works_and_matches_the_latest_data(self):
        latest = json.loads((ROOT / 'data' / 'derived' / 'latest.json').read_text('utf-8'))['folder']
        for lang in LANGS:
            links = set(re.findall(r'href="(/(?:data|charts)/[^"#]+)"', self.html[lang]))
            with self.subTest(lang=lang):
                self.assertGreater(len(links), 30)
                for link in links:
                    self.assertTrue((self.dist / link.lstrip('/')).is_file(), link)
                    if link.startswith(f'/data/{latest}/') and link.rsplit('/', 1)[1] in self.data.files:
                        self.assertEqual((self.dist / link.lstrip('/')).read_bytes(),
                                         (ROOT / 'data' / 'derived' / link[len('/data/'):]).read_bytes(), link)

    def test_every_table_is_listed_with_words_in_both_languages(self):
        tables = {f['table'] for f in self.data.files.values() if 'table' in f}
        for lang in LANGS:
            listed = re.findall(r'<li class="tb-row" id="t-(\w+)">', self.html[lang])
            with self.subTest(lang=lang):
                self.assertEqual(set(listed), tables)
                self.assertEqual(listed[:2], ['overview', 'peers'])
                self.assertNotIn('class="untranslated"', self.html[lang])

    def test_every_chart_is_listed(self):
        self.assertIn('home-yoy', self.site.charts)
        self.assertIn('languages-top', self.site.charts)
        self.assertEqual(sum(1 for c in self.site.charts if c.startswith('trends-')), 9)
        for chart_id, c in self.site.charts.items():
            with self.subTest(chart=chart_id):
                self.assertIn(f'href="{c["csv"][0]}"', self.html['en'])
                self.assertTrue((self.dist / c['json'][0].lstrip('/')).is_file())

    def test_country_downloads_keep_measured_data_and_forecasts_separate(self):
        quarter = self.data.quarter.lower()
        measured = f'/data/{quarter}/global-accounts.csv'
        forecast = '/data/octoverse-2025/country-outlook.json'
        for lang in LANGS:
            with self.subTest(lang=lang):
                html = self.html[lang]
                self.assertIn(f'href="{measured}" download', html)
                self.assertIn(f'href="{forecast}" download', html)
                self.assertEqual(html.count('class="data-country-card"'), 2)
        self.assertTrue((self.dist / measured.lstrip('/')).is_file())
        self.assertTrue((self.dist / forecast.lstrip('/')).is_file())
        self.assertIn('No Algeria forecast', self.html['en'])

    def test_explanations_have_unique_deep_links_without_duplicate_logs(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                html = self.html[lang]
                ids = re.findall(r'\bid="([^"]+)"', html)
                self.assertEqual(len(ids), len(set(ids)))
                for anchor in ('sources', 'indicators', 'peer-groups', 'limitations', 'updates'):
                    self.assertIn(f'<details class="data-method" id="{anchor}">', html)
                for anchor in ('accounts', 'languages', 'topics', 'collaboration', 'gdc26'):
                    self.assertIn(f'id="{anchor}"', html)
                self.assertEqual(html.count('id="corrections"'), 1)
                self.assertEqual(html.count('id="changelog"'), 1)

    def test_logs_and_anchors(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                for anchor in ('tables', 'charts', 'addresses', 'changelog', 'corrections', 'licence'):
                    self.assertIn(f'id="{anchor}"', self.html[lang])
        self.assertIn('Innovation Graph release 054c7dbc5275', self.html['en'].replace('</strong> ', ''))
        self.assertIn('No corrections yet.', self.html['en'])
        self.assertIn('Access-Control-Allow-Origin: *', (self.dist / '_headers').read_text('utf-8'))

    def test_a_correction_shows_when_it_was_found_and_fixed(self):
        entries = [{'found': '2026-11-10', 'fixed': '2026-11-12', 'issue': 'https://github.com/djazairdev/djazair.dev/issues/99',
                    'en': 'The **pushes** figure for Q1 2026 was wrong.', 'ar': 'كان رقم **الدفع** خاطئًا.'}]
        ctx = Ctx(self.site, 'en', self.site.routes['data'])
        with mock.patch.object(logs, '_load', lambda name: entries if name == 'corrections.json' else []):
            html = logs.entry_list(ctx, logs.corrections(ctx), 'none')
        self.assertIn('<time datetime="2026-11-12">12 Nov 2026</time>', html)
        self.assertIn('Found 10 Nov 2026 · fixed 12 Nov 2026', html)
        self.assertIn('<strong>pushes</strong>', html)
        self.assertIn('issues/99', html)
        self.assertIsInstance(html, Markup)

    def test_file_sizes(self):
        self.assertEqual([fsize(n) for n in (940, 1133, 12163, 1706235)], ['940 B', '1.1 KB', '12 KB', '1.7 MB'])
        self.assertEqual(fsize(1133, 'ar'), '1,1 KB')


if __name__ == '__main__':
    unittest.main()
