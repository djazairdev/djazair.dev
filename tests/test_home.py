"""Home (ticket #18): numbers from the derived data, editorial claims checked against it, and
the ticker's counter maths."""
import json
import math
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite import data, editorial  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.fmt import fint, fpct, rank_text  # noqa: E402
from djsite.pages import home  # noqa: E402
from htmlcheck import Doc, stylesheet  # noqa: E402

BASELINE = '2026-Q1'           # the quarter the hand-checked expectations below describe


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html))


class Editorial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = data.load()

    def test_the_latest_quarter_file_holds(self):
        doc = editorial.load(self.data.quarter)
        if doc is None:
            self.skipTest(f'no editorial file for {self.data.quarter}: pages use their computed text')
        self.assertEqual(editorial.verify(doc, self.data), [])
        for lang in ('en', 'ar'):
            for key in ('trend_title', 'trend_lede'):
                with self.subTest(lang=lang, key=key):
                    self.assertTrue(editorial.text(doc, lang, key))

    def test_a_claim_the_data_contradicts_is_caught(self):
        q = self.data.quarters
        doc = {'quarter': self.data.quarter, 'checks': [
            {'claim': 'DZ trails North Africa', 'indicator': 'yoy', 'series': 'DZ', 'below': 'median_north_africa', 'from': q[-1]},
            {'claim': 'DZ grew more slowly', 'indicator': 'accounts', 'rising': ['DZ'], 'from': q[-1], 'to': q[0]},
            {'claim': 'nonsense', 'indicator': 'yoy', 'series': 'DZ'},
        ]}
        dz, na = self.data.series('yoy', 'DZ')[-1], self.data.series('yoy', 'median_north_africa')[-1]
        failures = editorial.verify(doc, self.data)
        self.assertEqual(len(failures), 2 + (dz >= na))
        self.assertTrue(any(f.startswith('DZ grew more slowly: no data') for f in failures))
        self.assertTrue(any(f.startswith('nonsense: unknown check') for f in failures))
        self.assertEqual(any(f.startswith('DZ trails North Africa') for f in failures), dz >= na)

    def test_a_false_file_is_not_used(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        doc = {'quarter': self.data.quarter, 'en': {'trend_title': 'A false headline', 'trend_lede': 'False.'},
               'ar': {'trend_title': 'عنوان خاطئ', 'trend_lede': 'خطأ.'},
               'checks': [{'claim': 'Algeria shrank', 'indicator': 'accounts', 'rising': ['DZ'],
                           'from': self.data.quarter, 'to': self.data.quarter}]}
        (tmp / f'{self.data.quarter.lower()}.json').write_text(json.dumps(doc), 'utf-8')
        editorial.current.cache_clear()
        self.addCleanup(editorial.current.cache_clear)
        with mock.patch.object(editorial, 'EDITORIAL_DIR', tmp), mock.patch('sys.stderr'):
            self.assertIsNone(editorial.current(self.data))

    def test_streak(self):
        self.assertEqual(editorial.streak([None, 1, 2, 3]), (2, 1, 1))
        self.assertEqual(editorial.streak([5, 4, 3, 4]), (1, 1, 2))
        self.assertEqual(editorial.streak([3, 2, 1]), (2, -1, 0))
        self.assertEqual(editorial.streak([1, 1]), (0, 0, 1))
        self.assertEqual(editorial.streak([2, None, 1, 2]), (1, 1, 2))


class TickerMaths(unittest.TestCase):
    """The ticker draws each group of three digits with a CSS counter. A registered <integer>
    property rounds half up, so floor(n / d) is written round((n - (d - 1) / 2) / d)."""

    @staticmethod
    def floor_div(n: int, k: int) -> int:
        d = 1000 ** k
        return n if k == 0 else math.floor((n - (d - 1) / 2) / d + 0.5)

    def groups(self, n: int) -> list:
        g = len(f'{n:,}'.split(','))
        return [self.floor_div(n, g - 1)] + [self.floor_div(n, k) - 1000 * self.floor_div(n, k + 1) for k in range(g - 2, -1, -1)]

    def test_every_value_on_the_way_reads_correctly(self):
        values = list(range(393_565, 586_991, 7)) + [1_000, 999_999, 586_499, 586_500, 586_999, 587_000, 1_234_567, 9_999_999]
        for n in values:
            self.assertEqual(self.groups(n), [int(g) for g in f'{n:,}'.split(',')], n)

    def stub(self, now, before):
        rows = {'accounts': {'value': now, 'year_earlier': before}}
        return type('Data', (), {'overview': lambda self: rows})()

    def test_css_matches_the_maths(self):
        css = home.ticker_css(self.stub(1_234_567, 1_000_001))
        self.assertIn('@keyframes tick{from{--tick:1000001}to{--tick:1234567}}', css)
        self.assertIn('.tg0::after{--tka:calc((var(--tick) - 499999.5) / 1000000)', css)
        self.assertIn('.tg1::after{--tka:calc((var(--tick) - 499.5) / 1000);--tkb:calc((var(--tick) - 499999.5) / 1000000)', css)
        self.assertIn('.tg2::after{--tka:var(--tick);--tkb:calc((var(--tick) - 499.5) / 1000)', css)
        self.assertIn('prefers-reduced-motion:no-preference', css)

    def test_no_count_when_a_digit_group_is_added(self):
        self.assertEqual(home.ticker_css(self.stub(1_200_000, 950_000)), '')
        self.assertFalse(home.animated(self.stub(1_200_000, 950_000)))


class HomePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}
        cls.text = {lang: text_of(h) for lang, h in cls.html.items()}
        cls.css = stylesheet(cls.dist)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_hero_numbers_come_from_the_data(self):
        ov = self.data.overview()
        a, y = ov['accounts'], ov['yoy']
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                text = self.text[lang]
                self.assertIn(fint(a['value'], lang), text)
                self.assertIn(fpct(y['value'], 1, lang, sign=False), text)
                self.assertIn(rank_text(y['north_africa_rank'], y['north_africa_ranked'], lang), text)
                self.assertIn(fint(a['value'] - a['year_earlier'], lang, sign=True), text)

    def test_the_ticker_counts_from_a_year_earlier(self):
        a = self.data.overview()['accounts']
        self.assertIn(f'@keyframes tick{{from{{--tick:{a["year_earlier"]}}}to{{--tick:{a["value"]}}}}}', self.css)
        self.assertIn('<span class="tick-anim" aria-hidden="true">', self.html['en'])

    def test_baseline_sentences(self):
        if self.data.quarter != BASELINE:
            self.skipTest(f'the expectations describe {BASELINE}')
        self.assertIn('Growth has sped up for four quarters in a row.', self.text['en'])
        self.assertIn('تسارع النموّ أربعة أرباع متتالية.', self.text['ar'])
        self.assertIn('Four quarters of acceleration', self.html['en'])
        self.assertIn('from 25.6% to 49.1% a year', self.html['en'])
        self.assertIn('Everyone sped up in 2025. Algeria kept pace with North Africa.', self.text['en'])

    def test_the_scorecard_links_each_indicator_to_the_overview(self):
        doc = Doc(self.html['en'])
        hrefs = [a['href'] for a in doc.find('a', class_='tile')]
        self.assertEqual(hrefs, [f'/en/index/#ind-{k}' for k in ('accounts', 'pushes', 'repos', 'orgs', 'topics', 'permillion')])

    def test_the_trend_chart_has_its_data(self):
        rows = (self.dist / 'charts' / self.data.folder.name / 'home-yoy.csv').read_text('utf-8').splitlines()
        self.assertEqual(rows[0], 'quarter,DZ,median_africa,median_north_africa')
        last = rows[-1].split(',')
        self.assertEqual(last[0], self.data.quarter)
        self.assertAlmostEqual(float(last[1]), self.data.series('yoy', 'DZ')[-1], places=6)
        self.assertIn('id="home-yoy-table"', self.html['en'])

    def test_the_derived_data_is_published(self):
        folder = self.data.folder
        for name in list(self.data.files) + ['manifest.json', 'README.md']:
            with self.subTest(name=name):
                self.assertEqual((self.dist / 'data' / folder.name / name).read_bytes(), (folder / name).read_bytes())
        latest = json.loads((self.dist / 'data' / 'latest.json').read_text('utf-8'))
        self.assertEqual(latest['folder'], folder.name)
        self.assertIn(f'/data/{folder.name}/overview.csv', self.html['en'])

    def test_no_placeholders_left(self):
        for lang, html in self.html.items():
            with self.subTest(lang=lang):
                self.assertNotRegex(text_of(html), r'\{[a-z_]+\}')


if __name__ == '__main__':
    unittest.main()
