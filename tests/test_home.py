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
    """The hero's count prints each group of three digits with CSS counters (pages/home.py). A
    registered <integer> property rounds half up, so floor(n / d) is written
    round((n - (d - 1) / 2) / d). A group with digits before it takes its separator and leading
    zeros, and a group that is still 0 prints nothing, so the count can gain a group."""

    YEARS = [('2020-Q1', 91_819), ('2021-Q1', 132_744), ('2022-Q1', 181_881)]

    @staticmethod
    def floor_div(n: int, k: int) -> int:
        d = 1000 ** k
        return n if k == 0 else math.floor((n - (d - 1) / 2) / d + 0.5)

    def printed(self, n: int, width: int) -> str:
        """What the counters print for n, worked out the way the stylesheet does."""
        clamp = lambda v: min(max(v, 0), 1)
        out = ''
        for i in range(width):
            k = width - 1 - i
            a, h = self.floor_div(n, k), self.floor_div(n, k + 1)
            g = a - 1000 * h
            lead = clamp(h)
            zeros = lead * (3 - clamp(g) - clamp(g - 9) - clamp(g - 99))
            out += (',' if lead else '') + '0' * zeros + (str(g) if g > 0 else '')
        return out

    def test_every_value_on_the_way_reads_correctly(self):
        values = list(range(91_819, 586_991, 13)) + [1, 9, 10, 99, 100, 999, 1_000, 1_001, 99_999, 999_999, 1_000_000,
                                                      1_000_005, 1_010_101, 1_234_567, 9_999_999]
        for n in values:
            for width in range(len(f'{n:,}'.split(',')), 4):
                self.assertEqual(self.printed(n, width), f'{n:,}', (n, width))

    def test_the_stylesheet_goes_through_every_year(self):
        css = home.hero_css('en', self.YEARS)
        length, flips, rewind = home.timeline(3)
        self.assertEqual(flips, [home.HOLD, home.HOLD + home.FLIP])
        self.assertAlmostEqual(length, home.HOLD + 2 * home.FLIP + home.REST + home.REWIND)
        tick = re.search(r'@keyframes hero-tick\{(.*?)\}\n', css).group(1)
        self.assertEqual(re.findall(r'--tick:(\d+)', tick), ['91819', '91819', '132744', '132744', '181881', '181881', '91819'])
        self.assertEqual(re.findall(r'--yr:(\d+)', css), ['2020', '2020', '2021', '2021', '2022', '2022', '2020'])
        self.assertIn('.tick-anim .tg0{--ta:calc((var(--tick) - 499.5) / 1000);--th:calc((var(--tick) - 499999.5) / 1000000)}', css)
        self.assertIn('.tick-anim .tg1{--ta:var(--tick);--th:calc((var(--tick) - 499.5) / 1000)}', css)
        self.assertIn('@counter-style tick-sep{system:fixed 0;symbols:"" ","}', css)
        self.assertIn('content:"Q1 " counter(yr)', css)
        ar = home.hero_css('ar', self.YEARS)
        self.assertIn('@counter-style tick-sep{system:fixed 0;symbols:"" "."}', ar)
        self.assertIn('content:"الربع الأول " counter(yr)', ar)
        self.assertIn('@keyframes um-s2{', css)       # the years after the first, each with its squares
        self.assertNotIn('um-s3', css)

    def test_it_only_moves_when_motion_is_welcome(self):
        css = home.hero_css('en', self.YEARS)
        before, rules = css.split('@media (prefers-reduced-motion:no-preference){@supports (color:rgb(from white r g b)){')
        self.assertNotIn('animation:', before, 'definitions only')
        self.assertIn('.hero-n .tick-anim{display:inline;animation:hero-tick', rules)
        self.assertIn('.hero-pause{display:inline-flex}', rules)
        self.assertIn(':has(.hero-pause input:checked)', rules)
        self.assertIn('{animation-play-state:paused}', rules)

    def test_the_count_can_gain_a_digit_group(self):
        css = home.hero_css('en', [('2027-Q1', 875_000), ('2028-Q1', 1_300_000)])
        self.assertIn('.tick-anim .tg2{--ta:var(--tick)', css)
        self.assertIn('--tick:875000', css)

    def test_one_year_has_nothing_to_replay(self):
        self.assertEqual(home.hero_css('en', self.YEARS[:1]), '')


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

    def test_the_hero_replays_every_year(self):
        years = home.history(self.data)
        a = self.data.overview()['accounts']
        self.assertEqual(years[0][0], '2020' + self.data.quarter[4:], 'from the first year of data')
        self.assertTrue(all(q[4:] == self.data.quarter[4:] for q, _ in years), 'a year apart')
        self.assertEqual(years[-2:], [(years[-2][0], a['year_earlier']), (self.data.quarter, a['value'])])
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                html = self.html[lang]
                css = html.split('<style>')[1].split('</style>')[0]
                own = css[css.index('@property --tick'):]                 # Home's own rules, after the shared ones
                self.assertEqual(re.findall(r'--tick:(\d+)', own)[1::2], [str(v) for _, v in years])
                self.assertIn('<span class="tick-anim" aria-hidden="true">', html)
                self.assertIn('<span class="yr-anim"></span>', html)
                self.assertIn('<label class="hero-pause"><input class="sr-only" type="checkbox">', html)
                self.assertIn('<svg class="chart um um-years"', html)
                self.assertEqual(len(re.findall(r'<g class="s\d', html)), len(years))
        hub = (self.dist / 'en' / 'hub' / 'index.html').read_text('utf-8')
        self.assertNotIn('hero-tick', hub, 'only Home carries the replay')
        self.assertEqual(self.html['en'].count('<style>'), 1, 'in the one inlined stylesheet')

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
