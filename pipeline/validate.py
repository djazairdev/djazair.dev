"""Validate an archived release before anything is computed (ticket #10; PRD IDX-03, AC-IDX-5).

Checks every file's columns, value types, economy codes and duplicate rows, and that the
quarterly series run from 2020 Q1 to the release's quarter without gaps, for the dataset
and for every economy the Index reports on. A failed check stops the pipeline: nothing is
computed or published, the last good data and site stay live, and the scheduled run opens
an issue with the report.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from .config import CORE_PEERS, FILES, FIRST_QUARTER, HOME, NORTH_AFRICA
from .release import Archive, ArchiveError

SCHEMAS = {
    'developers': ('developers', 'iso2_code', 'year', 'quarter'),
    'git_pushes': ('git_pushes', 'iso2_code', 'year', 'quarter'),
    'repositories': ('repositories', 'iso2_code', 'year', 'quarter'),
    'organizations': ('organizations', 'iso2_code', 'year', 'quarter'),
    'languages': ('num_pushers', 'language', 'language_type', 'iso2_code', 'year', 'quarter'),
    'topics': ('num_pushers', 'topic', 'iso2_code', 'year', 'quarter'),
    'licenses': ('num_pushers', 'spdx_license', 'iso2_code', 'year', 'quarter'),
    'economy_collaborators': ('weight', 'source', 'destination', 'year', 'quarter'),
}
COUNTS = {'developers', 'git_pushes', 'repositories', 'organizations', 'num_pushers', 'weight'}
CODES = {'iso2_code', 'source', 'destination'}
SERIES = ('developers', 'git_pushes', 'repositories', 'organizations')   # quarterly series every indicator uses
REPORTED = tuple(sorted(set(NORTH_AFRICA) | set(CORE_PEERS)))
WHOLE = re.compile(r'\d+')
CODE = re.compile(r'[A-Z]{2}')
EXAMPLES = 5


def quarter_range(first: tuple, last: tuple) -> list:
    out, (y, q) = [], first
    while (y, q) <= last:
        out.append((y, q))
        y, q = (y, q + 1) if q < 4 else (y + 1, 1)
    return out


def qname(yq: tuple) -> str:
    return f'{yq[0]}-Q{yq[1]}'


def qlist(qs) -> str:
    qs = sorted(qs)
    shown = ', '.join(qname(q) for q in qs[:6])
    return shown + (f' and {len(qs) - 6} more' if len(qs) > 6 else '')


@dataclass
class Report:
    commit: str
    quarter: str
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    rows: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def markdown(self) -> str:
        """The report as an issue body."""
        verdict = 'passed' if self.ok else 'failed'
        out = [f'Validation of GitHub Innovation Graph release `{self.commit[:12]}` ({self.quarter} data) **{verdict}**.', '']
        if self.errors:
            out += ['### Errors', '', 'Nothing was computed or published. The last good data and site stay live.', '']
            out += [f'- {e}' for e in self.errors] + ['']
        if self.warnings:
            out += ['### Warnings', ''] + [f'- {w}' for w in self.warnings] + ['']
        out += ['### Rows read', '', '| File | Rows |', '|---|---:|']
        out += [f'| `{name}.csv` | {count:,} |' for name, count in self.rows.items()]
        out += ['', 'Source: https://github.com/github/innovationgraph/tree/' + self.commit + '/data. '
                'How to fix and rerun: `pipeline/README.md`.']
        return '\n'.join(out) + '\n'


def _check_row(row: dict) -> list:
    bad = []
    for col, value in row.items():
        if col in COUNTS:
            if not WHOLE.fullmatch(value):
                bad.append(f'{col} {value!r} is not a whole number')
        elif col in CODES:
            if not CODE.fullmatch(value):
                bad.append(f'{col} {value!r} is not a two-letter economy code')
        elif col == 'year':
            if not (WHOLE.fullmatch(value) and 2020 <= int(value) <= 2100):
                bad.append(f'year {value!r} is not a year from 2020')
        elif col == 'quarter':
            if value not in ('1', '2', '3', '4'):
                bad.append(f'quarter {value!r} is not 1 to 4')
        elif not value.strip():
            bad.append(f'{col} is empty')
    return bad


def validate(archive: Archive) -> Report:
    report = Report(archive.commit, archive.quarter)
    last = tuple(int(x) for x in archive.quarter.split('-Q'))
    expected = quarter_range(FIRST_QUARTER, last)
    quarters, present = {}, {name: set() for name in SERIES}
    latest_dev = {}

    for name in FILES:
        try:
            text = archive.read(name).decode('utf-8')
        except (ArchiveError, UnicodeDecodeError) as err:
            report.errors.append(f'`{name}.csv`: {err}')
            continue
        reader = csv.reader(io.StringIO(text))
        header = next(reader, [])
        schema = SCHEMAS[name]
        if sorted(header) != sorted(schema):
            missing = [c for c in schema if c not in header]
            extra = [c for c in header if c not in schema]
            detail = '; '.join(filter(None, [f'missing {", ".join(missing)}' if missing else '',
                                             f'unexpected {", ".join(extra)}' if extra else '']))
            report.errors.append(f'`{name}.csv`: the columns changed ({detail}). Expected: {", ".join(schema)}.')
            continue
        key_cols = [c for c in schema if c not in COUNTS]
        keys, seen, problems, count = set(), set(), [], 0
        for line, fields in enumerate(reader, start=2):
            count += 1
            if len(fields) != len(header):
                problems.append(f'line {line} has {len(fields)} fields, not {len(header)}')
                continue
            row = dict(zip(header, fields))
            bad = _check_row(row)
            if bad:
                problems.append(f'line {line}: {"; ".join(bad)}')
                continue
            key = tuple(row[c] for c in key_cols)
            if key in keys:
                problems.append(f'line {line} repeats {", ".join(key)}')
                continue
            keys.add(key)
            yq = (int(row['year']), int(row['quarter']))
            seen.add(yq)
            if name in SERIES:
                present[name].add((row['iso2_code'], yq))
            if name == 'developers' and yq in (last, expected[-2] if len(expected) > 1 else last):
                latest_dev[(row['iso2_code'], yq)] = int(row['developers'])
        report.rows[name] = count
        if problems:
            report.errors.append(f'`{name}.csv`: {len(problems):,} bad rows, for example: ' + '; '.join(problems[:EXAMPLES]) + '.')
        quarters[name] = seen

    for name, seen in quarters.items():
        outside = [q for q in seen if q < FIRST_QUARTER or q > last]
        if outside:
            report.errors.append(f'`{name}.csv`: rows for {qlist(outside)}, outside 2020-Q1 to {archive.quarter}.')
        span = expected if name in SERIES else quarter_range(FIRST_QUARTER, max(seen, default=last))
        gaps = [q for q in span if q not in seen]
        if gaps:
            report.errors.append(f'`{name}.csv`: no rows at all for {qlist(gaps)}.')
        if name not in SERIES and seen and max(seen) != last:
            report.warnings.append(f'`{name}.csv` ends at {qname(max(seen))}, not {archive.quarter}.')

    # Algeria needs every series in every quarter, and every economy we report on needs its
    # account counts. GitHub leaves out small values, so a peer may miss a quarter of another
    # series: medians and ranks then use the members with data (PRD §9.2).
    for name in SERIES:
        if name not in quarters:
            continue
        for code in REPORTED:
            gaps = [q for q in expected if (code, q) not in present[name]]
            if not gaps:
                continue
            message = f'`{name}.csv`: {code} has no value for {qlist(gaps)}.'
            if code == HOME or name == 'developers':
                report.errors.append(message)
            else:
                report.warnings.append(message + ' Medians and ranks for those quarters leave it out.')

    if len(expected) > 1:
        before = expected[-2]
        for code in REPORTED:
            now, prev = latest_dev.get((code, last)), latest_dev.get((code, before))
            if now is not None and prev and now < prev * 0.9:
                report.warnings.append(f'{code}: developer accounts fell {1 - now / prev:.0%} in a quarter '
                                       f'({prev:,} to {now:,}). Accounts are a running total, so check for a method change.')
    return report
