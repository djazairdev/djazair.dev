"""Languages (ticket #22): Algeria's top ten languages with the change on a year earlier, a
data table and downloads, a lede computed from the data, and the peers' first three."""
import csv
import io
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite import charts, data  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.fmt import and_list, fint  # noqa: E402
from djsite.pages import languages  # noqa: E402
from djsite.scorecard import CORE_PEERS  # noqa: E402

BASELINE = '2026-Q1'           # the quarter the hand-checked expectations below describe


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html))


class LanguagesPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'languages' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_the_chart_has_the_top_ten_with_a_year_earlier(self):
        top = languages.rows(self.data)[:10]
        path = self.dist / 'charts' / self.data.folder.name / 'languages-top.csv'
        rows = list(csv.DictReader(io.StringIO(path.read_text('utf-8'))))
        self.assertEqual([r['key'] for r in rows], [r['language'] for r in top])
        self.assertEqual([int(r['value']) for r in rows], [r['pushers'] for r in top])
        self.assertEqual([int(r['year_earlier']) for r in rows], [r['pushers_year_earlier'] for r in top])
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                self.assertIn('id="languages-top-table"', self.html[lang])
                self.assertIn(f'/charts/{self.data.folder.name}/{lang}/languages-top-light.svg', self.html[lang])
                self.assertIn(fint(top[0]['pushers'], lang), text_of(self.html[lang]))

    def test_it_says_the_counts_cannot_be_added_up(self):
        self.assertIn('the counts can’t be added up', text_of(self.html['en']))
        self.assertIn('لا تُجمع هذه الأعداد', text_of(self.html['ar']))

    def test_baseline_lede(self):
        if self.data.quarter != BASELINE:
            self.skipTest(f'the expectations describe {BASELINE}')
        text = text_of(self.html['en'])
        self.assertIn('HTML is first, as in every quarter since Q1 2020.', text)
        self.assertIn('Dockerfile and Jupyter Notebook entered the top ten, in place of C++ and Java.', text)
        self.assertIn('Dockerfile grew fastest: +172.7% on a year earlier.', text)
        self.assertIn('<bdi lang="en">C++</bdi>', self.html['ar'])          # keeps its signs in Arabic

    def test_peers_first_three(self):
        section = re.search(r'<section class="section section-s" id="peers".*?</section>', self.html['en'], re.S).group(0)
        keys = re.findall(r'<tr[^>]*data-key="(\w+)"', section)
        self.assertEqual(keys, ['DZ', *CORE_PEERS])
        for code in keys:
            row = re.search(rf'data-key="{code}">(.*?)</tr>', section, re.S).group(1)
            langs = languages.rows(self.data, code)
            with self.subTest(code=code):
                self.assertEqual(re.findall(r'class="lang-n"[^>]*>([^<]+)<', row), [r['language'] for r in langs[:3]])
                self.assertIn(f'data-v="{len(langs)}"', row)

    def test_methodology_link_and_download(self):
        self.assertIn('/en/methodology/#languages', self.html['en'])
        self.assertIn(f'/data/{self.data.folder.name}/languages.csv', self.html['en'])

    def test_no_placeholders_left(self):
        for lang, html in self.html.items():
            with self.subTest(lang=lang):
                self.assertNotRegex(text_of(html), r'\{[a-z_]+\}')


class HBarDrawing(unittest.TestCase):
    def chart(self, bars):
        return charts.HBarChart(id='t', quarter='2026-Q1', title='T', summary='S', bars=bars,
                                fmt=lambda v, lang: fint(v, lang), change_fmt=lambda v, lang: f'{v:+.1%}')

    def test_arabic_mirrors_the_bars(self):
        c = self.chart([charts.HBar('A', 'Alpha', 100, 50, 1), charts.HBar('B', 'Beta', 40, 20, 2)])
        g = charts.HBAR_SIZES['wide']
        start = g['label'] + 14                          # where bars begin, from the reading start
        for lang in ('en', 'ar'):
            body = charts.drawing(c, lang, 'wide').body
            x, w = map(float, re.search(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)"[^>]*class="hb-o', body).groups())
            with self.subTest(lang=lang):
                if lang == 'en':
                    self.assertAlmostEqual(x, start, places=0)           # grows rightwards from the names
                else:
                    self.assertAlmostEqual(x + w, g['W'] - start, places=0)   # grows leftwards

    def test_a_loss_is_an_outline(self):
        body = charts.drawing(self.chart([charts.HBar('A', 'Alpha', 80, 100, 1)]), 'en', 'narrow').body
        self.assertIn('class="hb-l fd"', body)
        self.assertNotIn('class="hb-n gr"', body)
        self.assertIn('-20.0%', body)

    def test_and_list(self):
        self.assertEqual(and_list(['A'], 'en'), 'A')
        self.assertEqual(and_list(['A', 'B', 'C'], 'en'), 'A, B and C')
        self.assertEqual(and_list(['أ', 'ب'], 'ar'), 'أ وب')


if __name__ == '__main__':
    unittest.main()
