"""Validating releases and failing safely (ticket #10)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igfixture import FakeGitHub, release_files  # noqa: E402
from pipeline import release  # noqa: E402
from pipeline.config import RAW_DIR  # noqa: E402
from pipeline.run import ValidationFailed, process  # noqa: E402
from pipeline.validate import validate  # noqa: E402


def edit(data: bytes, fn) -> bytes:
    lines = data.decode().splitlines()
    return ('\n'.join(fn(lines)) + '\n').encode()


class Validation(unittest.TestCase):
    def setUp(self):
        self.raw = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.raw)
        self.n = 0

    def archive(self, **changes) -> release.Archive:
        """Archive the fixture release with some files edited (``name=fn(lines) -> lines``)."""
        files = release_files()
        for name, fn in changes.items():
            files[name] = edit(files[name], fn)
        self.n += 1
        github = FakeGitHub(files, commit=f'{self.n:040x}')
        folder, _ = release.archive(release.latest(github), self.raw, github)
        return release.Archive(folder)

    def test_a_good_release_passes(self):
        report = validate(self.archive())
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(report.warnings, [])
        self.assertEqual(report.rows['developers'], 6 * 14)

    def test_a_renamed_column_fails_with_a_clear_report(self):
        archive = self.archive(developers=lambda ls: ['developer_count,iso2_code,year,quarter'] + ls[1:])
        report = validate(archive)
        self.assertFalse(report.ok)
        self.assertEqual(len(report.errors), 1)
        self.assertIn('`developers.csv`: the columns changed (missing developers; unexpected developer_count)', report.errors[0])
        body = report.markdown()
        self.assertIn('**failed**', body)
        self.assertIn('Nothing was computed or published', body)
        self.assertIn(archive.commit, body)

    def test_nothing_runs_after_a_failure(self):
        archive = self.archive(topics=lambda ls: ['pushers,topic,iso2_code,year,quarter'] + ls[1:])
        ran = []
        report_file = self.raw / 'report.md'
        with self.assertRaises(ValidationFailed) as caught:
            process(archive, steps=[lambda a: ran.append('compute'), lambda a: ran.append('publish')], report_path=report_file)
        self.assertEqual(ran, [])
        self.assertIn('topics.csv', report_file.read_text())
        self.assertFalse(caught.exception.report.ok)

    def test_the_steps_run_after_a_pass(self):
        ran = []
        process(self.archive(), steps=[lambda a: ran.append(a.quarter)])
        self.assertEqual(ran, ['2021-Q2'])

    def test_a_missing_quarter_fails(self):
        report = validate(self.archive(repositories=lambda ls: [line for line in ls if not line.endswith(',2020,3')]))
        self.assertIn('`repositories.csv`: no rows at all for 2020-Q3.', report.errors)

    def test_algeria_must_have_every_quarter_but_a_peer_may_miss_one(self):
        report = validate(self.archive(git_pushes=lambda ls: [line for line in ls if not line.endswith(',DZ,2021,1')]))
        self.assertIn('`git_pushes.csv`: DZ has no value for 2021-Q1.', report.errors)
        report = validate(self.archive(git_pushes=lambda ls: [line for line in ls if not line.endswith(',MA,2021,1')]))
        self.assertTrue(report.ok)
        self.assertTrue(any(w.startswith('`git_pushes.csv`: MA has no value for 2021-Q1.') for w in report.warnings))

    def test_every_reported_economy_needs_its_account_counts(self):
        report = validate(self.archive(developers=lambda ls: [line for line in ls if ',LY,' not in line]))
        self.assertTrue(any(e.startswith('`developers.csv`: LY has no value for 2020-Q1') for e in report.errors), report.errors)

    def test_bad_values_and_duplicates_fail_with_line_numbers(self):
        report = validate(self.archive(developers=lambda ls: ls + ['12.5,DZ,2019,1', '7,Algeria,2020,1', '7,ZZ,2020,5', ls[1]]))
        self.assertEqual(len(report.errors), 1)
        message = report.errors[0]
        self.assertIn('4 bad rows', message)
        self.assertIn("developers '12.5' is not a whole number", message)
        self.assertIn("year '2019' is not a year from 2020", message)
        self.assertIn("iso2_code 'Algeria' is not a two-letter economy code", message)
        self.assertIn("quarter '5' is not 1 to 4", message)
        self.assertIn(f'line {6 * 14 + 5} repeats DZ, 2020, 1', message)

    def test_rows_after_the_release_quarter_fail(self):
        report = validate(self.archive(topics=lambda ls: ls + ['150,rust,DZ,2021,3']))
        self.assertIn('`topics.csv`: rows for 2021-Q3, outside 2020-Q1 to 2021-Q2.', report.errors)

    def test_a_fall_in_accounts_is_flagged(self):
        report = validate(self.archive(developers=lambda ls: ['50000,DZ,2021,2' if line.endswith(',DZ,2021,2') else line
                                                              for line in ls]))
        self.assertTrue(report.ok)
        self.assertTrue(any(w.startswith('DZ: developer accounts fell') for w in report.warnings), report.warnings)


class RealRelease(unittest.TestCase):
    def test_the_q1_2026_release_passes(self):
        report = validate(release.Archive(RAW_DIR / '054c7dbc527518fa2ecfd316efe2aa01f3986c39'))
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(report.rows['developers'], 5656)
        self.assertEqual(len(report.warnings), 1)
        self.assertIn('MR has no value for 2020-Q1', report.warnings[0])


if __name__ == '__main__':
    unittest.main()
