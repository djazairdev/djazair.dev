"""Public discovery must never imply an opted-in Hub response pledge."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
from djsite import public_projects
from djsite.build import build


class PublicDiscovery(unittest.TestCase):
    def test_rejects_unsafe_or_unrelated_contribution_destinations(self):
        data = public_projects.load()
        for url in ('javascript:alert(1)', 'https://github.com.evil.test/a/b', 'https://github.com/other/project'):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as tmp:
                altered = copy.deepcopy(data)
                altered['projects'][0]['contribute'] = url
                path = Path(tmp) / 'projects.json'
                path.write_text(json.dumps(altered))
                with self.assertRaises(ValueError):
                    public_projects.load(path)

    def test_editorial_projects_are_separate_from_empty_hub(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'dist'
            build(out, quiet=True, hub_dir=Path(tmp) / 'no-hub')
            for lang in ('en', 'ar'):
                page = (out / lang / 'index.html').read_text()
                public = page.split('class="public-discovery"')[1].split('</section>')[0]
                for p in public_projects.load()['projects']:
                    self.assertIn(p['contribute'], public)
                self.assertNotIn('opportunity-pledge', public)
                self.assertNotIn('class="card opportunity"', public)
                self.assertNotIn('class="untranslated"', public)
                hub = (out / lang / 'hub' / 'index.html').read_text()
                self.assertNotIn('dzcode-io/dzcode.io', hub)
