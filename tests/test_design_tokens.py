"""Design tokens, fonts and base styles (ticket #3)."""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite.build import build  # noqa: E402
from djsite.palette import CSS_SOURCE, DARK  # noqa: E402

CSS_DIR = ROOT / 'site' / 'static' / 'css'
TOKEN_FILES = {'00-tokens.css', '05-fonts.css'}


def tokens() -> dict:
    css = (CSS_DIR / '00-tokens.css').read_text('utf-8')
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'(--[\w-]+):\s*([^;]+);', css)}


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip('#')
    def channel(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(h[i:i + 2]) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def norm(value: str) -> str:
    return value.replace(' ', '').lower()


class Tokens(unittest.TestCase):
    def test_text_tokens_meet_wcag_aa_on_every_surface(self):
        t = tokens()
        for text in ('--ink', '--ink2', '--ink3', '--mint', '--coral', '--amber'):
            for surface in ('--bg', '--s1', '--s2', '--s1-hover'):
                with self.subTest(text=text, surface=surface):
                    self.assertGreaterEqual(contrast(t[text], t[surface]), 4.5)
        self.assertGreaterEqual(contrast(t['--on-mint'], t['--mint']), 4.5)
        self.assertGreaterEqual(contrast(t['--on-mint'], t['--mint-hover']), 4.5)

    def test_chart_lines_meet_the_3_to_1_graphics_minimum(self):
        t = tokens()
        for colour in ('--grey', '--grey-hi', '--mint', '--amber', '--coral'):
            self.assertGreaterEqual(contrast(t[colour], t['--bg']), 3)

    def test_components_use_tokens_not_raw_colours(self):
        for path in sorted(CSS_DIR.glob('*.css')):
            if path.name in TOKEN_FILES:
                continue
            css = re.sub(r'/\*.*?\*/', '', path.read_text('utf-8'), flags=re.S)
            with self.subTest(file=path.name):
                self.assertEqual(re.findall(r'#[0-9a-fA-F]{3,8}\b', css), [])
                self.assertEqual(re.findall(r'\brgba?\(', css), [])

    def test_download_palette_matches_the_css_tokens(self):
        t = tokens()
        for key, prop in CSS_SOURCE.items():
            with self.subTest(colour=key):
                self.assertEqual(norm(DARK[key]), norm(t[prop]))


class Fonts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist)
        cls.css = next((cls.dist / 'assets').glob('site.*.css')).read_text('utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_fonts_are_self_hosted(self):
        self.assertNotIn('googleapis', self.css)
        self.assertNotIn('gstatic', self.css)
        urls = re.findall(r'url\((/assets/fonts/[^)]+)\)', self.css)
        self.assertGreaterEqual(len(urls), 9)
        for url in urls:
            self.assertTrue((self.dist / url.lstrip('/')).exists(), url)
        self.assertTrue((self.dist / 'assets' / 'fonts' / 'OFL-Tajawal.txt').exists())

    def test_both_scripts_render_in_tajawal(self):
        tajawal = re.findall(r"font-family: 'Tajawal';[^}]*unicode-range: ([^;]+);", self.css)
        self.assertTrue(any('U+0600-06FF' in r for r in tajawal), 'no Arabic subset')
        self.assertTrue(any('U+0000-00FF' in r for r in tajawal), 'no Latin subset')
        self.assertIn('font-display: swap', self.css)

    def test_two_fonts_are_preloaded_per_page(self):
        for lang in ('en', 'ar'):
            html = (self.dist / lang / 'index.html').read_text('utf-8')
            preloads = re.findall(r'<link rel="preload" href="([^"]+)" as="font"', html)
            self.assertEqual(len(preloads), 2, lang)
            for href in preloads:
                self.assertTrue((self.dist / href.lstrip('/')).exists(), href)

    def test_reduced_motion_stops_everything(self):
        block = re.search(r'@media \(prefers-reduced-motion: reduce\) \{(.*?)\}\s*\}', self.css, re.S)
        self.assertIsNotNone(block)
        self.assertIn('animation: none !important', block.group(1))
        self.assertIn('transition: none !important', block.group(1))


if __name__ == '__main__':
    unittest.main()
