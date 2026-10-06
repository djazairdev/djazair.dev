"""Detecting, downloading and archiving releases (ticket #9). No network: a fake GitHub serves a fixture."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igfixture import FakeGitHub, release_files  # noqa: E402
from pipeline import release  # noqa: E402
from pipeline.config import FILES, RAW_DIR  # noqa: E402


class Archiving(unittest.TestCase):
    def setUp(self):
        self.raw = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.raw)
        self.files = release_files()
        self.github = FakeGitHub(self.files)

    def run_archive(self, github=None):
        github = github or self.github
        return release.archive(release.latest(github), self.raw, github)

    def test_archives_a_new_release_with_checksums_and_metadata(self):
        folder, new = self.run_archive()
        self.assertTrue(new)
        self.assertEqual(folder, self.raw / self.github.commit)
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         sorted([f'{n}.csv' for n in FILES] + ['SHA256SUMS', 'release.json']))
        meta = json.loads((folder / 'release.json').read_text())
        self.assertEqual(meta['commit'], self.github.commit)
        self.assertEqual(meta['date'], '2021-09-01T12:00:00Z')
        self.assertEqual(meta['message'], 'release q2 2021 data')
        self.assertEqual(meta['quarter'], '2021-Q2')
        self.assertEqual(meta['files']['topics']['bytes'], len(self.files['topics']))
        sums = (folder / 'SHA256SUMS').read_text().splitlines()
        self.assertEqual(len(sums), 8)
        self.assertIn(f'{release.sha256(self.files["developers"])}  developers.csv', sums)

    def test_running_twice_on_the_same_release_changes_nothing(self):
        folder, _ = self.run_archive()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
        calls = len(self.github.calls)
        again, new = self.run_archive()
        self.assertFalse(new)
        self.assertEqual(again, folder)
        self.assertEqual({p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}, before)
        self.assertEqual(len(self.github.calls), calls + 1, 'only the release check, no downloads')

    def test_a_download_that_does_not_match_github_is_refused(self):
        github = FakeGitHub(self.files, serve={'topics': self.files['topics'] + b'1,extra,DZ,2021,2\n'})
        with self.assertRaises(release.ArchiveError):
            self.run_archive(github)
        self.assertEqual(list(self.raw.iterdir()), [], 'nothing half-written is left behind')

    def test_a_release_missing_a_file_is_refused(self):
        files = dict(self.files)
        del files['licenses']
        with self.assertRaisesRegex(release.ArchiveError, 'licenses.csv'):
            self.run_archive(FakeGitHub(files))

    def test_checksums_verify_on_read(self):
        folder, _ = self.run_archive()
        archive = release.Archive(folder)
        self.assertEqual(next(archive.rows('developers'))['iso2_code'], 'DZ')
        with open(folder / 'developers.csv', 'ab') as f:
            f.write(b'1,ZZ,2021,2\n')
        with self.assertRaises(release.ArchiveError):
            archive.read('developers')
        with self.assertRaises(release.ArchiveError):
            release.Archive(folder)

    def test_releases_are_listed_oldest_first(self):
        self.run_archive()
        newer = FakeGitHub(release_files((2021, 3)), commit='beef' + '0' * 36, date='2021-12-01T00:00:00Z')
        self.run_archive(newer)
        self.assertEqual([a.quarter for a in release.archives(self.raw)], ['2021-Q2', '2021-Q3'])


class ArchivedData(unittest.TestCase):
    def test_the_q1_2026_release_is_archived_and_intact(self):
        archive = release.Archive(RAW_DIR / '054c7dbc527518fa2ecfd316efe2aa01f3986c39')
        self.assertEqual(archive.quarter, '2026-Q1')
        self.assertEqual(archive.meta['date'][:10], '2026-07-07')


if __name__ == '__main__':
    unittest.main()
