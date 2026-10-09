"""Quarterly reports (ticket #34; PRD §13): the text follows the editorial structure in both
languages, every claim it makes holds against its own quarter's data, every figure in it is
filled from that data, and the page has its five charts and the press kit.
A draft stays out of search until it is published."""
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite import editorial, reports  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import LANGS  # noqa: E402
from djsite.data import DERIVED_DIR, Derived  # noqa: E402
from djsite.markdown import _PLACEHOLDER, sections  # noqa: E402
from djsite.pages import report as page  # noqa: E402
from htmlcheck import Doc  # noqa: E402

# PRD §13: headline numbers, what changed, peers, one deep dive, caveats, what djazair.dev did;
# then the press kit (§14). The deep dive's id names its subject.
STRUCTURE = ['numbers', 'changes', 'peers', None, 'caveats', 'djazair', 'press']
FIGURES = ['report-units', 'report-growth', 'report-pushes', 'report-accounts', 'report-languages']


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html))


class Content(unittest.TestCase):
    """Every report in content/reports/, whatever its quarter."""

    def setUp(self):
        self.all = reports.all_reports()
        self.assertTrue(self.all, 'report no. 1 lives in content/reports/2026-q1/')

    def test_both_languages_follow_the_editorial_structure(self):
        for r in self.all:
            ids = {}
            for lang in LANGS:
                front, body = r.source(lang)
                with self.subTest(report=r.slug, lang=lang):
                    self.assertTrue(front['title'] and front['standfirst'])
                    ids[lang] = [s.id for s in sections(body)]
                    self.assertEqual(len(ids[lang]), len(STRUCTURE))
                    for want, got in zip(STRUCTURE, ids[lang]):
                        if want:
                            self.assertEqual(got, want)
            self.assertEqual(ids['en'], ids['ar'], 'the same sections, in the same order, in both languages')

    def test_both_languages_draw_the_same_blocks(self):
        for r in self.all:
            blocks = {lang: re.findall(r'^::: ?(\w[\w-]*.*)$', r.source(lang)[1], re.M) for lang in LANGS}
            with self.subTest(report=r.slug):
                self.assertEqual(blocks['en'], blocks['ar'])
                self.assertEqual([b.split()[1] for b in blocks['en'] if b.startswith('figure')],
                                 [f.removeprefix('report-') for f in FIGURES], 'the five charts of the press kit, in order')

    def test_every_claim_holds_against_its_own_quarter(self):
        for r in self.all:
            data = Derived(DERIVED_DIR / r.slug)
            with self.subTest(report=r.slug):
                self.assertEqual(data.quarter, r.quarter)
                self.assertTrue(r.checks, 'a report lists the claims its words make')
                self.assertEqual(editorial.verify(r.doc(), data), [])

    def test_a_published_report_has_a_date(self):
        for r in self.all:
            with self.subTest(report=r.slug):
                self.assertIn(r.status, reports.STATUSES)
                if not r.draft:
                    self.assertRegex(r.published, r'^\d{4}-\d{2}-\d{2}$')
                self.assertEqual(set(r.hub), {'projects', 'issues', 'date'})

    def test_front_matter(self):
        meta, body = reports.front_matter('---\ntitle: A: B\nstandfirst: C\n---\n## X {#x}\n')
        self.assertEqual(meta, {'title': 'A: B', 'standfirst': 'C'})
        self.assertEqual(body, '## X {#x}\n')
        for bad in ('title: A\n', '---\ntitle: A\n---\n', '---\ntitle A\nstandfirst: B\n---\n'):
            with self.subTest(text=bad), self.assertRaises(ValueError):
                reports.front_matter(bad)

    def test_language_names_in_placeholders(self):
        self.assertEqual(page.slug('C++'), 'cpp')
        self.assertEqual(page.slug('C#'), 'csharp')
        self.assertEqual(page.slug('Jupyter Notebook'), 'jupyter_notebook')
        self.assertEqual(page.slug('Objective-C'), 'objective_c')


class Claims(unittest.TestCase):
    """The check kinds reports use catch claims the data contradicts."""

    @classmethod
    def setUpClass(cls):
        cls.data = Derived(DERIVED_DIR / '2026-q1')

    def check(self, *checks) -> list:
        return editorial.verify({'quarter': '2026-Q1', 'checks': list(checks)}, self.data)

    def test_true_claims_pass(self):
        self.assertEqual(self.check(
            {'indicator': 'repos_per_account', 'falling': ['DZ'], 'from': '2025-Q1'},
            {'indicator': 'pushes_per_account', 'series': 'DZ', 'grew_at_least': 1.0, 'from': '2025-Q1'},
            {'indicator': 'yoy', 'series': 'DZ', 'streak': 'up', 'min': 4},
            {'indicator': 'accounts_per_million', 'series': 'DZ', 'equals': 'median_north_africa', 'from': '2026-Q1'},
            {'indicator': 'repos_per_account', 'group': 'africa', 'bottom': 5},
            {'language': 'Dockerfile', 'entered_top': 10}, {'language': 'Java', 'left_top': 10},
            {'language': 'HTML', 'always_first': True}, {'language': 'Python', 'grew_at_least': 1.0, 'rank_at_most': 4}), [])

    def test_false_claims_fail(self):
        false = [
            {'claim': 'accounts fell', 'indicator': 'accounts', 'falling': ['DZ'], 'from': '2025-Q1'},
            {'claim': 'repos doubled', 'indicator': 'repos_per_account', 'series': 'DZ', 'grew_at_least': 1.0, 'from': '2025-Q1'},
            {'claim': 'growth slowed', 'indicator': 'yoy', 'series': 'DZ', 'streak': 'down'},
            {'claim': 'growth sped up for five quarters', 'indicator': 'yoy', 'series': 'DZ', 'streak': 'up', 'min': 5},
            {'claim': 'pushes at the median', 'indicator': 'pushes_per_account', 'series': 'DZ', 'equals': 'median_north_africa', 'from': '2026-Q1'},
            {'claim': 'few accounts', 'indicator': 'accounts', 'group': 'africa', 'bottom': 5},
            {'claim': 'Java entered', 'language': 'Java', 'entered_top': 10},
            {'claim': 'Python left', 'language': 'Python', 'left_top': 10},
            {'claim': 'CSS always first', 'language': 'CSS', 'always_first': True},
            {'claim': 'C doubled', 'language': 'C', 'grew_at_least': 1.0},
            {'claim': 'Cobol', 'language': 'COBOL', 'rank_at_most': 10},
            {'claim': 'typo', 'language': 'Python', 'grows_at_least': 1.0},
        ]
        for claim in false:
            with self.subTest(claim=claim['claim']):
                failures = self.check(claim)
                self.assertEqual(len(failures), 1, failures)
                self.assertTrue(failures[0].startswith(claim['claim']))


def archived_routes():
    from djsite.context import Route
    from djsite.routes import ROUTES
    return list(ROUTES) + [Route('reports', 'reports/', page.render_index),
                           *(Route(r.key, r.path, page.render) for r in reports.all_reports())]


class ReportPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, routes=archived_routes(), quiet=True)
        cls.report = reports.all_reports()[-1]          # report no. 1
        cls.data = Derived(DERIVED_DIR / cls.report.slug)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def html(self, lang: str, path: str) -> str:
        return (self.dist / lang / path / 'index.html').read_text('utf-8')

    def main(self, lang: str, path: str) -> str:
        """The page without the inlined stylesheet."""
        html = self.html(lang, path)
        return html[html.index('<main'):html.index('</main>')]

    def test_every_figure_in_the_text_is_filled(self):
        for lang in LANGS:
            html = self.main(lang, self.report.path)
            with self.subTest(lang=lang):
                self.assertNotIn('{{', html)
                self.assertNotIn('}}', html)
                self.assertNotRegex(text_of(html), r'\{\w+\}', 'no catalog placeholder left')
        names = {m.group(1) for lang in LANGS for m in _PLACEHOLDER.finditer(self.report.source(lang)[1])}
        self.assertIn('lang.cpp.name', names, 'C++ is isolated in Arabic text')

    def test_numbers_come_from_its_quarter(self):
        ov = self.data.overview()
        en = text_of(self.html('en', self.report.path))
        ar = text_of(self.html('ar', self.report.path))
        self.assertIn('Algeria had 586,990 developer accounts on GitHub at the end of March 2026, 49.1% more', en)
        self.assertIn('Algeria added 54,107 developer accounts between Q4 2025 and Q1 2026, a rise of 10.2%.', en)
        self.assertIn('Growth has sped up for four quarters in a row', en)
        self.assertIn('Pushes per account more than doubled, from 0.51 to 1.06.', en)
        self.assertIn('Algeria is 6th of 29 by number of accounts but 19th of 29 by growth', en)
        self.assertIn('Python is 4th, with 6,383 developers (+125%)', en)
        self.assertIn('Java was 4th in Q1 2020; it is 12th now.', en)
        self.assertIn('586.990', ar)
        self.assertIn('ارتفع عدد الحسابات في الجزائر بمقدار 54.107 بين الربع الرابع 2025 والربع الأول 2026', ar)
        self.assertEqual(ov['accounts']['value'], 586990)

    def test_headline_numbers_name_their_source_and_quarter(self):
        doc = Doc(self.html('en', self.report.path))
        cards = re.findall(r'<div class="kf-card">(.*?)</div>', self.html('en', self.report.path), re.S)
        self.assertEqual(len(cards), 4)
        for card in cards:
            self.assertRegex(text_of(card), r'GitHub Innovation Graph · Q1 2026')
        self.assertEqual(doc.title, 'Algeria’s developer accounts, Q1 2026 · djazair.dev')

    def test_five_charts_with_their_files(self):
        for lang in LANGS:
            html = self.html(lang, self.report.path)
            ids = re.findall(r'<div class="fig-label" id="(report-[\w-]+)-label">', html)
            with self.subTest(lang=lang):
                self.assertEqual(ids, FIGURES)
                for chart in FIGURES:
                    for name in (f'{chart}.csv', f'{chart}.json', f'{lang}/{chart}-dark.svg', f'{lang}/{chart}-light.svg'):
                        self.assertTrue((self.dist / 'charts' / '2026-q1' / name).is_file(), name)
                        self.assertIn(f'/charts/2026-q1/{name}', html)

    def test_press_kit(self):
        path = self.dist / page.zip_path(self.report).lstrip('/')
        for lang in LANGS:
            self.assertIn(f'href="{page.zip_path(self.report)}" download', self.html(lang, self.report.path))
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            readme = z.read('djazair.dev-report-2026-q1/README.txt').decode('utf-8')
            summary = {lang: z.read(f'djazair.dev-report-2026-q1/methodology-summary-{lang}.txt').decode('utf-8') for lang in LANGS}
            csv = z.read('djazair.dev-report-2026-q1/data/report-units.csv').decode('utf-8')
        self.assertEqual(len(names), 3 + len(FIGURES) * 6, 'README, two summaries; per chart CSV, JSON and four SVGs')
        for chart in FIGURES:
            for lang in LANGS:
                self.assertIn(f'djazair.dev-report-2026-q1/{lang}/{chart}-light.svg', names)
        self.assertIn('DRAFT', readme)
        self.assertIn('https://djazair.dev/ar/reports/2026-q1/', readme)
        self.assertIn('Source: GitHub Innovation Graph, Q1 2026 data, released on 7 July 2026 (CC0).', summary['en'])
        self.assertNotIn('**', summary['en'])
        self.assertIn('7 جويلية 2026', summary['ar'])
        self.assertIn('total,586990,587', csv)
        again = build(self.tmp / 'again', routes=archived_routes(), quiet=True)
        self.assertEqual((self.tmp / 'again' / page.zip_path(self.report).lstrip('/')).read_bytes(), path.read_bytes(),
                         'the same report always gives the same file')
        self.assertTrue(again.files)

    def test_tables(self):
        html = self.html('en', self.report.path)
        for caption in ('Algeria’s indicators in Q1 2026, a quarter earlier and a year earlier',
                        'Algeria and the peer-group medians, Q1 2026, with Algeria’s ranks',
                        'Algeria’s top languages, Q1 2026, with their ranks over time'):
            self.assertIn(f'<caption class="sr-only">{caption}</caption>', html)
        langs = re.search(r'rp-langs.*?</table>', html, re.S).group(0)
        self.assertEqual(len(re.findall(r'<tr class="" data-key=|<tr data-key=', langs)), 12, 'top ten, plus Java and C++')

    def test_a_draft_stays_out_of_search_and_says_so(self):
        for lang in LANGS:
            html = self.html(lang, self.report.path)
            with self.subTest(lang=lang):
                self.assertIn('<meta name="robots" content="noindex">', html)
                self.assertIn('class="callout rp-note"', html)
        self.assertNotIn(f'/en/{self.report.path}', (self.dist / 'sitemap.xml').read_text('utf-8'))
        self.assertIn('This report is a draft.', self.html('en', self.report.path))

    def test_reports_page_links_to_it_without_a_duplicate_home_section(self):
        for lang in LANGS:
            url = f'/{lang}/{self.report.path}'
            with self.subTest(lang=lang):
                html = self.html(lang, 'reports/')
                self.assertIn(f'href="{url}"', html)
                self.assertIn(f'href="{url}#press"', html)
                self.assertIn(f'href="{url}#languages"', html, 'the sections are listed')
                self.assertNotIn('id="report"', self.html(lang, ''))
        self.assertIn('Five rules for every report', text_of(self.html('en', 'reports/')))


class Published(unittest.TestCase):
    """The same report once published, and once GitHub has re-released its quarter."""

    def build(self, **changes) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        folder = tmp / 'reports' / '2026-q1'
        shutil.copytree(reports.REPORTS_DIR / '2026-q1', folder)
        doc = json.loads((folder / 'report.json').read_text('utf-8'))
        (folder / 'report.json').write_text(json.dumps({**doc, **changes}), 'utf-8')
        with mock.patch.object(reports, 'REPORTS_DIR', tmp / 'reports'):
            build(tmp / 'dist', routes=archived_routes(), quiet=True)
        return tmp / 'dist'

    def test_a_published_report_is_indexed(self):
        dist = self.build(status='published', published='2026-11-30')
        html = (dist / 'en' / 'reports' / '2026-q1' / 'index.html').read_text('utf-8')
        self.assertNotIn('noindex', html)
        self.assertIn('<link rel="canonical" href="https://djazair.dev/en/reports/2026-q1/">', html)
        self.assertIn('Published', text_of(html))
        self.assertIn('30 Nov 2026', text_of(html))
        self.assertNotIn('class="callout rp-note"', html)
        self.assertIn('https://djazair.dev/ar/reports/2026-q1/', (dist / 'sitemap.xml').read_text('utf-8'))
        with zipfile.ZipFile(next((dist / 'reports' / '2026-q1').glob('*.zip'))) as z:
            self.assertNotIn('DRAFT', z.read('djazair.dev-report-2026-q1/README.txt').decode('utf-8'))
        self.assertIn('Published 30 November 2026', text_of((dist / 'en' / 'reports' / 'index.html').read_text('utf-8')))

    def test_a_re_released_quarter_is_flagged(self):
        dist = self.build(release='0' * 40)
        html = (dist / 'en' / 'reports' / '2026-q1' / 'index.html').read_text('utf-8')
        self.assertIn('GitHub has re-released this quarter’s data.', html)

    def test_a_published_report_needs_its_date(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(reports.REPORTS_DIR / '2026-q1', tmp / '2026-q1')
        doc = json.loads((tmp / '2026-q1' / 'report.json').read_text('utf-8'))
        (tmp / '2026-q1' / 'report.json').write_text(json.dumps({**doc, 'status': 'published'}), 'utf-8')
        with self.assertRaises(ValueError):
            reports.all_reports(tmp)


if __name__ == '__main__':
    unittest.main()
