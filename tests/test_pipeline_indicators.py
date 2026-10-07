"""Indicators for every economy and quarter (ticket #11), on the made-up fixture release."""
import json
import shutil
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igfixture import ECONOMIES, RATIOS, TOPICS, FakeGitHub, accounts, release_files  # noqa: E402
from pipeline import release  # noqa: E402
from pipeline.config import NORTH_AFRICA, RAW_DIR  # noqa: E402
from pipeline.indicators import INDICATORS, Dataset, Index, rank_of  # noqa: E402
from pipeline.population import Population  # noqa: E402

POPULATION = {'DZ': {'2024': 46_000_000, '2025': 47_000_000}, 'MA': {'2024': 38_000_000}}


def fixture_index(tmp: Path, files=None) -> Index:
    github = FakeGitHub(files or release_files())
    folder, _ = release.archive(release.latest(github), tmp / 'raw', github)
    pop = tmp / 'population.json'
    pop.write_text(json.dumps({'series': {'SP.POP.TOTL': {'values': POPULATION}}}))
    return Index(Dataset.load(release.Archive(folder)), Population(pop))


class Indicators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.ix = fixture_index(cls.tmp)
        cls.last = (2021, 2)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_accounts_and_growth(self):
        ix = self.ix
        self.assertEqual(ix.value('accounts', 'DZ', (2020, 1)), 100_000)
        self.assertEqual(ix.value('accounts', 'DZ', self.last), accounts('DZ', 5))
        self.assertAlmostEqual(ix.value('yoy', 'DZ', (2021, 1)), accounts('DZ', 4) / accounts('DZ', 0) - 1)
        self.assertAlmostEqual(ix.value('since_2020', 'DZ', self.last), accounts('DZ', 5) / 100_000 - 1)
        self.assertIsNone(ix.value('yoy', 'DZ', (2020, 4)), 'no year-earlier quarter yet')

    def test_ratios_per_account(self):
        for name, series in (('pushes_per_account', 'git_pushes'), ('repos_per_account', 'repositories'),
                             ('orgs_per_account', 'organizations')):
            expected = round(accounts('KE', 3) * RATIOS[series]) / accounts('KE', 3)
            self.assertAlmostEqual(self.ix.value(name, 'KE', (2020, 4)), expected, msg=name)

    def test_four_quarter_push_average(self):
        pushes = [round(accounts('DZ', k) * RATIOS['git_pushes']) for k in range(2, 6)]
        devs = [accounts('DZ', k) for k in range(2, 6)]
        self.assertAlmostEqual(self.ix.value('pushes_per_account_4q', 'DZ', self.last), sum(pushes) / (sum(devs) / 4) / 4)
        self.assertIsNone(self.ix.value('pushes_per_account_4q', 'DZ', (2020, 3)))

    def test_accounts_per_million_use_the_latest_population(self):
        self.assertAlmostEqual(self.ix.value('accounts_per_million', 'DZ', self.last), accounts('DZ', 5) / 47_000_000 * 1e6)
        self.assertEqual(self.ix.population_year['DZ'], 2025)
        self.assertIsNone(self.ix.value('accounts_per_million', 'TN', self.last), 'no population, no value')

    def test_topics_count_what_github_publishes(self):
        self.assertEqual(self.ix.value('topics', 'DZ', self.last), len(TOPICS['DZ']))
        self.assertEqual(self.ix.value('topics', 'LY', self.last), 0, 'below the threshold everywhere')
        self.assertIsNone(self.ix.value('topics', 'FR', self.last), 'not in the data')

    def test_every_economy_and_quarter_with_inputs_has_its_indicators(self):
        for code in ECONOMIES:
            for i, q in enumerate(self.ix.ds.quarters):
                for name in INDICATORS:
                    needs_year = name == 'yoy' and i < 4 or name == 'pushes_per_account_4q' and i < 3
                    no_pop = name == 'accounts_per_million' and code not in POPULATION
                    if not (needs_year or no_pop):
                        self.assertIsNotNone(self.ix.value(name, code, q), (name, code, q))

    def test_groups(self):
        ix = self.ix
        self.assertEqual(ix.group('north_africa', self.last), list(NORTH_AFRICA))
        self.assertEqual(ix.group('core_peers', self.last), ['MA', 'TN', 'EG', 'NG', 'KE', 'ZA'])
        self.assertEqual(ix.group('africa', (2020, 4)), [], 'needs a year-earlier quarter')
        # 20,000+ accounts a year earlier: Senegal (18,000 in 2020 Q1) is not in; Ghana is
        self.assertEqual(ix.group('africa', (2021, 1)), ['DZ', 'EG', 'GH', 'KE', 'MA', 'NG', 'TN', 'ZA'])

    def test_medians_use_members_with_data(self):
        q = (2021, 1)
        yoy = [accounts(c, 4) / accounts(c, 0) - 1 for c in NORTH_AFRICA]
        self.assertAlmostEqual(self.ix.median('yoy', 'north_africa', q), statistics.median(yoy))
        self.assertIsNone(self.ix.median('yoy', 'africa', (2020, 2)))

    def test_ranks_descend_and_ties_share_a_rank(self):
        self.assertEqual(rank_of({'A': 3, 'B': 5, 'C': 5, 'D': 1}), {'B': 1, 'C': 1, 'A': 3, 'D': 4})
        self.assertEqual(self.ix.rank('accounts', 'north_africa', self.last, 'EG'), (1, 7))
        self.assertEqual(self.ix.rank('accounts', 'north_africa', self.last, 'MR'), (7, 7))

    def test_details(self):
        self.assertEqual([lang for lang, _, _ in self.ix.languages('DZ', self.last)], ['HTML', 'JavaScript', 'Python'])
        self.assertEqual(self.ix.partners('DZ', self.last), [('US', 90), ('EU', 80), ('FR', 40)])
        self.assertEqual(self.ix.senders('DZ', self.last), [('FR', 50), ('MA', 30)])


class MissingInputs(unittest.TestCase):
    def test_a_missing_input_gives_a_missing_value_not_zero(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        files = release_files()
        files['git_pushes'] = b''.join(line + b'\n' for line in files['git_pushes'].splitlines() if not line.endswith(b',MA,2021,1'))
        ix = fixture_index(tmp, files)
        self.assertIsNone(ix.value('pushes_per_account', 'MA', (2021, 1)))
        self.assertIsNone(ix.value('pushes_per_account_4q', 'MA', (2021, 2)), 'its window includes 2021 Q1')
        self.assertNotIn('MA', ix.group_values('pushes_per_account', 'north_africa', (2021, 1)))
        self.assertEqual(ix.rank('pushes_per_account', 'north_africa', (2021, 1), 'DZ')[1], 6)


class RealRelease(unittest.TestCase):
    def test_every_economy_and_quarter_with_inputs_has_its_indicators(self):
        ds = Dataset.load(release.Archive(RAW_DIR / '054c7dbc527518fa2ecfd316efe2aa01f3986c39'))
        ix = Index(ds, Population())
        for (code, q), dev in ds.series['developers'].items():
            self.assertEqual(ix.value('accounts', code, q), dev)
            if (code, q) in ds.series['git_pushes']:
                self.assertIsNotNone(ix.value('pushes_per_account', code, q))
            self.assertIsNotNone(ix.value('topics', code, q))
        self.assertEqual(len(ix.group('africa', ds.quarter)), 29)


if __name__ == '__main__':
    unittest.main()
