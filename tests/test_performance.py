"""Performance budgets that hold without a browser (ticket #30): what each page transfers,
compressed and fonts apart; nothing render-blocking but the page itself; small, subset fonts
that swap in; a light unit map; long caching for hashed files. Load times are measured in
Chrome by site/tools/perf.py (docs/performance.md)."""
import gzip
import re
import shutil
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(ROOT / 'site' / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import perf  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import PUBLISHED  # noqa: E402
from htmlcheck import stylesheet  # noqa: E402

BUDGET = 300 * 1024


def gz(data: bytes) -> int:
    return len(gzip.compress(data, 6))


class Budgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.pages = {p: p.read_text('utf-8') for p in sorted(cls.dist.rglob('*.html'))}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_every_page_transfers_under_300_kb_without_fonts(self):
        self.assertEqual(perf.BYTES_BUDGET, BUDGET)
        for path, html in self.pages.items():
            files = {self.dist / ref.lstrip('/') for ref in re.findall(r'(?:src|href)="(/(?:assets|favicon)[^"]*)"', html)
                     if '/fonts/' not in ref}
            total = gz(html.encode('utf-8')) + sum(gz(f.read_bytes()) for f in files)
            with self.subTest(page=str(path.relative_to(self.dist))):
                self.assertLessEqual(total, BUDGET)
                self.assertLessEqual(total, 100 * 1024, 'far over what pages weigh today: is something new too heavy?')

    def test_only_the_page_blocks_rendering(self):
        for path, html in self.pages.items():
            head = html.split('</head>', 1)[0]
            with self.subTest(page=str(path.relative_to(self.dist))):
                self.assertNotIn('rel="stylesheet"', head, 'the stylesheet is inlined: one round trip less')
                self.assertEqual(head.count('<style>'), 1)
                for tag in re.findall(r'<script\b[^>]*>', html):
                    if 'src=' in tag:
                        self.assertIn(' defer', tag)
                    else:   # inline: data for a script, or the root page's language redirect
                        self.assertTrue('type="application/json"' in tag or 'type="application/ld+json"' in tag or path == self.dist / 'index.html', tag)

    def test_fonts_are_subset_preloaded_and_swap(self):
        for font in sorted((self.dist / 'assets' / 'fonts').glob('*.woff2')):
            with self.subTest(font=font.name):
                self.assertLessEqual(font.stat().st_size, 32 * 1024)
        faces = re.findall(r'@font-face\s*\{[^}]*\}', stylesheet(self.dist))
        self.assertGreaterEqual(len(faces), 9)
        for face in faces:
            self.assertIn('font-display: swap', face)
            if 'Tajawal' in face:
                self.assertIn('unicode-range', face)
        for lang in ('en', 'ar'):
            preloads = re.findall(r'<link rel="preload" href="/assets/fonts/([^"]+)"', self.pages[self.dist / lang / 'index.html'])
            self.assertEqual(preloads, [f'tajawal-{"latin" if lang == "en" else "arabic"}-400.woff2', 'jetbrains-mono-latin.woff2'])

    def test_the_unit_map_stays_light(self):
        for lang in PUBLISHED:          # the other languages show the invitation to translate (#61)
            svg = re.search(r'<svg class="chart um[ "].*?</svg>', self.pages[self.dist / lang / 'index.html'], re.S).group(0)
            with self.subTest(lang=lang):
                self.assertLessEqual(len(svg.encode('utf-8')), 48 * 1024)
                self.assertLessEqual(gz(svg.encode('utf-8')), 6 * 1024)
                self.assertLessEqual(svg.count('<rect'), 800, 'one square per 1,000 accounts: rescale before it grows past 800')

    def test_hashed_files_are_cached_for_a_year(self):
        headers = (self.dist / '_headers').read_text('utf-8')
        self.assertIn('/assets/*\n  ! Cache-Control\n  Cache-Control: public, max-age=31536000, immutable', headers)
        for path in sorted((self.dist / 'assets').glob('*.js')):
            with self.subTest(file=path.name):
                self.assertRegex(path.name, r'^[\w-]+\.[0-9a-f]{10}\.js$')


class LocalServer(unittest.TestCase):
    """site/tools/perf.py serves the site as Cloudflare does: gzipped, with the 404 page."""

    def test_gzip_and_404(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / 'en').mkdir()
        (tmp / 'en' / 'index.html').write_text('<!doctype html><p>' + 'hello ' * 200, 'utf-8')
        (tmp / '404.html').write_text('<!doctype html><p>not here', 'utf-8')
        server = perf.serve(tmp)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_address[1]}'
        req = urllib.request.Request(base + '/en/', headers={'Accept-Encoding': 'gzip'})
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.headers['Content-Encoding'], 'gzip')
            self.assertEqual(r.headers['Cache-Control'], 'no-store')
            self.assertIn(b'hello hello', gzip.decompress(r.read()))
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(base + '/nowhere/')
        with caught.exception as missing:
            self.assertEqual(missing.code, 404)
            self.assertIn(b'not here', missing.read())


if __name__ == '__main__':
    unittest.main()
