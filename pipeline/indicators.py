"""The Index indicators for every economy and quarter (ticket #11; PRD §9.2, §9.3).

``Dataset`` holds one archived release; ``Index`` computes from it:

    accounts               developers(c, q)
    yoy                    developers(c, q) / developers(c, q−4) − 1
    since_2020             developers(c, q) / developers(c, 2020 Q1) − 1
    pushes_per_account     git_pushes(c, q) / developers(c, q)
    pushes_per_account_4q  Σ pushes over the last 4 quarters / mean accounts over them / 4
    repos_per_account      repositories(c, q) / developers(c, q)
    orgs_per_account       organizations(c, q) / developers(c, q)
    accounts_per_million   developers(c, q) / population(c) × 10⁶ (World Bank, latest year)
    topics                 topics GitHub publishes for (c, q): those with 100+ developers

plus the languages and collaboration partners of each economy. An indicator is missing,
never zero, when an input is missing. Peer-group medians use the members with data; ranks
are in descending order and ties share a rank. The Africa ranking group is every African
economy with at least 20,000 accounts a year before the quarter, so it starts in 2021 Q1.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

from .config import AFRICA, AFRICA_MIN_ACCOUNTS, CORE_PEERS, NORTH_AFRICA
from .population import Population
from .release import Archive
from .validate import quarter_range

INDICATORS = ('accounts', 'yoy', 'since_2020', 'pushes_per_account', 'pushes_per_account_4q', 'repos_per_account',
              'orgs_per_account', 'accounts_per_million', 'topics')
GROUPS = ('north_africa', 'core_peers', 'africa')
SERIES = ('developers', 'git_pushes', 'repositories', 'organizations')


def qkey(q: tuple) -> str:
    return f'{q[0]}-Q{q[1]}'


@dataclass
class Dataset:
    commit: str
    quarter: tuple                                    # the release's latest quarter
    quarters: list                                    # 2020 Q1 to ``quarter``
    series: dict = field(default_factory=dict)        # name -> {(code, q): int}
    topics: dict = field(default_factory=dict)        # (code, q) -> {topic: pushers}
    languages: dict = field(default_factory=dict)     # (code, q) -> {language: (type, pushers)}
    licenses: dict = field(default_factory=dict)      # (code, q) -> {licence: pushers}
    partners: dict = field(default_factory=dict)      # (code, q) -> {destination: weight}

    @classmethod
    def load(cls, archive: Archive) -> 'Dataset':
        last = tuple(int(x) for x in archive.quarter.split('-Q'))
        ds = cls(archive.commit, last, quarter_range((2020, 1), last))
        q = lambda row: (int(row['year']), int(row['quarter']))
        for name in SERIES:
            ds.series[name] = {(r['iso2_code'], q(r)): int(r[name]) for r in archive.rows(name)}
        for r in archive.rows('topics'):
            ds.topics.setdefault((r['iso2_code'], q(r)), {})[r['topic']] = int(r['num_pushers'])
        for r in archive.rows('languages'):
            ds.languages.setdefault((r['iso2_code'], q(r)), {})[r['language']] = (r['language_type'], int(r['num_pushers']))
        for r in archive.rows('licenses'):
            ds.licenses.setdefault((r['iso2_code'], q(r)), {})[r['spdx_license']] = int(r['num_pushers'])
        for r in archive.rows('economy_collaborators'):
            ds.partners.setdefault((r['source'], q(r)), {})[r['destination']] = int(r['weight'])
        return ds

    def economies(self) -> list:
        return sorted({c for c, _ in self.series['developers']})


def rank_of(values: dict) -> dict:
    """Descending ranks; ties share a rank (1, 2, 2, 4)."""
    return {c: 1 + sum(1 for x in values.values() if x > v) for c, v in values.items()}


class Index:
    def __init__(self, ds: Dataset, population: Population):
        self.ds = ds
        self.population = population
        self.population_year = {}
        self.values = {name: {} for name in INDICATORS}
        for i, q in enumerate(ds.quarters):
            for code in ds.economies():
                for name in INDICATORS:
                    v = self._compute(name, code, i)
                    if v is not None:
                        self.values[name][(code, q)] = v
        self.members = {q: self._groups(i) for i, q in enumerate(ds.quarters)}

    # ---- indicators
    def _get(self, series: str, code: str, i: int) -> Optional[int]:
        if i < 0:
            return None
        return self.ds.series[series].get((code, self.ds.quarters[i]))

    def _compute(self, name: str, code: str, i: int):
        dev = self._get('developers', code, i)
        if dev is None or dev == 0:
            return None
        if name == 'accounts':
            return dev
        if name == 'yoy':
            before = self._get('developers', code, i - 4)
            return dev / before - 1 if before else None
        if name == 'since_2020':
            first = self._get('developers', code, 0)
            return dev / first - 1 if first else None
        if name in ('pushes_per_account', 'repos_per_account', 'orgs_per_account'):
            series = {'pushes_per_account': 'git_pushes', 'repos_per_account': 'repositories',
                      'orgs_per_account': 'organizations'}[name]
            num = self._get(series, code, i)
            return num / dev if num is not None else None
        if name == 'pushes_per_account_4q':
            if i < 3:
                return None
            pushes = [self._get('git_pushes', code, k) for k in range(i - 3, i + 1)]
            devs = [self._get('developers', code, k) for k in range(i - 3, i + 1)]
            if None in pushes or None in devs:
                return None
            return sum(pushes) / (sum(devs) / 4) / 4
        if name == 'accounts_per_million':
            year, people = self.population.get(code)
            if not people:
                return None
            self.population_year[code] = year
            return dev / people * 1e6
        if name == 'topics':
            return len(self.ds.topics.get((code, self.ds.quarters[i]), {}))
        raise KeyError(name)

    def value(self, name: str, code: str, q: tuple):
        return self.values[name].get((code, q))

    def series(self, name: str, code: str) -> list:
        """One value per quarter, oldest first (None where missing)."""
        return [self.values[name].get((code, q)) for q in self.ds.quarters]

    # ---- groups, medians and ranks
    def _groups(self, i: int) -> dict:
        q = self.ds.quarters[i]
        has = lambda c: self._get('developers', c, i) is not None
        africa = []
        if i >= 4:
            africa = [c for c in AFRICA if has(c) and (self._get('developers', c, i - 4) or 0) >= AFRICA_MIN_ACCOUNTS]
        return {'north_africa': [c for c in NORTH_AFRICA if has(c)], 'core_peers': [c for c in CORE_PEERS if has(c)],
                'africa': sorted(africa)}

    def group(self, group: str, q: tuple) -> list:
        return self.members[q][group]

    def group_values(self, name: str, group: str, q: tuple) -> dict:
        return {c: self.values[name][(c, q)] for c in self.group(group, q) if (c, q) in self.values[name]}

    def median(self, name: str, group: str, q: tuple) -> Optional[float]:
        vals = list(self.group_values(name, group, q).values())
        return statistics.median(vals) if vals else None

    def ranks(self, name: str, group: str, q: tuple) -> dict:
        return rank_of(self.group_values(name, group, q))

    def rank(self, name: str, group: str, q: tuple, code: str) -> Optional[tuple]:
        """(rank, number ranked) for ``code``, or None if it isn't ranked."""
        ranks = self.ranks(name, group, q)
        return (ranks[code], len(ranks)) if code in ranks else None

    # ---- details
    def languages(self, code: str, q: tuple) -> list:
        """(language, type, developers pushing) by size. Can't be added up: one developer can push in several."""
        langs = self.ds.languages.get((code, q), {})
        return sorted(((lang, kind, n) for lang, (kind, n) in langs.items()), key=lambda t: (-t[2], t[0]))

    def partners(self, code: str, q: tuple) -> list:
        """(economy, collaboration weight) by weight."""
        return sorted(self.ds.partners.get((code, q), {}).items(), key=lambda t: (-t[1], t[0]))

    def topic_list(self, code: str, q: tuple) -> list:
        return sorted(self.ds.topics.get((code, q), {}).items(), key=lambda t: (-t[1], t[0]))
