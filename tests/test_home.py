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
from djsite.fmt import MINUS, fint, fpct, ordinal, quarter_label, rank_text  # noqa: E402
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
    """The hero's numbers print with CSS counters (pages/home.py). A registered <integer>
    property rounds half up, so floor(n / d) is written round((n - (d - 1) / 2) / d). Each group
    of three digits with digits before it takes its separator and leading zeros, and a group
    that is still 0 prints nothing, so a number can gain a group; the last group prints 0 for
    a number at 0. The figures under the count add a sign, the growth's tenths and the rank's
    ordinal."""

    YEARS = [('2020-Q1', 91_819), ('2021-Q1', 132_744), ('2022-Q1', 181_881)]
    STATS = [None, (446, 6, 7, 40_925), (370, 4, 7, 49_137)]

    @staticmethod
    def floor_div(n: int, k: int) -> int:
        d = 1000 ** k
        return n if k == 0 else math.floor((n - (d - 1) / 2) / d + 0.5)

    def printed(self, n: int, width: int, sep: str = ',') -> str:
        """What the counters print for the digits of n, worked out the way the stylesheet does."""
        clamp = lambda v: min(max(v, 0), 1)
        m, out = max(n, -n), ''
        for i in range(width):
            k, last = width - 1 - i, i == width - 1
            a, h = self.floor_div(m, k), self.floor_div(m, k + 1)
            g = a - 1000 * h
            lead = clamp(h)
            zeros = lead * (3 - (1 if last else clamp(g)) - clamp(g - 9) - clamp(g - 99))
            out += (sep if lead else '') + '0' * zeros + (str(g) if g > 0 or last else '')
        return out

    def figures_printed(self, row, lang: str) -> tuple:
        """What the counters print for a year's figures, worked out the way the stylesheet does."""
        growth, rank, ranked, added = row
        sign = lambda v: min(max(v, -1), 1) + 1
        m = max(growth, -growth)
        whole = math.floor((m - 4.5) / 10 + 0.5)
        return (['▼ ', '▲ ', '▲ '][sign(growth)] + f'{whole}{home.POINT[lang]}{m - 10 * whole}%',
                f'{ordinal(rank) if rank else 0} of {ranked}' if lang == 'en' else f'{rank} من {ranked}',
                [MINUS, '', '+'][sign(added)] + self.printed(added, 3, home.GROUP[lang]))

    def test_every_value_on_the_way_reads_correctly(self):
        values = list(range(91_819, 586_991, 13)) + [0, 1, 9, 10, 99, 100, 999, 1_000, 1_001, 99_999, 999_999, 1_000_000,
                                                      1_000_005, 1_010_101, 1_234_567, 9_999_999]
        for n in values:
            for width in range(len(f'{n:,}'.split(',')), 4):
                self.assertEqual(self.printed(n, width), f'{n:,}', (n, width))
                self.assertEqual(self.printed(-n, width), f'{n:,}', 'the digits of the magnitude')

    def test_the_figures_read_as_the_page_writes_them(self):
        for lang in ('en', 'ar'):
            for n in list(range(-1500, 1501, 7)) + [0, 1, 5, 9, 10, 99, 100, 999, 1000]:
                row = (n, 1 + abs(n) % 7, 7, n * 37)
                with self.subTest(lang=lang, n=n):
                    self.assertEqual(self.figures_printed(row, lang), home.figure_text(row, lang))
        self.assertEqual(self.figures_printed((0, 0, 7, 0), 'en'), ('▲ 0.0%', '0 of 7', '0'), 'the first year waits at 0')
        self.assertEqual(self.figures_printed((0, 0, 7, 0), 'ar'), ('▲ 0,0%', '0 من 7', '0'))

    def test_the_stylesheet_goes_through_every_year(self):
        css = home.hero_css('en', self.YEARS)
        length, flips, rewind = home.timeline(3)
        self.assertEqual(flips, [home.HOLD, home.HOLD + home.FLIP])
        self.assertAlmostEqual(length, home.HOLD + 2 * home.FLIP + home.REST + home.REWIND)
        tick = re.search(r'@keyframes hero-tick\{(.*?)\}\n', css).group(1)
        self.assertEqual(re.findall(r'--tick:(\d+)', tick), ['91819', '91819', '132744', '132744', '181881', '181881', '91819'])
        self.assertEqual(re.findall(r'--yr:(\d+)', css), ['2020', '2020', '2021', '2021', '2022', '2022', '2020'])
        self.assertIn('.tick-anim,.hs-c{--tm:max(var(--tick),-1 * var(--tick))}', css)
        self.assertIn('.tick-anim .tg0{--ta:calc((var(--tm) - 499.5) / 1000);--th:calc((var(--tm) - 499999.5) / 1000000)}', css)
        self.assertIn('.tick-anim .tg1{--ta:var(--tm);--th:calc((var(--tm) - 499.5) / 1000)}', css)
        self.assertIn('.tick-anim .tg1{--td:calc(1 + clamp(0,var(--tg) - 9,1) + clamp(0,var(--tg) - 99,1))}', css)
        self.assertIn('.tick-anim .tg1::after{content:counter(tkz,tick-zeros) counter(tkg)}', css)
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
        self.assertIn('.tick-anim .tg2{--ta:var(--tm)', css)
        self.assertIn('--tick:875000', css)

    def test_one_year_has_nothing_to_replay(self):
        self.assertEqual(home.hero_css('en', self.YEARS[:1]), '')

    def test_the_figures_count_with_the_year(self):
        css = home.hero_css('en', self.YEARS, self.STATS)
        frames = lambda name, prop: re.findall(rf'--{prop}:(-?\d+)', re.search(rf'@keyframes {name}\{{(.*?)\}}\n', css).group(1))
        self.assertEqual(frames('hero-tick', 'tick'), ['91819', '91819', '132744', '132744', '181881', '181881', '91819'])
        self.assertEqual(frames('hero-f0', 'tick'), ['0', '0', '446', '446', '370', '370', '0'], 'from 0, with the count, and back')
        self.assertEqual(frames('hero-f1', 'tick'), ['0', '0', '6', '6', '4', '4', '0'])
        self.assertEqual(frames('hero-f1', 'tn'), ['7'] * 7)
        self.assertEqual(frames('hero-f2', 'tick'), ['0', '0', '40925', '40925', '49137', '49137', '0'])
        self.assertRegex(css, r'@keyframes hero-on\{0%,[\d.]+%\{opacity:\.4\}[\d.]+%\{opacity:1\}', 'muted while the first year waits at 0')
        self.assertIn('.hv0::before{content:"▲ 44.6%"}.hv1::before{content:"6th of 7"}.hv2::before{content:"+40,925"}', css)
        self.assertIn('@counter-style tick-ord{system:fixed 1;symbols:"1st" "2nd" "3rd" "4th" "5th" "6th" "7th"}', css)
        self.assertIn('@counter-style tick-arrow{system:fixed 0;symbols:"▼ " "▲ " "▲ "}', css)
        self.assertIn(f'@counter-style tick-sign{{system:fixed 0;symbols:"{MINUS}" "" "+"}}', css)
        # the counters print what figures_printed works out
        self.assertIn('.hs-c{--ts:calc(clamp(-1,var(--tick),1) + 1)}', css)
        self.assertIn('--ti:calc((var(--tm) - 4.5) / 10);--tf:calc(var(--tm) - 10 * var(--ti))', css)
        self.assertIn('content:counter(tka,tick-arrow) counter(tki) "." counter(tkf) "%"', css)
        self.assertIn('content:counter(tkr,tick-ord) " of " counter(tkn)', css)
        self.assertIn('.hv2 .hs-c::before{counter-reset:tka var(--ts);content:counter(tka,tick-sign)}', css)
        ar = home.hero_css('ar', self.YEARS, self.STATS)
        self.assertIn('content:counter(tka,tick-arrow) counter(tki) "," counter(tkf) "%"', ar)
        self.assertIn('content:counter(tkr) " من " counter(tkn)', ar)
        self.assertNotIn('tick-ord', ar)
        self.assertIn('.um-years rect,.hs-a span){animation-play-state:paused}', css)
        self.assertNotIn('hero-f0', home.hero_css('en', self.YEARS), 'without the figures, the latest stay')
        self.assertNotIn('hero-f0', home.hero_css('en', self.YEARS, [None, None, self.STATS[2]]), 'and with a year missing')


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
                tick = re.search(r'@keyframes hero-tick\{((?:[^{}]*\{[^{}]*\})*)\}', own).group(1)
                self.assertEqual(re.findall(r'--tick:(\d+)', tick)[1::2], [str(v) for _, v in years])
                self.assertIn('<span class="tick-anim" aria-hidden="true">', html)
                self.assertIn('<span class="yr-anim"></span>', html)
                self.assertIn('<label class="hero-pause"><input class="sr-only" type="checkbox" checked>', html)
                self.assertIn('<svg class="chart um um-years"', html)
                self.assertEqual(len(re.findall(r'<g class="s\d', html)), len(years))
        hub = (self.dist / 'en' / 'hub' / 'index.html').read_text('utf-8')
        self.assertNotIn('hero-tick', hub, 'only Home carries the replay')
        self.assertEqual(self.html['en'].count('<style>'), 1, 'in the one inlined stylesheet')

    def test_3d_enhancement_keeps_the_data_and_accessible_map(self):
        accounts = int(self.data.overview()['accounts']['value'])
        first = home.history(self.data)[0][0][:4]
        for lang, html in self.html.items():
            with self.subTest(lang=lang):
                self.assertIn(f'data-map-accounts="{accounts}"', html)
                self.assertIn(f'data-map-first-year="{first}"', html)
                self.assertIn(f'data-map-latest-year="{self.data.quarter[:4]}"', html)
                self.assertRegex(html, r'<div class="hero-map-stage"><svg[^>]*role="img"')
                self.assertIn('id="home-units-table"', html)
                self.assertRegex(html, r'<script src="/assets/home-map\.[0-9a-f]{10}\.js" defer>')
        hub = (self.dist / 'en' / 'hub' / 'index.html').read_text('utf-8')
        self.assertNotIn('/assets/home-map.', hub)

    def test_the_figures_follow_the_year(self):
        years = home.history(self.data)
        stats = home.year_figures(self.data, years)
        ov = self.data.overview()
        a, y = ov['accounts'], ov['yoy']
        self.assertEqual(len(stats), len(years))
        self.assertIsNone(stats[0], 'the first year has no year before it')
        self.assertEqual(stats[-1][3], a['value'] - a['year_earlier'])
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                self.assertEqual(home.figure_text(stats[-1], lang),
                                 (f'▲ {fpct(y["value"], 1, lang, sign=False)}', rank_text(y['north_africa_rank'], y['north_africa_ranked'], lang),
                                  fint(a['value'] - a['year_earlier'], lang, sign=True)), 'the latest, as the Overview has them')
                css = self.html[lang].split('<style>')[1].split('</style>')[0]
                for name, column in (('hero-f0', 0), ('hero-f1', 1), ('hero-f2', 3)):     # growth, rank, accounts added
                    counts = re.search(rf'@keyframes {name}\{{((?:[^{{}}]*\{{[^{{}}]*\}})*)\}}', css).group(1)
                    reached = re.findall(r'--tick:(-?\d+)', counts)[2:-1:2]          # as each later year's count ends
                    self.assertEqual(reached, [str(s[column]) for s in stats[1:]], name)
                html = self.html[lang]
                self.assertEqual(html.count('<span class="hs-c'), 3)
                self.assertIn('<span class="hs-c tick-anim"><span class="tg0"></span>', html, 'the accounts added in digit groups')
        self.assertIn('accounts added in a year', self.text['en'])
        if self.data.quarter == BASELINE:
            self.assertEqual(stats[1:-1], [(446, 6, 7, 40_925), (370, 4, 7, 49_137), (309, 6, 7, 56_276), (315, 3, 7, 75_137),
                                           (256, 4, 7, 80_271)])
            self.assertEqual([home.figure_text(s, 'en') for s in stats[1:-1]],
                             [('▲ 44.6%', '6th of 7', '+40,925'), ('▲ 37.0%', '4th of 7', '+49,137'),
                              ('▲ 30.9%', '6th of 7', '+56,276'), ('▲ 31.5%', '3rd of 7', '+75,137'),
                              ('▲ 25.6%', '4th of 7', '+80,271')])

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

    def test_scorecard_ranks_describe_the_displayed_measure(self):
        overview = self.data.overview()
        keys = ('accounts', 'pushes', 'repos', 'orgs', 'topics', 'permillion')
        fields = ('accounts', 'pushes_per_account', 'repos_per_account', 'orgs_per_account', 'topics', 'accounts_per_million')
        for lang, html in self.html.items():
            cards = re.findall(r'<a class="card tile reveal"[^>]*>(.*?)</a>', html, re.S)
            self.assertEqual(len(cards), 6)
            for key, field, card in zip(keys, fields, cards):
                row = overview[field]
                groups = ('algeria_and_peers',) if key in ('topics', 'permillion') else ('north_africa', 'africa')
                with self.subTest(lang=lang, measure=key):
                    ranks = re.findall(r'<span class="num rank-n[^\"]*"[^>]*>(.*?)</span>', card)
                    self.assertEqual(ranks, [rank_text(row[g + '_rank'], row[g + '_ranked'], lang) for g in groups])
                    self.assertIn(quarter_label(self.data.quarter, lang), text_of(card))
            # Total-account ranks must not silently become growth ranks again.
            if overview['accounts']['africa_rank'] != overview['yoy']['africa_rank']:
                self.assertNotIn(rank_text(overview['yoy']['africa_rank'], overview['yoy']['africa_ranked'], lang), text_of(cards[0]))

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
