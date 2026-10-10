"""Methodology and About (ticket #23): formulas that match the pipeline, a worked example that
recomputes from the published counts, every section in both languages, the logs, and the
small Markdown renderer the content uses."""
import html
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'site'))

from pipeline import indicators  # noqa: E402
from djsite import data  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import LANGS  # noqa: E402
from djsite.fmt import fdec, fint, fpct  # noqa: E402
from djsite.markdown import Renderer, items, sections  # noqa: E402
from djsite.markup import Markup  # noqa: E402
from djsite.pages.methodology import days_text  # noqa: E402

SECTIONS = ['what', 'sources', 'indicators', 'peer-groups', 'limitations', 'updates', 'corrections']
ARITHMETIC = ('accounts', 'yoy', 'since_2020', 'pushes_per_account', 'repos_per_account', 'orgs_per_account',
              'accounts_per_million')


def text_of(s: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s)))


def normal(formula: str) -> str:
    """Formulas as the pipeline docstring writes them and as the page does: same maths."""
    formula = formula.replace('−', '-').replace('(World Bank, latest year)', '')
    return re.sub(r'\s+', '', formula)


def pipeline_formulas() -> dict:
    out = {}
    for line in indicators.__doc__.splitlines():
        m = re.match(r'^\s{4}(\w+)\s{2,}(.+)$', line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


class MethodologyPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True, published=LANGS)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'data' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}
        cls.about = {lang: (cls.dist / lang / 'about' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_definitions_live_in_expandable_data_panels(self):
        for lang in ('en', 'ar'):
            found = re.findall(r'<details class="data-method" id="([\w-]+)"', self.html[lang])
            self.assertEqual(found, ['sources', 'indicators', 'peer-groups', 'limitations', 'updates'])
            self.assertIn('id="languages"', self.html[lang])
            toc = re.search(r'<nav class="toc".*?</nav>', self.html[lang], re.S).group(0)
            self.assertIn('href="#reading"', toc)

    def test_formulas_match_the_pipeline(self):
        expected = pipeline_formulas()
        for lang in ('en', 'ar'):
            for key in ARITHMETIC:
                with self.subTest(lang=lang, key=key):
                    item = re.search(rf'<div class="fm" id="{key}">.*?<code class="fm-f" dir="ltr">(.*?)</code>', self.html[lang], re.S)
                    self.assertIsNotNone(item, key)
                    self.assertEqual(normal(html.unescape(item.group(1))), normal(expected[key]))
            with self.subTest(lang=lang, key='pushes_per_account_4q'):
                self.assertIn(normal(expected['pushes_per_account_4q']), normal(text_of(self.html[lang])))

    def test_the_worked_example_recomputes_the_published_values(self):
        dz, ov = self.data.peers()['DZ'], self.data.overview()
        for lang in ('en', 'ar'):
            example = text_of(re.search(r'<figure class="example">.*?</figure>', self.html[lang], re.S).group(0))
            with self.subTest(lang=lang):
                self.assertIn(fpct(ov['yoy']['value'], 1, lang), example)
                self.assertIn(fdec(dz['pushes_per_account'], 2, lang), example)
                self.assertIn(fdec(dz['repos_per_account'], 2, lang), example)
                self.assertIn(fdec(dz['orgs_per_account'], 4, lang), example)
                self.assertIn(fint(dz['accounts_per_million'], lang), example)
                self.assertIn(f'{fint(dz["git_pushes"], lang)} / {fint(dz["accounts"], lang)}', example)
        self.assertAlmostEqual(dz['git_pushes'] / dz['accounts'], dz['pushes_per_account'], places=6)
        self.assertAlmostEqual(dz['accounts'] / dz['population'] * 1e6, dz['accounts_per_million'], places=4)

    def test_figures_in_the_text_come_from_the_data(self):
        text = text_of(self.html['en'])
        africa = next(r for r in self.data.rows('groups') if r['group'] == 'africa' and r['quarter'] == self.data.quarter)
        self.assertIn(f'({africa["members"]} in Q', text)
        self.assertIn(f'Only {self.data.overview()["topics"]["value"]} of Algeria’s topics clear it.', text)
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                self.assertNotIn('{{', self.html[lang])
                self.assertNotRegex(text_of(self.html[lang]), r'\{[a-z_]+\}')

    def test_the_release_timeline_ends_with_the_data_release(self):
        times = re.findall(r'<time datetime="([\d-]+)"', re.search(r'<ol class="rel-line">.*?</ol>', self.html['en'], re.S).group(0))
        self.assertEqual(len(times), 5)
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[-1], self.data.release_date)

    def test_logs_and_citation(self):
        page = self.html['en']
        self.assertIn('Q1 2026', text_of(page))
        self.assertIn('No corrections yet.', page)
        self.assertIn('issues/new?template=correction.yml', page)
        self.assertTrue((ROOT / '.github' / 'ISSUE_TEMPLATE' / 'correction.yml').is_file())
        cite = text_of(re.search(r'<p class="cite-text">.*?</p>', page, re.S).group(0))
        self.assertIn('https://djazair.dev/en/data/', cite)
        self.assertIn('Algeria Developer Index', cite)

    def test_about(self):
        for lang in ('en', 'ar'):
            page = self.about[lang]
            with self.subTest(lang=lang):
                emails = {e.rstrip('.') for e in re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text_of(page))}
                self.assertEqual(emails, {'contact@djazair.dev'})            # the project address only
                self.assertIn('class="md-table"', page.replace('table-wrap md-table', 'md-table'))
                self.assertNotIn('{{', page)
        self.assertIn('djazair.dev is not affiliated with GitHub', text_of(self.about['en']))
        self.assertIn('غير تابع لـGitHub', text_of(self.about['ar']))


class Markdown(unittest.TestCase):
    def setUp(self):
        self.md = Renderer(values={'n': 29, 'link': Markup('<a href="mailto:x@y">x</a>')},
                           link=lambda key, hash_: f'/en/{key}/' + (f'#{hash_}' if hash_ else ''))

    def test_inline(self):
        out = self.md.inline('**A** *b* `c * d` [e](route:trends#f) {{n}} {{link}} <script>')
        self.assertEqual(out, '<strong>A</strong> <em>b</em> <code dir="ltr">c * d</code> <a href="/en/trends/#f">e</a> 29 '
                              '<a href="mailto:x@y">x</a> &lt;script&gt;')

    def test_unknown_placeholders_and_directives_fail(self):
        with self.assertRaises(KeyError):
            self.md.inline('{{missing}}')
        with self.assertRaises(KeyError):
            self.md.render('::: nothing\n:::')
        with self.assertRaises(ValueError):
            self.md.render('::: open\nnot closed')

    def test_blocks(self):
        out = self.md.render('Para one\ncontinues.\n\n- a\n  b\n- c\n\n1. x\n2. y\n\n| H | I |\n|---|---|\n| **r** | v |\n')
        self.assertIn('<p>Para one continues.</p>', out)
        self.assertIn('<ul><li>a b</li><li>c</li></ul>', out)
        self.assertIn('<ol><li>x</li><li>y</li></ol>', out)
        self.assertIn('<th scope="row"><strong>r</strong></th><td>v</td>', out)

    def test_sections_and_items(self):
        secs = sections('ignored\n## One {#one}\ntext\n## Two {#two}\nmore\n')
        self.assertEqual([(s.id, s.title, s.body) for s in secs], [('one', 'One', 'text'), ('two', 'Two', 'more')])
        with self.assertRaises(ValueError):
            sections('## No id\ntext')
        self.assertEqual(items(['### A {#a}', 'x', '### B', 'y']), [('A', 'a', ['x']), ('B', None, ['y'])])

    def test_days_in_arabic(self):
        self.assertEqual([days_text(n, 'ar') for n in (1, 2, 3, 10, 11, 61, 99, 100, 103)],
                         ['يوم واحد', 'يومان', '3 أيام', '10 أيام', '11 يومًا', '61 يومًا', '99 يومًا', '100 يوم', '103 أيام'])
        self.assertEqual(days_text(83, 'en'), '83 days')


if __name__ == '__main__':
    unittest.main()
