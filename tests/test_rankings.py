"""External rankings (ticket #38, IDX-11, PRD A.6): GitHub's one-off GDC26 ranking for Africa,
labelled as GitHub's; Algeria's figure labelled as djazair.dev's estimate wherever it appears;
how the estimate is made and how far it lands from GitHub's own figures."""
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
from djsite.charts import HBar, HBarChart  # noqa: E402
from djsite.pages import rankings  # noqa: E402

BASELINE = '2026-Q1'           # the quarter the hand-checked expectations below describe


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class RankingsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'rankings' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def main(self, lang: str) -> str:
        return re.search(r'<main.*?</main>', self.html[lang], re.S).group(0)

    def section(self, lang: str, id_: str) -> str:
        return re.search(rf'<section class="section section-s" id="{id_}".*?</section>', self.html[lang], re.S).group(0)

    def test_africas_top_ten_and_algerias_estimate(self):
        """PRD A.6: Mauritius 272 ... Eswatini 102; Algeria isn't listed, about 67 by the estimate."""
        figure = list(csv.DictReader(io.StringIO((self.dist / 'charts' / '2026-q1' / 'rankings-africa.csv').read_text())))
        self.assertEqual([(r['key'], round(float(r['value']))) for r in figure],
                         [('MU', 272), ('TN', 256), ('KE', 167), ('MA', 163), ('RW', 140), ('EG', 134), ('ZA', 123),
                          ('BW', 107), ('GH', 103), ('SZ', 102), ('DZ', 67)])
        self.assertEqual([r['key'] for r in figure if r['estimate'] == 'true'], ['DZ'])
        self.assertEqual(figure[-1]['rank'], '', 'the estimate has no rank')

    def test_the_estimate_is_labelled_as_one(self):
        for lang, label in (('en', 'Algeria (estimate)'), ('ar', 'الجزائر (تقدير)')):
            main = self.main(lang)
            for size in ('w', 'n'):
                svg = re.search(rf'<svg[^>]*aria-labelledby="rankings-africa-{size}-t.*?</svg>', main, re.S).group(0)
                self.assertEqual(len(re.findall(r'class="hb-e', svg)), 1)
                self.assertIn(f'>{label}</text>', svg)
            self.assertIn(label, re.search(r'<details class="disclosure fig-table".*?</details>', main, re.S).group(0))
            for theme in ('dark', 'light'):
                download = (self.dist / 'charts' / '2026-q1' / lang / f'rankings-africa-{theme}.svg').read_text('utf-8')
                self.assertIn(label, download)
                self.assertIn('stroke-dasharray="4 3"', download)

    @unittest.skipUnless(data.load().quarter == BASELINE, 'expectations describe the 2026-Q1 data')
    def test_sentences_follow_the_data(self):
        en, ar = text_of(self.main('en')), text_of(self.main('ar'))
        self.assertIn('Mauritius leads Africa with 272 pushes per 1,000 working-age people, ahead of Tunisia ( 256 ) and '
                      'Kenya ( 167 ).', en)
        self.assertIn('From North Africa, the top ten has Tunisia ( 2nd ), Morocco ( 4th ) and Egypt ( 6th ).', en)
        self.assertIn('GitHub doesn’t list Algeria. By djazair.dev’s estimate it stands at about 67 , against 102 for Eswatini '
                      'in tenth place.', en)
        self.assertIn('From Africa it has Nigeria ( 25th ) and Egypt ( 28th ).', en)
        self.assertIn('Quarters not released yet are taken as equal to Q1 2026: Q2 2026.', en)
        self.assertIn('would take about 1.5 times Algeria’s estimated pushes: some 3.07 million over the four quarters '
                      'instead of 2.01 million.', en)
        self.assertIn('the estimate comes within 13 % of GitHub’s figure for 9 of them. For Eswatini, GitHub’s figure is 2.5 '
                      'times the estimate.', en)
        self.assertIn('Nigeria ( 79 )', en)
        self.assertIn('تونس (المرتبة 2 ) والمغرب (المرتبة 4 ) ومصر (المرتبة 6 )', ar)
        self.assertIn('مقابل 102 للمرتبة العاشرة (إسواتيني)', ar)

    def test_the_estimate_step_by_step(self):
        dz = rankings.estimates(self.data)['DZ']
        for lang in ('en', 'ar'):
            section = self.section(lang, 'estimate')
            values = [int(v) for v in re.findall(r'<td class="end" data-v="(\d+)">', section)]
            quarters = [dz[f'pushes_{q[:4]}_q{q[-1]}'] for q in rankings.QUARTERS]
            self.assertEqual(values, quarters + [sum(quarters), dz['working_age_population']])
            self.assertEqual(sum(quarters), dz['pushes'])
            self.assertIn(f'data-v="{dz["per_1k_working_age"]}"', section.split('<tfoot>')[1])
        assumed = [q for q in rankings.QUARTERS if q not in self.data.quarters]
        self.assertEqual(dz['quarters_assumed'], len(assumed))
        if assumed:
            self.assertIn('(taken as', text_of(self.section('en', 'estimate')))

    def test_checked_against_githubs_figures(self):
        found = rankings.checked(self.data)
        self.assertEqual(len(found), 10)
        for code, rank, theirs, mine, ratio in found:
            self.assertAlmostEqual(ratio, theirs / mine)
        rows = dict(re.findall(r'<tr[^>]*data-key="(\w+)">(.*?)</tr>', self.section('en', 'check'), re.S))
        self.assertEqual(list(rows)[:10], [c for c, *_ in found])
        self.assertEqual(list(rows)[-1], 'DZ')
        self.assertIn('NG', rows, 'a core peer GitHub doesn’t list')

    def test_in_the_index_navigation_the_footer_and_the_sitemap(self):
        sitemap = (self.dist / 'sitemap.xml').read_text()
        for lang in ('en', 'ar'):
            overview = (self.dist / lang / 'index' / 'index.html').read_text('utf-8')
            self.assertIn(f'href="/{lang}/index/rankings/"', re.search(r'<nav class="subnav".*?</nav>', overview, re.S).group(0))
            self.assertIn(f'href="/{lang}/index/rankings/"', re.search(r'<footer.*?</footer>', overview, re.S).group(0))
            own = re.search(r'<nav class="subnav".*?</nav>', self.html[lang], re.S).group(0)
            self.assertRegex(own, rf'<a href="/{lang}/index/rankings/"[^>]*aria-current="page"')
            self.assertIn(f'<loc>https://djazair.dev/{lang}/index/rankings/</loc>', sitemap)
            self.assertIn(f'/{lang}/data/#gdc26', self.main(lang))
            self.assertIn('id="gdc26"', (self.dist / lang / 'data' / 'index.html').read_text('utf-8'))
            self.assertIn('/data/2026-q1/gdc26.csv', self.main(lang))


class EstimateBars(unittest.TestCase):
    def chart(self):
        bars = [HBar('MU', 'Mauritius', 272, rank=1), HBar('DZ', 'Algeria (estimate)', 67, estimate=True)]
        return HBarChart(id='t', quarter='2026-Q1', title='T', summary='S', bars=bars, fmt=lambda v, lang: str(round(v)),
                         change_fmt=lambda v, lang: '', highlight='DZ', split=False)

    def test_an_estimate_is_an_outline(self):
        svg = charts.drawing(self.chart(), 'en', 'wide').body
        outline = re.search(r'<rect[^>]*class="hb-e[^"]*"/>', svg).group(0)
        self.assertIn(f'stroke="{charts.DARK["algeria"]}"', outline)
        self.assertIn(f'fill="{charts.DARK["algeria_fill"]}"', outline)
        self.assertEqual(len(re.findall(r'class="hb-n', svg)), 1, 'only the published bar is solid')

    def test_files_flag_the_estimate_only_when_there_is_one(self):
        self.assertEqual(self.chart().csv().decode().splitlines()[0], 'key,rank,value,year_earlier,change,estimate')
        plain = HBarChart(id='t', quarter='2026-Q1', title='T', summary='S', bars=[HBar('MU', 'Mauritius', 272)],
                          fmt=str, change_fmt=str)
        self.assertEqual(plain.csv().decode().splitlines()[0], 'key,rank,value,year_earlier,change')
        self.assertNotIn('"estimate"', plain.json().decode())

    def test_a_table_without_a_year_earlier_has_two_columns(self):
        head, rows = charts.table(self.chart(), 'en', {})
        self.assertEqual(len(head), 2)
        self.assertEqual([len(cells) for _, cells in rows], [2, 2])


if __name__ == '__main__':
    unittest.main()
