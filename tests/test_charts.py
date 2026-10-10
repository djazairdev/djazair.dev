"""The chart kit (ticket #7): scales, labels, drawings, downloads and data tables."""
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

from djsite import charts, unitmap  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import LANGS  # noqa: E402
from djsite.charts import (Bar, BarChart, Line, LineChart, UnitMap, nice_ticks, place_labels,  # noqa: E402
                           tick_compact, tick_decimals)
from djsite.fmt import fint, fpct  # noqa: E402
from djsite.palette import DARK, LIGHT  # noqa: E402
from htmlcheck import Doc, resolve, stylesheet  # noqa: E402

QUARTERS = [f'{y}-Q{q}' for y in range(2020, 2027) for q in range(1, 5)][:25]


def sample_line(**kw) -> LineChart:
    grow = lambda start, rate: [round(start * rate ** i) for i in range(25)]
    spec = dict(id='t-accounts', quarter='2026-Q1', title={'en': 'Developer accounts', 'ar': 'حسابات المطوّرين'},
                summary='Test chart.', unit={'en': 'Accounts', 'ar': 'الحسابات'}, x=QUARTERS,
                fmt=lambda v, lang: fint(v, lang), tick_fmt=tick_compact,
                lines=[Line('MA', {'en': 'Morocco', 'ar': 'المغرب'}, grow(142405, 1.08)),
                       Line('TN', {'en': 'Tunisia', 'ar': 'تونس'}, grow(88631, 1.067)),
                       Line('KE', {'en': 'Kenya', 'ar': 'كينيا'}, grow(90770, 1.087), 'hl'),
                       Line('median', {'en': 'N. Africa median', 'ar': 'وسيط شمال أفريقيا'}, grow(88631, 1.066), 'median'),
                       Line('DZ', {'en': 'Algeria', 'ar': 'الجزائر'}, grow(91819, 1.08), 'dz')])
    spec.update(kw)
    return LineChart(**spec)


def text_items(svg: str):
    """(attributes, text) for every <text> in an SVG string."""
    return [(dict(re.findall(r'([\w:-]+)="([^"]*)"', attrs)), re.sub(r'<[^>]+>', '', body))
            for attrs, body in re.findall(r'<text ([^>]*)>(.*?)</text>', svg)]


class Scales(unittest.TestCase):
    def test_nice_ticks(self):
        self.assertEqual(nice_ticks(0, 1_794_519), [0, 500_000, 1_000_000, 1_500_000, 2_000_000])
        self.assertEqual(nice_ticks(0, 0.6, 4), [0, 0.2, 0.4, 0.6])
        self.assertEqual(nice_ticks(0, 1033, 5), [0, 250, 500, 750, 1000, 1250])
        self.assertEqual(nice_ticks(-0.074, 0.49), [-0.2, 0, 0.2, 0.4, 0.6])

    def test_tick_decimals(self):
        self.assertEqual([tick_decimals(s) for s in (100, 0.5, 0.25, 0.01, 0.005)], [0, 1, 2, 2, 3])

    def test_labels_never_collide_and_keep_their_order(self):
        targets = [100, 103, 104, 180, 181, 300, 101]
        ys = place_labels(targets, 19, 0, 400)
        order = sorted(range(len(targets)), key=lambda i: (targets[i], i))
        placed = [ys[i] for i in order]
        for a, b in zip(placed, placed[1:]):
            self.assertGreaterEqual(b - a, 19 - 1e-9)
        self.assertEqual(ys[5], 300)                 # a label with room stays at its line
        self.assertTrue(all(0 <= y <= 400 for y in ys))

    def test_labels_stay_inside_the_plot(self):
        ys = place_labels([2, 3, 4], 20, 0, 400)
        self.assertEqual(sorted(ys), [0, 20, 40])
        ys = place_labels([399, 400, 398], 20, 0, 400)
        self.assertEqual(sorted(ys), [360, 380, 400])


class LineCharts(unittest.TestCase):
    def test_same_data_same_svg(self):
        a = charts.svg(sample_line(), 'en', 'wide', 'x', 'desc')
        b = charts.svg(sample_line(), 'en', 'wide', 'x', 'desc')
        self.assertEqual(a, b)
        self.assertEqual(charts.download_svg(sample_line(), 'ar', LIGHT), charts.download_svg(sample_line(), 'ar', LIGHT))

    def test_time_runs_left_to_right_in_both_languages(self):
        for lang in ('en', 'ar'):
            for size in ('wide', 'narrow'):
                svg = str(charts.svg(sample_line(), lang, size, 'x', 'desc'))
                with self.subTest(lang=lang, size=size):
                    self.assertIn('direction="ltr"', svg.split('>', 1)[0])
                    years = {t: float(a['x']) for a, t in text_items(svg) if re.fullmatch(r'20\d\d', t)}
                    self.assertLess(years['2020'], years['2026'])

    def test_end_labels_do_not_overlap(self):
        for lang in ('en', 'ar'):
            svg = str(charts.svg(sample_line(), lang, 'wide', 'x', 'desc'))
            ys = sorted(float(a['y']) for a, _ in text_items(svg) if 'lb' in a.get('class', '').split())
            self.assertEqual(len(ys), 5)
            for a, b in zip(ys, ys[1:]):
                self.assertGreaterEqual(b - a, 19 - 0.05, lang)

    def test_arabic_words_read_right_to_left_and_figures_left_to_right(self):
        svg = str(charts.svg(sample_line(), 'ar', 'wide', 'x', 'desc'))
        label = next(a for a, t in text_items(svg) if t.startswith('الجزائر'))
        self.assertEqual(label['direction'], 'rtl')
        self.assertRegex(svg, r'<tspan [^>]*direction="ltr"[^>]*>[\d.]+</tspan>')

    def test_highlight_median_and_algeria_use_their_colours(self):
        svg = str(charts.svg(sample_line(), 'en', 'wide', 'x', 'desc'))
        self.assertRegex(svg, rf'class="ln-dz k-DZ ln"[^>]*stroke="{DARK["algeria"]}"')
        self.assertRegex(svg, rf'class="ln-hl k-KE ln"[^>]*stroke="{DARK["highlight"]}"')
        self.assertRegex(svg, rf'class="ln-median k-median fd"[^>]*stroke="{DARK["median"]}"[^>]*stroke-dasharray')
        self.assertLess(svg.index('k-MA'), svg.index('k-DZ'), 'Algeria is drawn last, on top')

    def test_indexed_charts_draw_a_dashed_baseline(self):
        svg = str(charts.svg(sample_line(baseline=100), 'en', 'wide', 'x', 'desc'))
        self.assertIn('stroke-dasharray="2 4"', svg)

    def test_csv_and_json_put_algeria_first_and_carry_the_licence(self):
        chart = sample_line()
        rows = list(csv.reader(io.StringIO(chart.csv().decode('utf-8'))))
        self.assertEqual(rows[0], ['quarter', 'DZ', 'median', 'MA', 'TN', 'KE'])
        self.assertEqual(rows[1][:2], ['2020-Q1', '91819'])
        self.assertEqual(len(rows), 26)
        data = json.loads(chart.json())
        self.assertEqual(data['licence'], 'CC0-1.0')
        self.assertIn('GitHub Innovation Graph', data['attribution'])
        self.assertEqual(data['series'][0]['name'], {'en': 'Algeria', 'ar': 'الجزائر'})


class Downloads(unittest.TestCase):
    COLOUR = re.compile(r'(?:fill|stroke|stop-color)="([^"]+)"')

    def colours(self, svg: bytes) -> set:
        found = set(self.COLOUR.findall(svg.decode('utf-8')))
        return {c for c in found if c not in ('none', '#fff') and not c.startswith('url(')}

    def test_light_and_dark_files_use_only_their_palette(self):
        bars = BarChart(id='t-bars', quarter='2026-Q1', title='Growth', summary='', bars=[Bar('2025', '2025', .256), Bar('2026', '2026', .491)],
                        fmt=lambda v, lang: fpct(v, 1, lang), highlight='2026', credit='Data: test')
        units = UnitMap(id='t-um', quarter='2026-Q1', title='Units', summary='', total=586990, start=393565,
                        start_label='Q1 2025', added_label='Added since', total_label='Q1 2026', square_label='1 square')
        for chart in (sample_line(credit='Data: test'), bars, units):
            for lang in ('en', 'ar'):
                for name, pal in (('dark', DARK), ('light', LIGHT)):
                    with self.subTest(chart=chart.id, lang=lang, theme=name):
                        svg = charts.download_svg(chart, lang, pal)
                        self.assertLessEqual(self.colours(svg), set(pal.values()))
                        self.assertIn(f'fill="{pal["paper"]}"', svg.decode())

    def test_downloads_carry_the_credit(self):
        svg = charts.download_svg(sample_line(credit={'en': 'Data: GitHub Innovation Graph (CC0)', 'ar': 'x'}), 'en', LIGHT).decode()
        self.assertIn('Data: GitHub Innovation Graph (CC0)', svg)
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', svg)


class UnitMaps(unittest.TestCase):
    def test_one_square_per_thousand_accounts(self):
        chart = UnitMap(id='u', quarter='2026-Q1', title='', summary='', total=586990, start=393565)
        self.assertEqual(chart.squares, (587, 193))
        m = chart.layout()
        self.assertEqual((m.total, m.added), (587, 193))

    def test_the_same_numbers_give_the_same_map(self):
        unitmap.layout.cache_clear()
        a = unitmap.layout(120, 40)
        unitmap.layout.cache_clear()
        b = unitmap.layout(120, 40)
        self.assertEqual(a, b)

    def test_squares_sit_inside_the_outline(self):
        m = unitmap.layout(587, 193)
        geo = unitmap.outline()
        poly = [(x * 0.6, y * 0.6) for x, y in geo['outline']]
        def near_edge(x, y):     # stored coordinates are rounded to 0.01
            return min(unitmap._seg_dist(x, y, *poly[i], *poly[(i + 1) % len(poly)]) for i in range(len(poly))) < 0.01
        for c in m.cells:
            x, y = c.x + m.pitch / 2, c.y + m.pitch / 2
            self.assertTrue(unitmap.inside(x, y, poly) or near_edge(x, y), c)

    def test_maps_are_never_mirrored(self):
        chart = UnitMap(id='u', quarter='2026-Q1', title='', summary='', total=586990, start=393565)
        self.assertEqual(charts.unit_drawing(chart, 'en').body, charts.unit_drawing(chart, 'ar').body)

    def test_a_replay_adds_each_year_to_the_one_before(self):
        history = (('2024-Q1', 313294), ('2025-Q1', 393565), ('2026-Q1', 586990))
        chart = UnitMap(id='u', quarter='2026-Q1', title='', summary='', total=586990, start=393565, history=history)
        self.assertEqual(chart.steps(), (313, 394, 587))
        m = chart.layout()
        self.assertEqual([sum(c.step == k for c in m.cells) for k in range(3)], [313, 81, 193])
        self.assertEqual({c for c in m.cells if c.step == 2}, {c for c in m.cells if c.new}, 'the latest year is the bright one')
        plain = UnitMap(id='u', quarter='2026-Q1', title='', summary='', total=586990, start=393565).layout()
        self.assertEqual([(c.x, c.y, c.new) for c in m.cells], [(c.x, c.y, c.new) for c in plain.cells], 'the same picture')
        d = charts.unit_drawing(chart, 'en')
        self.assertEqual(d.cls, 'um um-years')
        self.assertEqual(re.findall(r'<g class="(s\d[^"]*)"', d.body), ['s0', 's1', 's2 um-new'])
        head, rows = charts.table(chart, 'en', {k: k for k in ('quarter', 'series', 'accounts', 'squares')})
        self.assertEqual(head[0][0], 'quarter')
        self.assertEqual([key for key, _ in rows], ['2024-Q1', '2025-Q1', '2026-Q1'])

    def test_a_replay_must_add_up(self):
        with self.assertRaises(ValueError):
            unitmap.layout(587, 193, history=(400, 394, 587))     # a year with fewer squares than the one before
        with self.assertRaises(ValueError):
            unitmap.layout(587, 193, history=(300, 587))          # the year before isn't 587 - 193


class Figures(unittest.TestCase):
    """The chart figures on the built component pages."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, dev=True, quiet=True, published=LANGS)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def pages(self):
        return [(lang, (self.dist / lang / '_dev' / 'components' / 'index.html').read_text('utf-8')) for lang in ('en', 'ar')]

    def test_every_chart_is_an_image_with_a_title_and_description(self):
        for lang, html in self.pages():
            doc = Doc(html)
            svgs = doc.find('svg', role='img')
            charts_found = [s for s in svgs if 'chart' in s.get('class', '').split()]
            self.assertGreaterEqual(len(charts_found), 9, lang)
            for s in charts_found:
                title, desc = s['aria-labelledby'].split()
                self.assertIn(title, doc.ids)
                self.assertIn(desc, doc.ids)

    def test_every_figure_has_a_data_table_and_downloads(self):
        for lang, html in self.pages():
            figures = re.findall(r'<figure class="frame fig".*?</figure>', html, re.S)
            self.assertEqual(len(figures), 5, lang)
            for fig in figures:
                with self.subTest(lang=lang, figure=fig[:120]):
                    self.assertIn('<table class="dt"', fig)
                    links = re.findall(r'<a href="(/charts/[^"]+)" download="([^"]+)"', fig)
                    kinds = sorted(name.rsplit('.', 1)[1] for _, name in links)
                    self.assertEqual(kinds, ['csv', 'json', 'png', 'png', 'svg', 'svg'])
                    for href, _ in links:
                        self.assertTrue(resolve(self.dist, href).is_file(), href)
                    self.assertEqual(fig.count('<li hidden data-png>'), 2)

    def test_csv_and_json_are_shared_by_both_languages(self):
        en = set(re.findall(r'href="(/charts/[^"]+\.(?:csv|json))"', self.pages()[0][1]))
        ar = set(re.findall(r'href="(/charts/[^"]+\.(?:csv|json))"', self.pages()[1][1]))
        self.assertEqual(en, ar)
        self.assertEqual(len(en), 10)

    def test_chart_motion_only_runs_when_motion_is_welcome(self):
        css = stylesheet(self.dist)
        inside, outside, pos = '', '', 0
        for m in re.finditer(r'@media \(prefers-reduced-motion: ?no-preference\)', css):
            depth, i = 0, css.index('{', m.start())
            while True:                               # find the end of that block
                depth += {'{': 1, '}': -1}.get(css[i], 0)
                if depth == 0:
                    break
                i += 1
            outside += css[pos:m.start()]
            inside += css[m.start():i]
            pos = i
        outside += css[pos:]
        for marker in ('animation-timeline', '.draw-wait', '.draw-go', '.um .o rect', '.um .n rect'):
            self.assertIn(marker, inside)
            self.assertNotIn(marker, outside)

    def test_the_build_is_deterministic(self):
        other = self.tmp / 'again'
        build(other, dev=True, quiet=True, published=LANGS)
        first = {p.relative_to(self.dist): p.read_bytes() for p in self.dist.rglob('*') if p.is_file()}
        second = {p.relative_to(other): p.read_bytes() for p in other.rglob('*') if p.is_file()}
        self.assertEqual(first.keys(), second.keys())
        for path in first:
            self.assertEqual(first[path], second[path], str(path))


if __name__ == '__main__':
    unittest.main()
