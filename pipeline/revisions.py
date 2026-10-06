"""Revisions: past values a new release changed (ticket #12; PRD §9.4, §9.5).

GitHub can revise earlier quarters in a new release. Comparing the four quarterly series
with the previous archived release, for every quarter the previous release covered, turns
any change into a report for editorial review instead of letting it pass silently.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import CORE_PEERS, HOME, NORTH_AFRICA
from .release import Archive

SERIES = ('developers', 'git_pushes', 'repositories', 'organizations')
WATCHED = (HOME,) + tuple(c for c in dict.fromkeys(NORTH_AFRICA + CORE_PEERS) if c != HOME)


@dataclass(frozen=True)
class Revision:
    series: str
    code: str
    quarter: str
    old: object        # None when the newer release added a value
    new: object        # None when the newer release removed one


@dataclass
class RevisionReport:
    old: str           # commit of the earlier release
    new: str
    old_quarter: str
    new_quarter: str
    revisions: list = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.revisions)

    def markdown(self) -> str:
        head = (f'Comparing GitHub Innovation Graph release `{self.new[:12]}` ({self.new_quarter} data) with '
                f'`{self.old[:12]}` ({self.old_quarter} data), for every quarter up to {self.old_quarter}:')
        if not self.found:
            return head + ' **no past value changed**.\n'
        watched = [r for r in self.revisions if r.code in WATCHED]
        out = [head + f' **{len(self.revisions):,} past values changed**, {len(watched):,} of them for economies the Index '
               f'reports on. Review them before publishing: the derived data and the report must say what changed.', '',
               '| Series | Economy | Quarter | Before | Now | Change |', '|---|---|---|---:|---:|---:|']
        shown = sorted(self.revisions, key=lambda r: (r.code not in WATCHED, WATCHED.index(r.code) if r.code in WATCHED else 0,
                                                      r.code, r.series, r.quarter))
        for r in shown[:60]:
            change = f'{r.new / r.old - 1:+.2%}' if r.old and r.new is not None else ('added' if r.old is None else 'removed')
            out.append(f'| {r.series} | {r.code} | {r.quarter} | {_n(r.old)} | {_n(r.new)} | {change} |')
        if len(shown) > 60:
            out.append(f'\n…and {len(shown) - 60:,} more.')
        return '\n'.join(out) + '\n'


def _n(value) -> str:
    return '—' if value is None else f'{value:,}'


def _values(archive: Archive, series: str, upto: tuple) -> dict:
    out = {}
    for row in archive.rows(series):
        q = (int(row['year']), int(row['quarter']))
        if q <= upto:
            out[(row['iso2_code'], q)] = int(row[series])
    return out


def compare(old: Archive, new: Archive) -> RevisionReport:
    """Every value of the older release's quarters that the newer release changed, added or removed."""
    upto = tuple(int(x) for x in old.quarter.split('-Q'))
    report = RevisionReport(old.commit, new.commit, old.quarter, new.quarter)
    for series in SERIES:
        before, after = _values(old, series, upto), _values(new, series, upto)
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                code, (y, q) = key
                report.revisions.append(Revision(series, code, f'{y}-Q{q}', before.get(key), after.get(key)))
    return report
