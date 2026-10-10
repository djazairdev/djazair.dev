"""Accessibility (ticket #29).

Every built page passes the automated checks in tests/a11y.py in both languages, text on
tinted surfaces keeps WCAG AA contrast, focus is never hidden, and motion stops for people who
ask for less. The checks that need a person are listed in docs/accessibility.md.
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

import a11y  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import LANGS, PUBLISHED  # noqa: E402
from djsite.markdown import Renderer  # noqa: E402
from test_design_tokens import CSS_DIR, contrast, tokens  # noqa: E402

JS_DIR = ROOT / 'site' / 'static' / 'js'


def over(colour: str, base: str) -> str:
    """A token colour as it shows on ``base``: rgba() tints are blended, hex is kept."""
    m = re.fullmatch(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', colour)
    if not m:
        return colour
    r, g, b, a = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
    under = [int(base.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join(f'{round(c * a + u * (1 - a)):02x}' for c, u in zip((r, g, b), under))


class Pages(unittest.TestCase):
    """Every page as it ships, the invitations to translate at the Arabic addresses included (#61)."""
    PUBLISHED = PUBLISHED

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True, published=cls.PUBLISHED)
        cls.pages = sorted(cls.dist.rglob('*.html'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_every_page_passes_the_automated_checks(self):
        checked = {lang: 0 for lang in LANGS}
        for path in self.pages:
            rel = path.relative_to(self.dist)
            lang = rel.parts[0] if rel.parts[0] in LANGS else 'en'   # the root chooser and 404
            checked[lang] += 1
            with self.subTest(page=str(rel)):
                self.assertEqual(a11y.check(path.read_text('utf-8'), lang), [])
        for lang in LANGS:
            self.assertGreaterEqual(checked[lang], 12, f'too few {lang} pages: did the build change?')

    def test_tables_have_names(self):
        for lang in self.PUBLISHED:
            for page in ('about', 'data'):
                html = (self.dist / lang / page / 'index.html').read_text('utf-8')
                with self.subTest(lang=lang, page=page):
                    self.assertRegex(html, r'<caption class="sr-only">[^<]{12,}</caption>')

    def test_one_skip_link_per_page_and_it_lands_on_main(self):
        for lang in LANGS:
            html = (self.dist / lang / 'index.html').read_text('utf-8')
            first = re.search(r'<a [^>]*href="#([\w-]+)"', html)
            self.assertIsNotNone(first, lang)
            self.assertRegex(html, rf'<main id="{first.group(1)}" tabindex="-1"')


class PagesWithArabic(Pages):
    """The same checks with the Arabic pages built, as they will be once reviewed."""
    PUBLISHED = LANGS


class Checker(unittest.TestCase):
    """The checker catches what it says it catches, so a passing page means something."""
    PAGE = ('<!doctype html><html lang="{lang}" dir="{dir}"><head><title>T</title></head><body>'
            '<a href="#main">Skip</a><header><nav aria-label="Main"><a href="/">Home</a></nav></header>'
            '<main id="main" tabindex="-1"><h1>Title</h1>{body}</main></body></html>')

    def problems(self, body: str, lang: str = 'en') -> list:
        page = self.PAGE.format(lang=lang, dir='rtl' if lang == 'ar' else 'ltr', body=body)
        return a11y.check(page, lang)

    def test_a_clean_page_passes(self):
        self.assertEqual(self.problems('<p>Hello</p>'), [])
        self.assertEqual(self.problems('<p>مرحبا</p>', 'ar'), [])

    def test_what_it_catches(self):
        cases = {
            '<img src="x.png">': 'no alt',
            '<input type="text">': 'form field without a label',
            '<label for="q">Search</label><input id="q" type="search"><input type="checkbox" id="c">': 'form field without a label',
            '<button><svg aria-hidden="true"></svg></button>': 'button without a name',
            '<a href="/x"></a>': 'link without a name',
            '<a href="#nowhere">Jump</a>': 'missing id "nowhere"',
            '<p id="a">1</p><p id="a">2</p>': 'id "a" is used 2 times',
            '<div aria-labelledby="ghost" role="region"></div>': 'missing id "ghost"',
            '<h3>Too deep</h3>': 'heading level jumps from h1 to h3',
            '<h1>Second</h1>': '2 <h1> elements',
            '<h2></h2>': 'empty heading',
            '<div aria-hidden="true"><a href="/x">Hidden link</a></div>': 'focusable inside aria-hidden',
            '<span tabindex="2">x</span>': 'positive tabindex',
            '<div role="buton">x</div>': 'unknown role "buton"',
            '<svg viewBox="0 0 1 1"></svg>': 'an SVG must be aria-hidden',
            '<table><tr><td>1</td></tr></table>': 'table without a caption',
            '<table aria-label="T"><tr><th>A</th></tr></table>': 'header cell outside <thead> without scope',
            '<fieldset><input type="radio" aria-label="A"></fieldset>': 'fieldset without a legend',
            '<nav><a href="/">Again</a></nav>': 'navigation landmarks need distinct names',
        }
        for body, expected in cases.items():
            with self.subTest(body=body):
                found = self.problems(body)
                self.assertTrue(any(expected in p for p in found), found)

    def test_the_page_language(self):
        page = self.PAGE.format(lang='en', dir='ltr', body='<p>x</p>')
        self.assertIn('html: lang/dir should be ar/rtl', a11y.check(page, 'ar'))

    def test_markdown_tables_take_a_caption(self):
        html = str(Renderer().render(['| What | Licence |', '| --- | --- |', '| Code | MIT |',
                                      'Table: Licences for the *code*']))
        self.assertIn('<caption class="sr-only">Licences for the <em>code</em></caption>', html)
        self.assertIn('aria-label="Licences for the code"', html)
        self.assertNotIn('Table:', html)
        self.assertIn('aria-label="What"', str(Renderer().render(['| What | Licence |', '| --- | --- |', '| Code | MIT |'])))


class Styles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tokens()
        cls.css = {p.name: re.sub(r'/\*.*?\*/', '', p.read_text('utf-8'), flags=re.S) for p in sorted(CSS_DIR.glob('*.css'))}

    def test_text_on_tinted_surfaces(self):
        t = self.t
        pairs = [('--mint', '--mint-bg'),         # rising chips, beginner labels, health badges
                 ('--mint-hi', '--mint-bg'),      # Algeria's rank
                 ('--coral', '--coral-bg'),       # falling chips, failed checks
                 ('--amber', '--amber-bg'),       # health warnings
                 ('--ink', '--amber-bg'),         # a peer brought forward
                 ('--ink', '--seg-on'),           # the chosen option
                 ('--ink2', '--chip-bg'),         # labels
                 ('--ink3', '--sunk'),            # the search box's hint
                 ('--ink', '--tip-bg'), ('--ink3', '--tip-bg')]
        for text, tint in pairs:
            for surface in ('--bg', '--s1', '--s2'):
                with self.subTest(text=text, on=tint, surface=surface):
                    self.assertGreaterEqual(contrast(t[text], over(t[tint], t[surface])), 4.5)

    def test_focus_is_never_hidden(self):
        # The only element without an outline is <main>, which takes focus from the skip link.
        for name, css in self.css.items():
            for rule in re.finditer(r'([^{}]+)\{[^}]*outline:\s*(?:none|0)\b', css):
                with self.subTest(file=name):
                    self.assertEqual(rule.group(1).strip(), 'main:focus')
        base = self.css['10-base.css']
        self.assertRegex(base, r':focus-visible \{ outline: 2px solid var\(--mint\)')
        for surface in ('--bg', '--s1', '--s2'):
            self.assertGreaterEqual(contrast(self.t['--mint'], self.t[surface]), 3, 'focus ring against ' + surface)

    def test_radios_drawn_as_buttons_show_focus(self):
        # Inputs that are visually hidden inside a styled label hand their focus ring to it
        # (radio buttons, and the checkbox that pauses Home's hero).
        css = ''.join(self.css.values())
        for label in ('.mt', '.pk', '.seg label', '.hf-opt', '.hero-pause'):
            self.assertRegex(css, re.escape(label) + r':has\(> input:focus-visible\)[^{]*\{[^}]*outline: 2px solid var\(--mint\)')

    def test_motion_stops_for_people_who_ask(self):
        motion = self.css['90-motion.css']
        self.assertRegex(motion, r'@media \(prefers-reduced-motion: reduce\) \{\s*\*, \*::before, \*::after \{\s*animation: none !important;')
        # Scripted motion asks too: the chart fallback and the Hub's scroll to the feed.
        for script in ('site.js', 'hub.js'):
            js = (JS_DIR / script).read_text('utf-8')
            with self.subTest(script=script):
                self.assertIn("prefers-reduced-motion: reduce", js)
        for name, css in self.css.items():
            with self.subTest(file=name):
                self.assertNotRegex(css, r'scroll-behavior:\s*smooth')


if __name__ == '__main__':
    unittest.main()
