"""Derived data (ticket #13): every table as CSV and JSON with the licence, stable for diffs,
nothing written when validation fails, and the committed data matches the code."""
import csv
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igfixture import FakeGitHub, accounts, release_files  # noqa: E402
from pipeline import publish, release  # noqa: E402
from pipeline.config import ATTRIBUTION, DERIVED_DIR, RAW_DIR  # noqa: E402
from pipeline.indicators import INDICATORS  # noqa: E402
from pipeline.population import Population  # noqa: E402
from pipeline.run import ValidationFailed, process  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TABLES = ('overview', 'peers', 'groups', 'ranks', 'trends', 'languages', 'languages_algeria', 'topics', 'collaboration',
          'indicators', 'revisions')
T1 = datetime(2021, 9, 2, 8, 0, tzinfo=timezone.utc)
T2 = datetime(2021, 9, 3, 8, 0, tzinfo=timezone.utc)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = self.tmp / 'derived'
        pop = self.tmp / 'population.json'
        pop.write_text(json.dumps({'series': {'SP.POP.TOTL': {'updated': '2026-07-13', 'values': {
            'DZ': {'2024': 46_000_000, '2025': 47_000_000}, 'MA': {'2024': 38_000_000}}}}}))
        self.population = Population(pop)

    def archive(self, files=None, commit='a', date='2021-09-01T00:00:00Z'):
        github = FakeGitHub(files or release_files(), commit=commit * 40, date=date)
        folder, _ = release.archive(release.latest(github), self.tmp / 'raw', github)
        return release.Archive(folder)

    def publish(self, archive, **kw):
        kw.setdefault('now', T1)
        return publish.publish(archive, self.out, self.population, **kw)


class Files(Fixture):
    def test_every_table_as_csv_and_json_with_a_manifest(self):
        folder = self.publish(self.archive())
        self.assertEqual(folder, self.out / '2021-q2')
        names = {p.name for p in folder.iterdir()}
        self.assertEqual(names, {f'{t}.{ext}' for t in TABLES for ext in ('csv', 'json')} | {'README.md', 'manifest.json'})
        manifest = json.loads((folder / 'manifest.json').read_text())
        self.assertEqual(set(manifest['files']), names - {'manifest.json'})
        for name, entry in manifest['files'].items():
            data = (folder / name).read_bytes()
            self.assertEqual((entry['bytes'], entry['sha256']), (len(data), hashlib.sha256(data).hexdigest()), name)
        self.assertEqual((manifest['quarter'], manifest['release'], manifest['generated_at']), ('2021-Q2', 'a' * 40, '2021-09-02T08:00:00Z'))
        self.assertEqual(manifest['quarters'][0], '2020-Q1')
        self.assertEqual(manifest['population']['algeria_year'], 2025)
        latest = json.loads((self.out / 'latest.json').read_text())
        self.assertEqual((latest['quarter'], latest['folder'], latest['licence']), ('2021-Q2', '2021-q2', 'CC0-1.0'))

    def test_every_file_and_folder_states_the_licence_and_attribution(self):
        folder = self.publish(self.archive())
        for path in folder.glob('*.json'):
            body = json.loads(path.read_text())
            self.assertEqual((body['licence'], body['attribution']), ('CC0-1.0', ATTRIBUTION), path.name)
            self.assertIn('creativecommons.org/publicdomain/zero', body['licence_url'])
        readme = (folder / 'README.md').read_text()
        self.assertIn('CC0', readme)
        self.assertIn(ATTRIBUTION, readme)
        for table in TABLES:
            self.assertIn(f'`{table}.csv`', readme)

    def test_json_rows_match_the_csv_and_the_columns(self):
        folder = self.publish(self.archive())
        for table in TABLES:
            body = json.loads((folder / f'{table}.json').read_text())
            names = [c['name'] for c in body['columns']]
            rows = list(csv.reader(io.StringIO((folder / f'{table}.csv').read_text())))
            self.assertEqual(rows[0], names, table)
            self.assertEqual(len(rows) - 1, len(body['rows']), table)
            for line, row in zip(rows[1:], body['rows']):
                self.assertEqual(list(row), names, f'{table}: rows keep the column order')
                as_text = ['' if v is None else 'true' if v is True else 'false' if v is False
                           else publish.number_text(v) if isinstance(v, float) else str(v) for v in row.values()]
                self.assertEqual(line, as_text, table)
            for col in body['columns']:
                self.assertIn(col['type'], ('string', 'integer', 'number', 'boolean'))
                self.assertTrue(col['description'], f'{table}.{col["name"]} has a description')

    def test_values(self):
        folder = self.publish(self.archive())
        overview = {r['indicator']: r for r in json.loads((folder / 'overview.json').read_text())['rows']}
        self.assertEqual([r for r in overview], list(INDICATORS))
        self.assertEqual(overview['accounts']['value'], accounts('DZ', 5))
        self.assertEqual(overview['accounts']['year_earlier'], accounts('DZ', 1))
        self.assertEqual(overview['accounts']['change'], round(accounts('DZ', 5) / accounts('DZ', 1) - 1, 6))
        self.assertIsNone(overview['yoy']['change'], 'a growth rate has no growth of its own')
        self.assertEqual(overview['accounts']['north_africa_ranked'], 7)
        self.assertEqual(overview['accounts_per_million']['value'], round(accounts('DZ', 5) / 47, 6))
        peers = {r['economy']: r for r in json.loads((folder / 'peers.json').read_text())['rows']}
        self.assertEqual(list(peers), ['DZ', 'EG', 'LY', 'MA', 'MR', 'SD', 'TN', 'NG', 'KE', 'ZA'])
        self.assertEqual((peers['DZ']['north_africa'], peers['DZ']['core_peer'], peers['MA']['core_peer']), (True, False, True))
        self.assertIsNone(peers['EG']['accounts_per_million'], 'missing, not zero')
        self.assertEqual(peers['MA']['population_year'], 2024)
        trends = json.loads((folder / 'trends.json').read_text())['rows']
        dz = [r['value'] for r in trends if r['indicator'] == 'accounts' and r['series'] == 'DZ']
        self.assertEqual(dz, [accounts('DZ', i) for i in range(6)])

    def test_collaboration_both_ways_with_the_eu_unranked(self):
        folder = self.publish(self.archive())
        rows = [r for r in json.loads((folder / 'collaboration.json').read_text())['rows'] if r['quarter'] == '2021-Q2']
        self.assertEqual([(r['direction'], r['rank'], r['partner'], r['weight']) for r in rows],
                         [('sent', 1, 'US', 90), ('sent', None, 'EU', 80), ('sent', 2, 'FR', 40),
                          ('received', 1, 'FR', 50), ('received', 2, 'MA', 30)])

    def test_numbers_have_fixed_decimals(self):
        cases = {586990.0: '586990', 0.4914690001: '0.491469', 1.0630129999: '1.063013', -0.0: '0', -1e-9: '0', 1e-05: '0.00001',
                 -0.0738724: '-0.073872', 2.5: '2.5', 12374.536506123: '12374.536506'}
        for value, text in cases.items():
            self.assertEqual(publish.number_text(value), text, value)
        folder = self.publish(self.archive())
        for path in folder.glob('*.csv'):
            self.assertNotRegex(path.read_text(), r'\d[eE][-+]?\d', f'{path.name}: no exponent notation')
            self.assertNotRegex(path.read_text(), r'\.\d{7}', f'{path.name}: at most six decimals')


class Stability(Fixture):
    def test_publishing_again_changes_nothing(self):
        archive = self.archive()
        folder = self.publish(archive, now=T1)
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        self.publish(archive, now=T2)
        self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, before, 'same data, same bytes and same generated_at')

    def test_generated_at_moves_when_the_data_does(self):
        self.publish(self.archive(), now=T1)
        files = release_files()
        files['developers'] = files['developers'].replace(f'{accounts("DZ", 5)},DZ,2021,2'.encode(), b'999999,DZ,2021,2')
        folder = self.publish(self.archive(files, commit='b', date='2021-09-05T00:00:00Z'), now=T2)
        manifest = json.loads((folder / 'manifest.json').read_text())
        self.assertEqual((manifest['generated_at'], manifest['release']), ('2021-09-03T08:00:00Z', 'b' * 40))

    def test_latest_never_moves_back(self):
        self.publish(self.archive(release_files((2021, 3)), commit='c', date='2021-12-01T00:00:00Z'))
        self.publish(self.archive(release_files((2021, 2)), commit='d', date='2021-09-01T00:00:00Z'))
        self.assertEqual(json.loads((self.out / 'latest.json').read_text())['quarter'], '2021-Q3')
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ['2021-q2', '2021-q3', 'latest.json'])

    def test_a_dropped_table_is_removed(self):
        folder = self.publish(self.archive())
        (folder / 'old_table.csv').write_text('x\n')
        self.publish(self.archive())
        self.assertFalse((folder / 'old_table.csv').exists())


class Gate(Fixture):
    def test_nothing_is_written_when_validation_fails(self):
        files = release_files()
        files['git_pushes'] = files['git_pushes'].replace(b'git_pushes,iso2_code', b'pushes,iso2_code')
        archive = self.archive(files)
        with self.assertRaises(ValidationFailed):
            process(archive, steps=[lambda a: self.publish(a)])
        self.assertFalse(self.out.exists())

    def test_revisions_are_published(self):
        old = self.archive()
        files = release_files((2021, 3))
        before = accounts('DZ', 3)
        files['developers'] = files['developers'].replace(f'{before},DZ,2020,4'.encode(), f'{before + 500},DZ,2020,4'.encode())
        new = self.archive(files, commit='e', date='2021-12-01T00:00:00Z')
        folder = self.publish(new, previous=old)
        rows = json.loads((folder / 'revisions.json').read_text())['rows']
        self.assertEqual(rows, [{'series': 'developers', 'economy': 'DZ', 'quarter': '2020-Q4', 'before': before, 'now': before + 500}])
        manifest = json.loads((folder / 'manifest.json').read_text())
        self.assertEqual(manifest['revisions'], {'compared_with': 'a' * 40, 'compared_quarter': '2021-Q2', 'changed': 1})


class Committed(unittest.TestCase):
    """The data in data/derived/ is what the code makes from the archived release."""

    def test_latest_is_the_newest_archived_release(self):
        latest = json.loads((DERIVED_DIR / 'latest.json').read_text())
        newest = release.archives(RAW_DIR)[-1]
        self.assertEqual((latest['release'], latest['quarter']), (newest.commit, newest.quarter))

    def test_committed_files_match_the_code(self):
        latest = json.loads((DERIVED_DIR / 'latest.json').read_text())
        archive = next(a for a in release.archives(RAW_DIR) if a.commit == latest['release'])
        folder = DERIVED_DIR / latest['folder']
        manifest = json.loads((folder / 'manifest.json').read_text())
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        made = publish.publish(archive, tmp, previous=None if manifest['revisions']['compared_with'] is None else next(
            a for a in release.archives(RAW_DIR) if a.commit == manifest['revisions']['compared_with']))
        for path in sorted(made.iterdir()):
            if path.name == 'manifest.json':
                continue
            self.assertEqual(path.read_bytes(), (folder / path.name).read_bytes(),
                             f'data/derived/{folder.name}/{path.name} is stale: run `python3 -m pipeline publish`')
        fresh = json.loads((made / 'manifest.json').read_text())
        self.assertEqual({k: v for k, v in fresh.items() if k != 'generated_at'},
                         {k: v for k, v in manifest.items() if k != 'generated_at'})

    def test_appendix_a_in_the_published_files(self):
        folder = DERIVED_DIR / json.loads((DERIVED_DIR / 'latest.json').read_text())['folder']
        overview = {r['indicator']: r for r in json.loads((folder / 'overview.json').read_text())['rows']}
        self.assertEqual((overview['accounts']['value'], overview['accounts']['year_earlier']), (586_990, 393_565))
        self.assertEqual(round(overview['yoy']['value'] * 100, 1), 49.1)
        self.assertEqual((overview['yoy']['north_africa_rank'], overview['yoy']['north_africa_ranked']), (3, 7))
        self.assertEqual((overview['yoy']['africa_rank'], overview['yoy']['africa_ranked']), (19, 29))
        self.assertEqual(round(overview['orgs_per_account']['value'], 4), 0.0315)

    def test_the_eu_is_the_sum_of_its_members_listed(self):
        """Why the collaboration table leaves the EU unranked, in the published data."""
        from pipeline.config import EU_MEMBERS
        folder = DERIVED_DIR / json.loads((DERIVED_DIR / 'latest.json').read_text())['folder']
        rows = json.loads((folder / 'collaboration.json').read_text())['rows']
        groups = {}
        for r in rows:
            groups.setdefault((r['quarter'], r['direction']), []).append(r)
        checked = 0
        for key, found in groups.items():
            eu = [r['weight'] for r in found if r['partner'] == 'EU']
            if eu:
                self.assertEqual(eu[0], sum(r['weight'] for r in found if r['partner'] in EU_MEMBERS), key)
                checked += 1
            self.assertEqual(sorted(r['rank'] for r in found if r['partner'] != 'EU'),
                             sorted(r['rank'] for r in found if r['rank'] is not None), key)
        self.assertGreater(checked, 40)

    def test_the_schema_is_documented(self):
        readme = (REPO / 'data' / 'README.md').read_text()
        folder = DERIVED_DIR / json.loads((DERIVED_DIR / 'latest.json').read_text())['folder']
        for table in TABLES:
            self.assertIn(f'### `{table}`', readme)
            section = readme.split(f'### `{table}`', 1)[1].split('\n### ', 1)[0]
            for col in json.loads((folder / f'{table}.json').read_text())['columns']:
                self.assertIn(f'`{col["name"]}`', section, f'data/README.md: {table}.{col["name"]}')


if __name__ == '__main__':
    unittest.main()
