"""The site builds from data/derived/ only (ticket #13)."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite import data  # noqa: E402
from djsite.build import build  # noqa: E402


class Loader(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def copy(self) -> Path:
        root = self.tmp / 'derived'
        shutil.copytree(data.DERIVED_DIR, root)
        return root

    def test_latest_quarter(self):
        d = data.load()
        latest = json.loads((data.DERIVED_DIR / 'latest.json').read_text())
        self.assertEqual((d.quarter, d.release), (latest['quarter'], latest['release']))
        self.assertEqual(d.quarters[0], '2020-Q1')
        self.assertEqual(d.quarters[-1], d.quarter)
        accounts = d.series('accounts', 'DZ')
        self.assertEqual(len(accounts), len(d.quarters))
        self.assertEqual(accounts[-1], d.overview()['accounts']['value'])
        self.assertEqual(len(d.series('yoy', 'median_africa')), len(d.quarters))
        with self.assertRaises(data.DataError):
            d.series('accounts', 'XX')

    def test_a_changed_file_is_refused(self):
        root = self.copy()
        folder = root / json.loads((root / 'latest.json').read_text())['folder']
        path = folder / 'overview.json'
        path.write_text(path.read_text().replace('586990', '586991'))
        with self.assertRaisesRegex(data.DataError, 'does not match manifest.json'):
            data.load(root).table('overview')

    def test_missing_data_says_how_to_make_it(self):
        with self.assertRaisesRegex(data.DataError, 'pipeline publish'):
            data.load(self.tmp / 'nothing')

    def test_files_outside_the_manifest_are_refused(self):
        with self.assertRaises(data.DataError):
            data.load().read('../latest.json')


class SourcesOfTruth(unittest.TestCase):
    def test_site_code_reads_no_other_data(self):
        for path in (ROOT / 'site' / 'djsite').rglob('*.py'):
            text = path.read_text('utf-8')
            with self.subTest(path=path.name):
                self.assertNotRegex(text, r'^\s*(from|import)\s+pipeline', 'the site never runs the pipeline')
                self.assertNotIn('population.json', text)
                self.assertNotRegex(text, r"['/]raw['/]", 'the site never reads the raw archive')
        self.assertFalse((ROOT / 'site' / 'dev').exists(), 'no data snapshot of its own')

    def test_built_numbers_come_from_the_derived_data(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        build(tmp / 'dist', dev=True, quiet=True)
        page = (tmp / 'dist' / 'en' / '_dev' / 'components' / 'index.html').read_text('utf-8')
        d = data.load()
        per_million = round(d.peers()['DZ']['accounts_per_million'])
        self.assertIn(f'{per_million:,}', re.sub(r'<[^>]+>', '', page))
        self.assertIn(f'{d.overview()["accounts"]["value"]:,}', page)


if __name__ == '__main__':
    unittest.main()
