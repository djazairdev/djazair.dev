"""The launch smoke check (ticket #35): site/tools/smoke.py against the built site, served
locally, with and without the headers Cloudflare adds from _headers, and against a copy of
the site with things broken on purpose."""
import re
import shutil
import sys
import tempfile
import threading
import unittest
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(ROOT / 'site' / 'tools'))

import perf  # noqa: E402
import smoke  # noqa: E402
from djsite.build import build  # noqa: E402


def header_rules(dist: Path) -> list:
    """(path pattern, {name: value}) from the site's _headers file, as Cloudflare reads it."""
    rules = []
    for line in (dist / '_headers').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        if not line[0].isspace():
            rules.append((line.strip(), {}))
        else:
            name, _, value = line.strip().partition(':')
            rules[-1][1][name.strip()] = value.strip()
    return rules


class Cloudflareish(perf.Handler):
    """The local server, answering as Cloudflare does: with the headers from _headers."""
    rules: list = []

    def version_string(self):
        return 'cloudflare'

    def end_headers(self):
        path = urlsplit(self.path).path
        for pattern, headers in self.rules:
            if path.startswith(pattern[:-1]) if pattern.endswith('*') else path == pattern:
                for name, value in headers.items():
                    self.send_header(name, value)
        super().end_headers()


def serve(root: Path, handler=perf.Handler):
    server = perf.Server(('127.0.0.1', 0), partial(handler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}'


class Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.locs = re.findall(r'<loc>([^<]+)</loc>', (cls.dist / 'sitemap.xml').read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def check(self, root: Path, handler=perf.Handler):
        server, base = serve(root, handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return smoke.Smoke(base).run(), base

    def test_the_built_site_passes(self):
        result, base = self.check(self.dist)
        self.assertTrue(result.ok, result.report())
        self.assertEqual(result.counts['sitemap'], len(self.locs))
        self.assertGreaterEqual(result.counts['page'], 2)      # report drafts, outside the sitemap
        self.assertGreaterEqual(result.counts['file'], 100)
        self.assertEqual(result.counts['zip'], 2)              # the CSV bundle and the press kit
        self.assertEqual(result.counts['image'], 2)
        self.assertIn('response headers were not checked', result.report())

    def test_headers_are_checked_when_cloudflare_answers(self):
        Cloudflareish.rules = header_rules(self.dist)
        result, _ = self.check(self.dist, Cloudflareish)
        self.assertTrue(result.cloudflare)
        self.assertTrue(result.ok, result.report())
        self.assertNotIn('not checked', result.report())

        Cloudflareish.rules = []          # Cloudflare without the _headers file
        result, _ = self.check(self.dist, Cloudflareish)
        report = result.report()
        self.assertFalse(result.ok)
        self.assertRegex(report, r'/assets/\S+ is not cached as immutable')
        self.assertRegex(report, r'/data/\S+ cannot be read by other sites')
        self.assertRegex(report, r'/charts/\S+ cannot be read by other sites')
        self.assertIn('/en/ lacks X-Content-Type-Options: nosniff', report)

    def test_problems_are_found(self):
        broken = self.tmp / 'broken'
        shutil.copytree(self.dist, broken)
        self.addCleanup(shutil.rmtree, broken)
        chart = next((broken / 'charts').rglob('*.svg'))
        chart.unlink()
        page = broken / 'ar' / 'hub' / 'index.html'
        page.write_text(page.read_text('utf-8').replace('<html lang="ar"', '<html lang="en"', 1), 'utf-8')
        page = broken / 'en' / 'about' / 'index.html'
        page.write_text(page.read_text('utf-8').replace('<head>', '<head><meta name="robots" content="noindex">', 1), 'utf-8')
        (broken / '404.html').unlink()
        next((broken / 'reports').rglob('*.zip')).write_bytes(b'not a zip')
        (broken / 'robots.txt').write_text('User-agent: *\nAllow: /\n')
        root = broken / 'index.html'
        root.write_text(root.read_text('utf-8').replace('location.replace', 'location.assign'), 'utf-8')

        result, _ = self.check(broken)
        report = result.report()
        self.assertFalse(result.ok)
        self.assertIn(f'{chart.relative_to(broken).as_posix()} answered 404, not 200', report)
        self.assertIn("/ar/hub/ says it is in 'en', not 'ar'", report)
        self.assertIn('/en/about/ is in the sitemap but asks search engines not to index it', report)
        self.assertIn("a missing page doesn't show the site's own 404 page", report)
        self.assertRegex(report, r'/reports/\S+\.zip is not a zip file')
        self.assertIn('/robots.txt does not name the sitemap', report)
        self.assertIn('/ does not send readers to their language', report)
        self.assertTrue(report.endswith('8 problems.'), report)

    def test_no_answer(self):
        result = smoke.Smoke('http://127.0.0.1:9').run()
        self.assertFalse(result.ok)
        self.assertRegex(result.report(), r'/sitemap.xml did not answer \(.+\), not 200')

    def test_links_to_the_site_itself(self):
        s = smoke.Smoke('https://site.pages.dev/')
        page = 'https://site.pages.dev/en/data/'
        self.assertEqual(s.local('https://djazair.dev/en/#top', page), 'https://site.pages.dev/en/')
        self.assertEqual(s.local('/data/2026-q1/peers.csv', page), 'https://site.pages.dev/data/2026-q1/peers.csv')
        self.assertEqual(s.local('../methodology/#peer-groups', page), 'https://site.pages.dev/en/methodology/')
        self.assertIsNone(s.local('https://github.com/djazairdev', page))
        self.assertIsNone(s.local('mailto:hello@djazair.dev', page))


if __name__ == '__main__':
    unittest.main()
