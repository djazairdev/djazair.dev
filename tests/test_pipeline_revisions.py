"""Revisions between releases (ticket #12): a changed past value is reported, never silent."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igfixture import FakeGitHub, accounts, release_files  # noqa: E402
from pipeline import release  # noqa: E402
from pipeline.revisions import compare  # noqa: E402


class Revisions(unittest.TestCase):
    def setUp(self):
        self.raw = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.raw)
        self.old = self.archive(release_files((2021, 2)), 'a', '2021-09-01T00:00:00Z')

    def archive(self, files, commit, date):
        github = FakeGitHub(files, commit=commit * 40, date=date)
        folder, _ = release.archive(release.latest(github), self.raw, github)
        return release.Archive(folder)

    def test_an_unrevised_release_reports_nothing(self):
        new = self.archive(release_files((2021, 3)), 'b', '2021-12-01T00:00:00Z')
        report = compare(self.old, new)
        self.assertFalse(report.found)
        self.assertIn('no past value changed', report.markdown())

    def test_a_changed_past_value_is_reported(self):
        files = release_files((2021, 3))
        before = accounts('DZ', 3)
        old_line = f'{before},DZ,2020,4'.encode()
        self.assertIn(old_line, files['developers'])
        files['developers'] = files['developers'].replace(old_line, f'{before + 500},DZ,2020,4'.encode())
        files['organizations'] = b'\n'.join(line for line in files['organizations'].split(b'\n')
                                             if not line.endswith(b',SN,2021,1'))
        new = self.archive(files, 'c', '2021-12-01T00:00:00Z')
        report = compare(self.old, new)
        self.assertTrue(report.found)
        self.assertEqual([(r.series, r.code, r.quarter, r.old, r.new) for r in report.revisions],
                         [('developers', 'DZ', '2020-Q4', before, before + 500),
                          ('organizations', 'SN', '2021-Q1', round(accounts('SN', 4) * 0.04), None)])
        body = report.markdown()
        self.assertIn('**2 past values changed**, 1 of them for economies the Index reports on', body)
        self.assertIn(f'| developers | DZ | 2020-Q4 | {before:,} | {before + 500:,} |', body)
        self.assertIn('| removed |', body)
        self.assertLess(body.index('| DZ |'), body.index('| SN |'), 'Algeria and its peers come first')

    def test_new_quarters_are_not_revisions(self):
        new = self.archive(release_files((2022, 1)), 'd', '2022-03-01T00:00:00Z')
        self.assertEqual(compare(self.old, new).revisions, [])


if __name__ == '__main__':
    unittest.main()
