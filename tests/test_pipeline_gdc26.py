"""GitHub's GDC26 rankings (ticket #38): archived like a release, and djazair.dev's estimate of
the same measure from the quarterly files."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import gdc26  # noqa: E402
from pipeline.config import API_URL, RAW_URL, SOURCE_REPO  # noqa: E402
from pipeline.release import ArchiveError, blob_sha  # noqa: E402

FILES = {
    'README.md': b'# GDC26\n',
    gdc26.WORLD: b'classified_iso2_code,economy_name,icann_region_name,pushes,rank_pushes\nUS,United States,North America,9,1\n',
    gdc26.PER_CAPITA: (b'classified_iso2_code,economy_name,icann_region_name,git_pushes,working_age_population,'
                       b'git_pushes_per_1k_working_age_population,rank_d5_by_icann_region\n'
                       b'TN,Tunisia,Africa,30,1000,30.0,2\nMU,Mauritius,Africa,40,1000,40.0,1\n'
                       b'CH,Switzerland,Europe,90,1000,90.0,1\n'),
}


class FakeGitHub:
    def __init__(self, files=FILES, listed=None):
        self.files, self.listed = dict(files), listed if listed is not None else {n: blob_sha(d) for n, d in files.items()}
        self.calls = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        if url == f'{API_URL}/repos/{SOURCE_REPO}/contents/{gdc26.FOLDER}?ref={gdc26.COMMIT}':
            return json.dumps([{'name': n, 'sha': sha} for n, sha in self.listed.items()]).encode()
        prefix = f'{RAW_URL}/{SOURCE_REPO}/{gdc26.COMMIT}/{gdc26.FOLDER}/'
        return self.files[url[len(prefix):]]


class Archive(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.dest = self.tmp / 'gdc26'

    def test_archived_once_with_checksums(self):
        github = FakeGitHub()
        folder, new = gdc26.archive(self.dest, github)
        self.assertTrue(new)
        meta = gdc26.verify(folder)
        self.assertEqual(meta['commit'], gdc26.COMMIT)
        self.assertEqual(set(meta['files']), set(gdc26.FILES))
        lists = gdc26.GDC26(folder)
        self.assertEqual([(e.rank, e.economy) for e in lists.africa], [(1, 'MU'), (2, 'TN')], 'Africa only, by rank')
        self.assertEqual([(e.rank, e.economy, e.region, e.pushes) for e in lists.world], [(1, 'US', 'North America', 9)])
        calls = len(github.calls)
        self.assertEqual(gdc26.archive(self.dest, github), (folder, False))
        self.assertEqual(len(github.calls), calls, 'nothing is downloaded again')

    def test_a_download_that_doesnt_match_githubs_hash_is_refused(self):
        github = FakeGitHub(listed={**{n: blob_sha(d) for n, d in FILES.items()}, gdc26.WORLD: '0' * 40})
        with self.assertRaisesRegex(ArchiveError, 'does not match the hash'):
            gdc26.archive(self.dest, github)
        self.assertFalse(self.dest.exists())
        self.assertEqual([p.name for p in self.tmp.iterdir()], [], 'no partial folder is left')

    def test_a_missing_file_is_refused(self):
        github = FakeGitHub(listed={n: blob_sha(d) for n, d in FILES.items() if n != 'README.md'})
        with self.assertRaisesRegex(ArchiveError, 'has no README.md'):
            gdc26.archive(self.dest, github)

    def test_a_changed_file_is_caught(self):
        folder, _ = gdc26.archive(self.dest, FakeGitHub())
        (folder / gdc26.PER_CAPITA).write_bytes(FILES[gdc26.PER_CAPITA].replace(b'30.0', b'99.0'))
        with self.assertRaisesRegex(ArchiveError, 'does not match SHA256SUMS'):
            gdc26.GDC26(folder)


class Estimate(unittest.TestCase):
    PUSHES = {('DZ', (2025, 3)): 100, ('DZ', (2025, 4)): 200, ('DZ', (2026, 1)): 300, ('DZ', (2026, 2)): 400}
    PEOPLE = {'DZ': {'2024': 1, '2025': 10_000}}

    def released(self, last):
        return [q for q in ((2025, 2), (2025, 3), (2025, 4), (2026, 1), (2026, 2), (2026, 3)) if q <= last]

    def test_all_four_quarters_released(self):
        est = gdc26.estimate('DZ', self.PUSHES, self.released((2026, 3)), self.PEOPLE)
        self.assertEqual((est.quarters, est.assumed, est.pushes), ((100, 200, 300, 400), 0, 1000))
        self.assertEqual(est.per_1k, 100.0)

    def test_a_quarter_still_to_come_repeats_the_latest(self):
        est = gdc26.estimate('DZ', self.PUSHES, self.released((2026, 1)), self.PEOPLE)
        self.assertEqual((est.quarters, est.assumed), ((100, 200, 300, 300), 1))
        est = gdc26.estimate('DZ', self.PUSHES, self.released((2025, 3)), self.PEOPLE)
        self.assertEqual((est.quarters, est.assumed), ((100, 100, 100, 100), 3))

    def test_no_estimate_without_the_first_quarter_or_the_economy(self):
        self.assertIsNone(gdc26.estimate('DZ', self.PUSHES, self.released((2025, 2)), self.PEOPLE))
        self.assertIsNone(gdc26.estimate('MA', self.PUSHES, self.released((2026, 1)), self.PEOPLE))
        self.assertIsNone(gdc26.estimate('DZ', self.PUSHES, [], self.PEOPLE))

    def test_the_population_year_is_githubs(self):
        est = gdc26.estimate('DZ', self.PUSHES, self.released((2026, 3)), {'DZ': {'2026': 5, '2025': 10_000}})
        self.assertEqual((est.year, est.working_age), (2025, 10_000))
        self.assertIsNone(gdc26.estimate('DZ', self.PUSHES, self.released((2026, 3)), {}).per_1k)


class Baseline(unittest.TestCase):
    """PRD Appendix A.6, from the archived files and the committed population cache."""

    @classmethod
    def setUpClass(cls):
        cls.lists = gdc26.GDC26()
        cls.population = json.loads((ROOT / 'data' / 'population.json').read_text())['series']['SP.POP.1564.TO']['values']

    def test_africas_top_ten(self):
        self.assertEqual([(e.economy, round(e.per_1k)) for e in self.lists.africa],
                         [('MU', 272), ('TN', 256), ('KE', 167), ('MA', 163), ('RW', 140), ('EG', 134), ('ZA', 123),
                          ('BW', 107), ('GH', 103), ('SZ', 102)])
        self.assertNotIn('DZ', [e.economy for e in self.lists.africa + self.lists.world])

    def test_github_used_the_world_bank_2025_working_age_population(self):
        for e in self.lists.africa:
            self.assertEqual(e.working_age, self.population[e.economy][str(gdc26.POPULATION_YEAR)], e.economy)

    def test_algerias_estimate(self):
        derived = ROOT / 'data' / 'derived' / json.loads((ROOT / 'data' / 'derived' / 'latest.json').read_text())['folder']
        rows = json.loads((derived / 'gdc26.json').read_text())['rows']
        dz = next(r for r in rows if r['list'] == 'estimate' and r['economy'] == 'DZ')
        self.assertEqual(round(dz['per_1k_working_age']), 67)
        tenth = self.lists.africa[-1].per_1k
        self.assertAlmostEqual(tenth / dz['per_1k_working_age'], 1.5, delta=0.05, msg='"roughly 1.5× current push volume"')


if __name__ == '__main__':
    unittest.main()
