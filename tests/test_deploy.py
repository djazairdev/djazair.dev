"""Deploys (ticket #6, docs/deploy.md): the site is a Cloudflare Worker made only of static
assets (wrangler.jsonc), deployed by CI once the tests and the build pass. The holding page
keeps djazair.dev until launch (wrangler.holding.jsonc)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite.build import MARKER, build  # noqa: E402

CI = (ROOT / '.github' / 'workflows' / 'ci.yml').read_text('utf-8')


def jsonc(path: Path) -> dict:
    """A Wrangler configuration file: JSON with // comments, dropped wherever they are outside
    a string."""
    text, out, i = path.read_text('utf-8'), [], 0
    in_string = escaped = False
    while i < len(text):
        c = text[i]
        if in_string:
            escaped, in_string = (not escaped and c == '\\'), (escaped or c != '"')
        elif c == '"':
            in_string = True
        elif text.startswith('//', i):
            i = text.find('\n', i)
            if i < 0:
                break
            continue
        out.append(c)
        i += 1
    return json.loads(''.join(out))


class Configuration(unittest.TestCase):
    def test_the_site_is_static_assets_only(self):
        config = jsonc(ROOT / 'wrangler.jsonc')
        assets = config['assets']
        self.assertEqual(assets['directory'], './site/dist', 'where site/build.py writes the site')
        self.assertEqual(assets['not_found_handling'], '404-page', 'the nearest 404.html, with status 404')
        self.assertEqual(assets['html_handling'], 'auto-trailing-slash', '/en/hub/ is the address of /en/hub/index.html')
        self.assertNotIn('main', config, 'no Worker code')
        self.assertNotIn('routes', config, 'djazair.dev stays on the holding page until launch (docs/launch.md)')

    def test_the_holding_page_has_the_domain_until_launch(self):
        config = jsonc(ROOT / 'wrangler.holding.jsonc')
        self.assertTrue((ROOT / config['assets']['directory'] / 'index.html').is_file())
        self.assertEqual(config['routes'], [{'pattern': 'djazair.dev', 'custom_domain': True}])
        self.assertNotEqual(config['name'], jsonc(ROOT / 'wrangler.jsonc')['name'], 'two Workers')

    def test_comments_are_dropped_but_not_inside_strings(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / 'w.jsonc').write_text('// top\n{"a": "https://x.dev/", // after\n "b": "say \\"//\\""}\n')
        self.assertEqual(jsonc(tmp / 'w.jsonc'), {'a': 'https://x.dev/', 'b': 'say "//"'})

    def test_the_build_keeps_its_marker_off_the_site(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        build(tmp / 'dist', quiet=True)
        self.assertEqual((tmp / 'dist' / '.assetsignore').read_text().split(), [MARKER])


class Workflow(unittest.TestCase):
    JOB = CI[CI.index('\n  deploy:\n'):]

    def test_main_deploys_and_pull_requests_upload_a_preview(self):
        self.assertIn("github.event_name != 'pull_request' && 'deploy'", self.JOB)
        self.assertIn("versions upload --preview-alias=pr-{0}", self.JOB, 'a preview never replaces the live site')
        self.assertIn('path: site/dist', self.JOB, 'the build goes where wrangler.jsonc looks for it')
        self.assertLess(self.JOB.index('actions/checkout@'), self.JOB.index('wrangler-action@'), 'wrangler.jsonc comes from the checkout')

    def test_deploys_wait_for_the_tests_and_the_build(self):
        self.assertIn('needs: deploy-settings', self.JOB)
        settings = CI[CI.index('\n  deploy-settings:\n'):CI.index('\n  deploy:\n')]
        self.assertIn('needs: build', settings)
        self.assertIn('CLOUDFLARE_API_TOKEN', settings)
        self.assertIn('CLOUDFLARE_ACCOUNT_ID', settings)

    def test_nothing_is_left_from_pages(self):
        self.assertNotIn('pages deploy', CI)
        self.assertNotIn('CLOUDFLARE_PAGES_PROJECT', CI, 'the Worker is named in wrangler.jsonc')


if __name__ == '__main__':
    unittest.main()
