"""Topics (ticket #36, IDX-09, AC-IDX-3): the topics GitHub publishes for Algeria against the
six core peers and the medians, a year earlier and since 2020; Algeria's own topics; the
largest topics in each peer; the sentences computed from the data."""
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
from djsite.pages import topics  # noqa: E402
from djsite.scorecard import CORE_PEERS  # noqa: E402

BASELINE = '2026-Q1'           # the quarter the hand-checked expectations below describe


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class TopicsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'topics' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def main(self, lang: str) -> str:
        return re.search(r'<main.*?</main>', self.html[lang], re.S).group(0)

    def section(self, lang: str, id_: str) -> str:
        return re.search(rf'<section class="section section-s" id="{id_}".*?</section>', self.html[lang], re.S).group(0)

    def rows(self, html: str) -> dict:
        body = html.split('<tbody>')[1].split('</tbody>')[0]
        return dict(re.findall(r'<tr[^>]*data-key="([\w-]+)">(.*?)</tr>', body, re.S))

    @unittest.skipUnless(data.load().quarter == BASELINE, 'expectations describe the 2026-Q1 data')
    def test_counts_match_the_prd(self):
        """AC-IDX-3: Algeria 3, Egypt 37, Nigeria 23, Tunisia 18 in Q1 2026."""
        for code, n in (('DZ', 3), ('EG', 37), ('NG', 23), ('TN', 18)):
            self.assertEqual(topics.count(self.data, code), n)
        figure = (self.dist / 'charts' / '2026-q1' / 'topics-peers.csv').read_text()
        table = {r['key']: r for r in csv.DictReader(io.StringIO(figure))}
        self.assertEqual({k: int(table[k]['value']) for k in ('DZ', 'EG', 'NG', 'TN')}, {'DZ': 3, 'EG': 37, 'NG': 23, 'TN': 18})
        self.assertEqual(int(table['DZ']['year_earlier']), 2)
        self.assertEqual(int(table['TN']['change']), 16)                      # a difference, not a ratio
        for lang in ('en', 'ar'):
            peers = self.rows(self.section(lang, 'peers'))
            self.assertEqual(list(peers), ['DZ', *CORE_PEERS])
            self.assertIn('data-v="37"', peers['EG'])

    @unittest.skipUnless(data.load().quarter == BASELINE, 'expectations describe the 2026-Q1 data')
    def test_sentences_follow_the_data(self):
        en, ar = text_of(self.main('en')), text_of(self.main('ar'))
        self.assertIn('GitHub published 3 topics for Algeria in Q1 2026, the same as the North African median.', en)
        self.assertIn('Egypt had 37 , Nigeria 23 and Tunisia 18 ; the median of the six core peers was 15.5', en)
        self.assertIn('From Q1 2021 to Q4 2025, GitHub published 2 topics for Algeria every quarter. In Q1 2026 it published 3 .', en)
        self.assertIn('Not published a year earlier: python', en)
        self.assertIn('وهو وسيط شمال أفريقيا', ar)
        self.assertIn('15,5', ar)
        self.assertEqual(topics.steady(self.data), ('2021-Q1', '2025-Q4'))

    def test_the_lede_side_matches_the_median(self):
        side = {'at': 'the same as the North African median', 'above': 'above the North African median',
                'below': 'below the North African median'}
        n, m = topics.count(self.data, 'DZ'), topics.medians(self.data)['na']
        expected = 'at' if n == m else 'above' if n > m else 'below'
        self.assertIn(side[expected], text_of(self.main('en')))

    def test_algerias_topics_table(self):
        for lang in ('en', 'ar'):
            table = self.rows(self.section(lang, 'algeria'))
            self.assertEqual(list(table), [r['topic'] for r in topics.rows(self.data)])
            for key, row in table.items():
                self.assertRegex(row, r'^\s*<th scope="row"><span class="topic-n" lang="en" dir="ltr">')
            new = [r['topic'] for r in topics.rows(self.data) if r['pushers_year_earlier'] is None]
            for topic in new:
                self.assertIn('<td class="end" data-v="">—</td>', table[topic])

    def test_two_figures_with_downloads_and_tables(self):
        for lang in ('en', 'ar'):
            main = self.main(lang)
            self.assertEqual(len(re.findall(r'<details class="disclosure fig-table"', main)), 2)
            for chart_id in ('topics-peers', 'topics-trend'):
                self.assertIn(f'/charts/2026-q1/{chart_id}.csv', main)
                for theme in ('dark', 'light'):
                    self.assertTrue((self.dist / 'charts' / '2026-q1' / lang / f'{chart_id}-{theme}.svg').is_file())
        trend = (self.dist / 'charts' / '2026-q1' / 'topics-trend.csv').read_text().splitlines()
        self.assertEqual(trend[0], 'quarter,DZ,median_north_africa,' + ','.join(CORE_PEERS))
        self.assertEqual(len(trend), 1 + len(self.data.quarters))

    def test_in_the_index_navigation_and_the_footer(self):
        for lang in ('en', 'ar'):
            overview = (self.dist / lang / 'index' / 'index.html').read_text('utf-8')
            sub = re.search(r'<nav class="subnav".*?</nav>', overview, re.S).group(0)
            self.assertIn(f'href="/{lang}/index/topics/"', sub)
            footer = re.search(r'<footer.*?</footer>', overview, re.S).group(0)
            self.assertIn(f'href="/{lang}/index/topics/"', footer)
            own = re.search(r'<nav class="subnav".*?</nav>', self.html[lang], re.S).group(0)
            self.assertRegex(own, rf'<a href="/{lang}/index/topics/"[^>]*aria-current="page"')

    def test_in_the_sitemap(self):
        sitemap = (self.dist / 'sitemap.xml').read_text()
        for lang in ('en', 'ar'):
            self.assertIn(f'<loc>https://djazair.dev/{lang}/index/topics/</loc>', sitemap)

    def test_topic_names_stay_left_to_right(self):
        ar = self.main('ar')
        self.assertIn('<span class="topic-n" lang="en" dir="ltr">machine-learning</span>', ar)
        self.assertNotIn('dir=ltr>', ar)


class HighlightedBars(unittest.TestCase):
    """The bar chart's highlight and difference options, used for economies side by side."""

    def chart(self, **kw):
        bars = [HBar('EG', 'Egypt', 37, 18), HBar('DZ', 'Algeria', 3, 2), HBar('LY', 'Libya', 0, 1)]
        return HBarChart(id='t', quarter='2026-Q1', title='T', summary='S', bars=bars, fmt=lambda v, lang: str(v),
                         change_fmt=lambda v, lang: f'{v:+}', before_label='Q1 2025', added_label='Added', **kw)

    def test_only_the_highlighted_bar_is_green(self):
        svg = charts.drawing(self.chart(highlight='DZ', highlight_label='Algeria', change_kind='diff'), 'en', 'wide').body
        pal = charts.DARK
        green = re.findall(rf'<rect[^>]*fill="{pal["algeria"]}"', svg)
        self.assertEqual(len(green), 1)                                           # Algeria's added part
        self.assertEqual(len(re.findall(rf'fill="{pal["peer"]}"', svg)), 1)      # Egypt's added part
        legend = charts.legend_items(self.chart(highlight='DZ', highlight_label='Algeria'), 'en', pal)
        self.assertEqual([text for _, _, text in legend], ['Q1 2025', 'Added', 'Algeria'])

    def test_change_as_a_difference(self):
        chart = self.chart(change_kind='diff')
        self.assertEqual([chart.change(b) for b in chart.bars], [19, 1, -1])
        self.assertAlmostEqual(self.chart().change(chart.bars[0]), 37 / 18 - 1)
        self.assertIn('-1', charts.drawing(chart, 'en', 'wide').body)

    def test_without_highlight_every_bar_is_green(self):
        svg = charts.drawing(self.chart(), 'en', 'wide').body
        self.assertEqual(len(re.findall(rf'<rect[^>]*fill="{charts.DARK["algeria"]}"', svg)), 2)     # Egypt's and Algeria's gains


if __name__ == '__main__':
    unittest.main()
