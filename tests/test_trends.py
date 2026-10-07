"""Trends (ticket #20): eight views drawn at build time, each with its data table and
downloads; radio buttons and CSS switch them, so the page works without JavaScript."""
import csv
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

from djsite import data  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.fmt import fdec, fint  # noqa: E402
from djsite.pages.trends import INDS, SCALES, SERIES  # noqa: E402
from htmlcheck import stylesheet  # noqa: E402

BASELINE = '2026-Q1'
VIEWS = [f'{k}-{s}' for k, _ in INDS for s in SCALES]


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class Trends(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'trends' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}
        cls.css = stylesheet(cls.dist)
        cls.payload = {lang: json.loads(re.search(r'<script type="application/json" id="trends-data">(.*?)</script>',
                                                  html, re.S).group(1).replace('<\\/', '</')) for lang, html in cls.html.items()}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_every_view_is_drawn_wide_and_narrow(self):
        for lang, html in self.html.items():
            for view in VIEWS:
                key, scale = view.split('-')
                with self.subTest(lang=lang, view=view):
                    self.assertEqual(len(re.findall(rf'<svg class="chart chart-line v i-{key} s-{scale}"', html)), 2)
                    self.assertTrue(f'id="tr-{view}-w-t"' in html and f'id="tr-{view}-n-t"' in html)

    def test_default_view_without_javascript(self):
        html = self.html['en']
        checked = re.findall(r'<input[^>]*id="([\w-]+)"[^>]*checked', html)
        self.assertEqual(checked, ['tr-ind-accounts', 'tr-scale-actual', 'tr-hl-none'])
        for key, _ in INDS:
            self.assertIn(f'.trc:has(#tr-ind-{key}:checked) .v:not(.i-{key})', self.css)
        self.assertIn('.trc:has(#tr-scale-actual:checked) .v.s-indexed', self.css)
        self.assertIn('@supports not selector(:has(*))', self.css)
        # the readout overlay only shows once the script marks the chart active
        self.assertIn('.cw[data-act=true] .ov { opacity: 1; }', self.css)

    def test_controls_are_radio_buttons(self):
        html = self.html['en']
        self.assertEqual(len(re.findall(r'name="tr-ind"', html)), 4)
        self.assertEqual(len(re.findall(r'name="tr-scale"', html)), 2)
        self.assertEqual(len(re.findall(r'name="tr-hl"', html)), 7)          # six peers and "none"
        embeds = html.count('class="seg emb-ts" role="radiogroup"')        # dark or light, in each Embed panel
        self.assertEqual(embeds, 9)
        self.assertEqual(html.count('role="radiogroup"') - embeds, 3)

    def test_each_view_has_a_matching_table(self):
        for view in VIEWS:
            key, scale = view.split('-')
            ind = dict(INDS)[key]
            with self.subTest(view=view):
                block = re.search(rf'<div class="table-wrap fig-dt dz-col v i-{key} s-{scale}".*?</table>', self.html['en'], re.S).group(0)
                rows = re.findall(r'<tr><th scope="row">([^<]+)</th>(.*?)</tr>', block)
                self.assertEqual(len(rows), len(self.data.quarters))
                self.assertEqual(rows[0][0], self.data.quarter.replace('-', ' '))
                dz = self.data.series(ind, 'DZ')
                last = dz[-1] / dz[0] * 100 if scale == 'indexed' else dz[-1]
                fmt = fint(last) if scale == 'indexed' or key == 'accounts' else fdec(last, {'pushes': 2, 'repos': 2, 'orgs': 4}[key])
                self.assertEqual(re.findall(r'<td class="end">([^<]*)</td>', rows[0][1])[0], fmt)

    def test_each_view_has_its_downloads(self):
        folder = self.data.folder.name
        for view in VIEWS:
            with self.subTest(view=view):
                rows = list(csv.reader(io.StringIO((self.dist / 'charts' / folder / f'trends-{view}.csv').read_text('utf-8'))))
                self.assertEqual(rows[0][:3], ['quarter', 'DZ', 'median_north_africa'])
                self.assertEqual(len(rows), len(self.data.quarters) + 1)
                for lang in ('en', 'ar'):
                    self.assertTrue((self.dist / 'charts' / folder / lang / f'trends-{view}-dark.svg').is_file())
        self.assertIn(f'href="/data/{folder}/trends.csv"', self.html['en'])

    def test_readout_data_matches_the_tables(self):
        for lang, p in self.payload.items():
            self.assertEqual(sorted(p['views']), sorted(VIEWS))
            self.assertEqual(p['series'], list(SERIES))
            self.assertEqual(len(p['q']), len(self.data.quarters))
            self.assertEqual(len(p['said']), len(self.data.quarters))
            for view, v in p['views'].items():
                with self.subTest(lang=lang, view=view):
                    for size in ('w', 'n'):
                        self.assertEqual(len(v[size]['g']), 6)
                        self.assertEqual({len(ys) for ys in v[size]['y'].values()}, {len(self.data.quarters)})
                    key, scale = view.split('-')
                    block = re.search(rf'<div class="table-wrap fig-dt dz-col v i-{key} s-{scale}".*?</table>', self.html[lang], re.S).group(0)
                    first_row = re.search(r'<tbody><tr>(.*?)</tr>', block).group(1)
                    self.assertEqual(re.findall(r'<td class="end">([^<]*)</td>', first_row), [v['t'][s][-1] for s in SERIES])

    def test_baseline_text(self):
        if self.data.quarter != BASELINE:
            self.skipTest(f'the expectations describe {BASELINE}')
        text = text_of(self.html['en'])
        self.assertIn('Growth slowed from 44.6% in 2021 to 25.6% in 2025, then jumped to 49.1% in 2026, the fastest pace in the series.', text)
        self.assertIn('In 2026 Q1, Algeria stands at 639: 6.4 times its level in 2020 Q1. Nigeria stands at 1,033, the highest of the six peers.', text)
        self.assertIn('One large value, like Egypt’s 1,626,418 accounts, would pull an average up.', text)
        ind = self.payload['en']['views']['accounts-indexed']['t']
        self.assertEqual(self.payload['en']['said'][self.payload['en']['q'].index('2024 Q2')], 'Q2 2024')
        self.assertEqual(self.payload['ar']['said'][self.payload['ar']['q'].index('2024 Q2')], 'الربع الثاني 2024')
        i = self.payload['en']['q'].index('2024 Q2')
        self.assertEqual((ind['DZ'][i], ind['median_north_africa'][i], ind['MA'][i]), ('361', '308', '379'))
        pushes = self.payload['en']['views']['pushes-actual']['t']
        i = self.payload['en']['q'].index('2021 Q3')
        self.assertEqual((pushes['DZ'][i], pushes['median_north_africa'][i], pushes['KE'][i]), ('0.49', '0.50', '2.34'))

    def test_script_is_loaded_and_keyboard_handled(self):
        self.assertRegex(self.html['en'], r'<script src="/assets/trends\.[0-9a-f]{10}\.js" defer></script>')
        js = next((self.dist / 'assets').glob('trends.*.js')).read_text('utf-8')
        for key in ('ArrowLeft', 'ArrowRight', 'Home', 'End', 'aria-label', 'pointermove'):
            self.assertIn(key, js)


if __name__ == '__main__':
    unittest.main()
