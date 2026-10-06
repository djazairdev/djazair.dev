"""Regression tests: the pipeline reproduces PRD Appendix A from the Q1 2026 release (ticket #12;
AC-IDX-1, AC-IDX-2, AC-IDX-3). Values are compared as the appendix rounds them.

The appendix was computed with 2024 World Bank population, so these tests pin that year;
the published data uses each economy's latest year and records it."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import release  # noqa: E402
from pipeline.config import RAW_DIR  # noqa: E402
from pipeline.indicators import Dataset, Index  # noqa: E402
from pipeline.population import Population  # noqa: E402

Q1_2026 = (2026, 1)
RELEASE = '054c7dbc527518fa2ecfd316efe2aa01f3986c39'

# A.1: accounts Q1 2020, accounts Q1 2026, since 2020 (%), year on year (%), per million,
# pushes per account, 4-quarter average, repositories per account, organisations per account, topics
A1 = {
    'DZ': (91_819, 586_990, 539, 49.1, 12_539, 1.06, 0.84, 1.04, 0.0315, 3),
    'MA': (142_405, 906_406, 536, 43.2, 23_802, 1.39, 1.20, 1.65, 0.0428, 13),
    'EG': (236_751, 1_626_418, 587, 43.9, 13_956, 1.57, 1.53, 2.05, 0.0341, 37),
    'NG': (173_641, 1_794_519, 933, 35.8, 7_712, 1.66, 1.45, 2.61, 0.0412, 23),
    'KE': (90_770, 678_197, 647, 46.3, 12_018, 2.31, 2.28, 4.77, 0.0434, 11),
    'ZA': (202_767, 1_058_997, 422, 42.8, 16_545, 1.30, 1.21, 1.72, 0.0432, 7),
    'TN': (88_631, 420_582, 375, 32.9, 34_257, 1.35, 1.29, 2.33, 0.0470, 18),
}
# A.2: group, members, year-on-year growth (%), pushes, repositories and organisations per account
A2 = {'north_africa': (7, 44.0, 1.34, 1.52, 0.0315), 'core_peers': (6, 43.0, 1.48, 2.19, 0.0430),
      'africa': (29, 56.5, 1.69, 1.75, 0.0428)}


class Baseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = Dataset.load(release.Archive(RAW_DIR / RELEASE))
        cls.ix = Index(cls.ds, Population(year=2024))

    def v(self, name, code, q=Q1_2026):
        return self.ix.value(name, code, q)

    def test_the_release_is_q1_2026(self):
        self.assertEqual(self.ds.quarter, Q1_2026)

    def test_algeria_headline(self):
        self.assertEqual(self.v('accounts', 'DZ'), 586_990)
        self.assertEqual(round(self.v('yoy', 'DZ') * 100, 1), 49.1)
        self.assertEqual(round(self.v('pushes_per_account', 'DZ'), 2), 1.06)
        self.assertEqual(round(self.v('repos_per_account', 'DZ'), 2), 1.04)
        self.assertEqual(round(self.v('orgs_per_account', 'DZ'), 4), 0.0315)
        self.assertEqual(self.v('accounts', 'DZ') - self.v('accounts', 'DZ', (2025, 1)), 193_425)

    def test_a1_peer_table(self):
        for code, row in A1.items():
            got = (self.v('accounts', code, (2020, 1)), self.v('accounts', code), round(self.v('since_2020', code) * 100),
                   round(self.v('yoy', code) * 100, 1), round(self.v('accounts_per_million', code)),
                   round(self.v('pushes_per_account', code), 2), round(self.v('pushes_per_account_4q', code), 2),
                   round(self.v('repos_per_account', code), 2), round(self.v('orgs_per_account', code), 4), self.v('topics', code))
            self.assertEqual(got, row, code)

    def test_a2_group_medians(self):
        for group, (n, yoy, pushes, repos, orgs) in A2.items():
            got = (len(self.ix.group(group, Q1_2026)), round(self.ix.median('yoy', group, Q1_2026) * 100, 1),
                   round(self.ix.median('pushes_per_account', group, Q1_2026), 2),
                   round(self.ix.median('repos_per_account', group, Q1_2026), 2),
                   round(self.ix.median('orgs_per_account', group, Q1_2026), 4))
            self.assertEqual(got, (n, yoy, pushes, repos, orgs), group)

    def test_a3_growth_ranks(self):
        self.assertEqual(self.ix.rank('yoy', 'north_africa', Q1_2026, 'DZ'), (3, 7))
        self.assertEqual(self.ix.rank('yoy', 'africa', Q1_2026, 'DZ'), (19, 29))
        north = sorted(self.ix.group_values('yoy', 'north_africa', Q1_2026).items(), key=lambda t: -t[1])
        self.assertEqual([(c, round(v * 100, 1)) for c, v in north],
                         [('MR', 65.9), ('LY', 65.0), ('DZ', 49.1), ('SD', 44.0), ('EG', 43.9), ('MA', 43.2), ('TN', 32.9)])

    def test_algeria_q1_to_q1_growth(self):
        self.assertEqual([round(self.v('yoy', 'DZ', (y, 1)) * 100, 1) for y in range(2021, 2027)],
                         [44.6, 37.0, 30.9, 31.5, 25.6, 49.1])

    def test_index_2020_q1_equals_100(self):
        index = {c: round((self.v('since_2020', c) + 1) * 100) for c in A1}
        self.assertEqual(index, {'DZ': 639, 'MA': 636, 'TN': 475, 'EG': 687, 'NG': 1033, 'KE': 747, 'ZA': 522})

    def test_algerian_ratios_against_a_year_earlier(self):
        cases = {'pushes_per_account': (1.0630, 0.5050, 110.5, (5, 7), (26, 29)),
                 'repos_per_account': (1.0393, 1.1222, -7.4, (5, 7), (27, 29)),
                 'orgs_per_account': (0.0315, 0.0425, -25.8, (4, 7), (25, 29))}
        for name, (now, before, change, north, africa) in cases.items():
            a, b = self.v(name, 'DZ'), self.v(name, 'DZ', (2025, 1))
            self.assertEqual((round(a, 4), round(b, 4), round((a / b - 1) * 100, 1)), (now, before, change), name)
            self.assertEqual(self.ix.rank(name, 'north_africa', Q1_2026, 'DZ'), north, name)
            self.assertEqual(self.ix.rank(name, 'africa', Q1_2026, 'DZ'), africa, name)

    def test_a4_languages(self):
        self.assertEqual([(lang, n) for lang, _, n in self.ix.languages('DZ', Q1_2026)[:8]],
                         [('HTML', 13_477), ('JavaScript', 10_221), ('CSS', 9_825), ('Python', 6_383), ('TypeScript', 4_682),
                          ('Shell', 2_189), ('Dockerfile', 1_819), ('C', 1_582)])

    def test_a5_collaboration_partners(self):
        self.assertEqual(self.ix.partners('DZ', Q1_2026)[:8],
                         [('US', 2_612), ('EU', 2_181), ('FR', 1_232), ('DE', 791), ('JO', 608), ('GB', 504), ('IN', 359),
                          ('CH', 242)])


if __name__ == '__main__':
    unittest.main()
