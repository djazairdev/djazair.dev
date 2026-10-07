"""Collaboration (ticket #37, IDX-10): where pushes and pull requests from developers in Algeria
went and where those to repositories owned in Algeria came from, against a year earlier and
since 2020; every listed economy both ways; the EU left out of rankings and totals; the
sentences computed from the data."""
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
sys.path.insert(0, str(ROOT))

from djsite import charts, data  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.charts import HBar, HBarChart  # noqa: E402
from djsite.i18n import Catalog  # noqa: E402
from djsite.pages import collaboration  # noqa: E402
from pipeline import config  # noqa: E402

BASELINE = '2026-Q1'           # the quarter the hand-checked expectations below describe


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class CollaborationPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'collaboration' / 'index.html').read_text('utf-8')
                    for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def main(self, lang: str) -> str:
        return re.search(r'<main.*?</main>', self.html[lang], re.S).group(0)

    def figure_csv(self, chart_id: str) -> list:
        return list(csv.DictReader(io.StringIO((self.dist / 'charts' / '2026-q1' / f'{chart_id}.csv').read_text())))

    def both_rows(self, lang: str) -> tuple:
        section = re.search(r'<section class="section section-s" id="both".*?</section>', self.html[lang], re.S).group(0)
        body = section.split('<tbody>')[1].split('</tbody>')[0]
        foot = section.split('<tfoot>')[1].split('</tfoot>')[0]
        return dict(re.findall(r'<tr[^>]*data-key="([\w-]+)">(.*?)</tr>', body, re.S)), foot

    @unittest.skipUnless(data.load().quarter == BASELINE, 'expectations describe the 2026-Q1 data')
    def test_partners_match_the_prd(self):
        """PRD A.5: United States 2,612, then France, Germany, Jordan; the EU aggregate isn't a bar."""
        sent = self.figure_csv('collaboration-sent')
        self.assertEqual([(r['key'], int(r['value'])) for r in sent][:7],
                         [('US', 2612), ('FR', 1232), ('DE', 791), ('JO', 608), ('GB', 504), ('IN', 359), ('CH', 242)])
        self.assertEqual([r['rank'] for r in sent], [str(i) for i in range(1, len(sent) + 1)])
        self.assertEqual(int(sent[0]['year_earlier']), 1188)
        self.assertEqual(sent[3]['year_earlier'], '', 'Jordan wasn’t listed a year earlier: unknown, not zero')
        received = self.figure_csv('collaboration-received')
        self.assertEqual([(r['key'], int(r['value'])) for r in received][:4], [('FR', 809), ('BR', 800), ('LU', 432), ('US', 307)])
        self.assertEqual(collaboration.total(self.data, 'sent'), 7057)
        self.assertEqual(collaboration.total(self.data, 'received'), 3485)

    @unittest.skipUnless(data.load().quarter == BASELINE, 'expectations describe the 2026-Q1 data')
    def test_sentences_follow_the_data(self):
        en, ar = text_of(self.main('en')), text_of(self.main('ar'))
        self.assertIn('In Q1 2026, repositories owned in the United States received the most pushes and pull requests from '
                      'developers in Algeria: 2,612 , up from 1,188 a year earlier. Next came France, with 1,232 , and '
                      'Germany, with 791 .', en)
        self.assertIn('GitHub also lists the European Union, at 2,181 : the sum of France, Germany and the Netherlands above.', en)
        self.assertIn('the sum of France, Luxembourg, Spain and the Netherlands above', en)
        self.assertIn('Repositories owned in Algeria received 3,485 pushes and pull requests from the economies listed, against '
                      '1,312 a year earlier. The most came from France: 809 .', en)
        self.assertIn('In Q1 2020, developers in Algeria sent 2,777 pushes', en)
        self.assertIn('In Q1 2026: 7,057 sent and 3,485 received.', en)
        self.assertIn('في الولايات المتحدة الوجهة الأولى', ar)
        self.assertIn('ارتفاعًا من 1.188 قبل عام', ar)
        self.assertIn('مجموع فرنسا وألمانيا وهولندا أعلاه', ar)

    def test_the_lede_direction_matches_the_data(self):
        first, now, _ = collaboration.ranked(self.data, 'sent')[0]
        before = collaboration.partners(self.data, 'sent', collaboration.year_earlier(self.data.quarter)).get(first)
        expected = ('GitHub didn’t list them a year earlier' if before is None else 'up from' if now > before
                    else 'down from' if now < before else 'the same as a year earlier')
        self.assertIn(expected, text_of(self.main('en')))

    def test_the_eu_is_never_ranked_or_added(self):
        for chart_id in ('collaboration-sent', 'collaboration-received'):
            self.assertNotIn('EU', [r['key'] for r in self.figure_csv(chart_id)])
        trend = self.figure_csv('collaboration-trend')[-1]
        self.assertEqual(int(trend['sent']), sum(w for p, w in collaboration.partners(self.data, 'sent').items() if p != 'EU'))
        for lang in ('en', 'ar'):
            rows, _ = self.both_rows(lang)
            self.assertNotIn('EU', rows)

    def test_both_ways_table(self):
        sent, received = collaboration.partners(self.data, 'sent'), collaboration.partners(self.data, 'received')
        expected = sorted((set(sent) | set(received)) - {'EU'}, key=lambda c: (-sent.get(c, 0), -received.get(c, 0), c))
        for lang in ('en', 'ar'):
            rows, foot = self.both_rows(lang)
            self.assertEqual(list(rows), expected)
            for code, row in rows.items():
                cells = re.findall(r'<td class="end"( data-v="[^"]*")?>(.*?)</td>', row)
                self.assertEqual(len(cells), 2)
                for (attr, html), side in zip(cells, (sent, received)):
                    if code in side:
                        self.assertEqual(attr, f' data-v="{side[code]}"')
                    else:
                        self.assertEqual((attr, html), (' data-v=""', '—'))
            self.assertIn(f'data-v="{collaboration.total(self.data, "sent")}"', foot)
            self.assertIn(f'data-v="{collaboration.total(self.data, "received")}"', foot)

    def test_three_figures_with_downloads_and_tables(self):
        for lang in ('en', 'ar'):
            main = self.main(lang)
            self.assertEqual(len(re.findall(r'<details class="disclosure fig-table"', main)), 3)
            for chart_id in ('collaboration-sent', 'collaboration-received', 'collaboration-trend'):
                self.assertIn(f'/charts/2026-q1/{chart_id}.csv', main)
                for theme in ('dark', 'light'):
                    self.assertTrue((self.dist / 'charts' / '2026-q1' / lang / f'{chart_id}-{theme}.svg').is_file())
            self.assertIn('/data/2026-q1/collaboration.csv', main)
        trend = (self.dist / 'charts' / '2026-q1' / 'collaboration-trend.csv').read_text().splitlines()
        self.assertEqual(trend[0], 'quarter,sent,received')
        self.assertEqual(len(trend), 1 + len(self.data.quarters))

    def test_in_the_index_navigation_the_footer_and_the_sitemap(self):
        sitemap = (self.dist / 'sitemap.xml').read_text()
        for lang in ('en', 'ar'):
            overview = (self.dist / lang / 'index' / 'index.html').read_text('utf-8')
            sub = re.search(r'<nav class="subnav".*?</nav>', overview, re.S).group(0)
            self.assertIn(f'href="/{lang}/index/collaboration/"', sub)
            footer = re.search(r'<footer.*?</footer>', overview, re.S).group(0)
            self.assertIn(f'href="/{lang}/index/collaboration/"', footer)
            own = re.search(r'<nav class="subnav".*?</nav>', self.html[lang], re.S).group(0)
            self.assertRegex(own, rf'<a href="/{lang}/index/collaboration/"[^>]*aria-current="page"')
            self.assertIn(f'<loc>https://djazair.dev/{lang}/index/collaboration/</loc>', sitemap)
            self.assertIn(f'/{lang}/methodology/#collaboration', self.main(lang))
            methodology = (self.dist / lang / 'methodology' / 'index.html').read_text('utf-8')
            self.assertIn('id="collaboration"', methodology)


class Names(unittest.TestCase):
    def test_every_partner_since_2020_has_a_name_in_both_languages(self):
        catalog = Catalog(ROOT / 'site' / 'i18n')
        codes = {r['partner'] for r in data.load().rows('collaboration')}
        for lang in ('en', 'ar'):
            missing = sorted(c for c in codes if not any(
                catalog.flat[lang].get(f'{group}.{c}') for group in ('economy', 'world')))
            self.assertEqual(missing, [], lang)

    def test_names_in_running_text_take_the_article(self):
        catalog = Catalog(ROOT / 'site' / 'i18n')
        self.assertEqual(catalog.flat['en']['world_the.US'], 'the United States')
        keys = {lang: {k for k in catalog.flat[lang] if k.startswith('world_the.')} for lang in ('en', 'ar')}
        self.assertEqual(keys['en'], keys['ar'])
        self.assertTrue(all(catalog.flat['en'][k].startswith('the ') for k in keys['en']))

    def test_the_eu_members_match_the_pipeline(self):
        self.assertEqual(collaboration.EU_MEMBERS, config.EU_MEMBERS)
        self.assertEqual(len(set(config.EU_MEMBERS)), 27)


class SingleColourBars(unittest.TestCase):
    """``split=False``: one green per bar, and 'new' where the year earlier is unknown."""

    def chart(self, **kw):
        bars = [HBar('US', 'United States', 2612, 1188, 1), HBar('JO', 'Jordan', 608, None, 2), HBar('IN', 'India', 359, 400, 3)]
        return HBarChart(id='t', quarter='2026-Q1', title='T', summary='S', bars=bars, fmt=lambda v, lang: str(v),
                         change_fmt=lambda v, lang: f'{v:+.0%}', before_label='Q1 2025', change_label='Change', **kw)

    def test_one_colour_and_the_new_label(self):
        svg = charts.drawing(self.chart(split=False, new_label={'en': 'new', 'ar': 'جديد'}), 'en', 'wide').body
        self.assertEqual(len(re.findall(rf'<rect[^>]*fill="{charts.DARK["algeria"]}"', svg)), 3)
        self.assertNotIn('class="hb-o', svg)
        self.assertNotIn('class="hb-l', svg, 'a loss is in the change, not drawn')
        self.assertIn('>new</text>', svg)
        self.assertIn('>-10%</text>', svg)
        self.assertIn('جديد', charts.drawing(self.chart(split=False, new_label={'en': 'new', 'ar': 'جديد'}), 'ar', 'wide').body)

    def test_no_legend_and_the_label_in_the_table(self):
        chart = self.chart(split=False, new_label='new')
        self.assertEqual(charts.legend_items(chart, 'en', charts.DARK), [])
        _, rows = charts.table(chart, 'en', {})
        self.assertEqual(dict(rows)['JO'][3], ('new', None))
        _, rows = charts.table(self.chart(), 'en', {})
        self.assertEqual(dict(rows)['JO'][3], ('—', None))

    def test_the_scale_follows_the_bars_drawn(self):
        """A larger year-earlier value doesn't shrink the bar when it isn't drawn."""
        width = lambda svg, cls: float(re.search(rf'<rect[^>]*width="([\d.]+)"[^>]*class="{cls}', svg).group(1))
        bars = [HBar('A', 'A', 100, 400)]
        split = HBarChart(id='t', quarter='2026-Q1', title='T', summary='S', bars=bars, fmt=lambda v, lang: str(v),
                          change_fmt=lambda v, lang: str(v))
        single = HBarChart(id='t', quarter='2026-Q1', title='T', summary='S', bars=bars, fmt=lambda v, lang: str(v),
                           change_fmt=lambda v, lang: str(v), split=False)
        kept = width(charts.drawing(split, 'en', 'wide').body, 'hb-o')
        self.assertAlmostEqual(width(charts.drawing(single, 'en', 'wide').body, 'hb-n'), 4 * kept, delta=1)


if __name__ == '__main__':
    unittest.main()
