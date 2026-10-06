"""Publish the Index as CSV and JSON (ticket #13; PRD IDX-15, §9.5 step 3).

Writes ``data/derived/<yyyy-qN>/``: one CSV and one JSON file per table the site shows, a
README with the licence and attribution, and ``manifest.json`` (release, data quarter,
generation time, and every file with its size and checksum). ``data/derived/latest.json``
names the newest quarter. The site builds only from these files.

Output is stable for diffs: rows come in a fixed order, numbers are rounded to six decimal
places, JSON keys are sorted (rows keep their column order, one row per line), and
``generated_at`` changes only when a file does.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import (AFRICA_MIN_ACCOUNTS, ATTRIBUTION, CORE_PEERS, DERIVED_DIR, HOME, LICENCE, LICENCE_URL, NORTH_AFRICA,
                     SOURCE_URL)
from .indicators import INDICATORS, Dataset, Index, qkey, rank_of
from .population import Population
from .release import Archive
from .revisions import RevisionReport, compare

FORMAT_VERSION = 1
DECIMALS = 6
PEERS = tuple(dict.fromkeys(NORTH_AFRICA + CORE_PEERS))          # Algeria, the rest of North Africa, then NG, KE, ZA
GROUPS = ('north_africa', 'core_peers', 'africa', 'algeria_and_peers')
RATES = ('yoy', 'since_2020')                                     # already changes: no change on a year earlier

GROUP_TEXT = {
    'north_africa': 'Algeria, Egypt, Libya, Mauritania, Morocco, Sudan and Tunisia',
    'core_peers': 'Morocco, Tunisia, Egypt, Nigeria, Kenya and South Africa',
    'africa': f'African economies with at least {AFRICA_MIN_ACCOUNTS:,} accounts a year earlier (from 2021 Q1)',
    'algeria_and_peers': 'Algeria and the six core peers',
}


def number_text(v) -> str:
    """A number rounded to six decimal places, in plain notation, without trailing zeros: 586990, 0.491, 1.063021."""
    text = f'{round(float(v), DECIMALS) + 0.0:.{DECIMALS}f}'.rstrip('0').rstrip('.')      # + 0.0 turns -0.0 into 0.0
    return '0' if text == '-0' else text


@dataclass(frozen=True)
class Column:
    name: str
    type: str                 # string, integer, number or boolean
    description: str

    def text(self, v) -> str:
        """The value as CSV holds it (empty when missing); JSON uses the same text for numbers."""
        if v is None:
            return ''
        if self.type == 'integer':
            if not float(v).is_integer():
                raise ValueError(f'{self.name}: {v!r} is not a whole number')
            return str(int(v))
        if self.type == 'number':
            return number_text(v)
        if self.type == 'boolean':
            return 'true' if v else 'false'
        return str(v)

    def json(self, v) -> str:
        if v is None:
            return 'null'
        return json.dumps(str(v), ensure_ascii=False) if self.type == 'string' else self.text(v)

    def schema(self) -> dict:
        return {'name': self.name, 'type': self.type, 'description': self.description}


def S(name, description):
    return Column(name, 'string', description)


def I(name, description):           # noqa: E743
    return Column(name, 'integer', description)


def N(name, description):
    return Column(name, 'number', description)


def B(name, description):
    return Column(name, 'boolean', description)


ECONOMY = S('economy', 'ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union)')
QUARTER = S('quarter', 'Data quarter, as YYYY-QN')
INDICATOR = S('indicator', 'Indicator: one of the indicator columns of the indicators table')
COLUMNS = {
    'accounts': I('accounts', 'Developer accounts located in the economy (a running total)'),
    'yoy': N('yoy', 'Growth in accounts on the same quarter a year earlier: accounts / accounts a year earlier − 1'),
    'since_2020': N('since_2020', 'Growth in accounts since 2020 Q1: accounts / accounts in 2020 Q1 − 1'),
    'pushes_per_account': N('pushes_per_account', 'Git pushes during the quarter / accounts'),
    'pushes_per_account_4q': N('pushes_per_account_4q', 'Pushes over the last four quarters / mean accounts over them / 4'),
    'repos_per_account': N('repos_per_account', 'Repositories / accounts (both running totals)'),
    'orgs_per_account': N('orgs_per_account', 'Organisations / accounts (both running totals)'),
    'accounts_per_million': N('accounts_per_million', 'Accounts per million people (World Bank population, latest year)'),
    'topics': I('topics', 'Topics GitHub publishes for the economy: those with 100 or more developers pushing'),
}


@dataclass
class Table:
    name: str
    title: str
    description: str
    columns: list             # [Column]
    rows: list                # [[value, ...]] in column order

    def csv(self) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator='\n')
        writer.writerow([c.name for c in self.columns])
        for row in self.rows:
            writer.writerow([c.text(v) for c, v in zip(self.columns, row)])
        return buf.getvalue().encode('utf-8')

    def json(self, meta: dict) -> bytes:
        body = {**meta, 'table': self.name, 'title': self.title, 'description': self.description,
                'columns': [c.schema() for c in self.columns], 'rows': '\0rows'}
        text = json.dumps(body, ensure_ascii=False, sort_keys=True, indent=1)
        lines = ['{' + ', '.join(f'"{c.name}": {c.json(v)}' for c, v in zip(self.columns, row)) + '}' for row in self.rows]
        rows = '[\n' + ',\n'.join('  ' + line for line in lines) + '\n ]' if lines else '[]'
        return (text.replace('"\\u0000rows"', rows, 1) + '\n').encode('utf-8')


class Publisher:
    """The tables, computed from one release."""

    def __init__(self, ix: Index, revisions: Optional[RevisionReport] = None):
        self.ix, self.ds = ix, ix.ds
        self.q = ix.ds.quarter
        self.year_before = ix.ds.quarters[-5] if len(ix.ds.quarters) > 4 else None
        self.revision_report = revisions

    def members(self, group: str, q: tuple) -> list:
        if group == 'algeria_and_peers':
            return [c for c in (HOME,) + CORE_PEERS if (c, q) in self.ix.values['accounts']]
        return self.ix.group(group, q)

    def values(self, name: str, group: str, q: tuple) -> dict:
        return {c: self.ix.values[name][(c, q)] for c in self.members(group, q) if (c, q) in self.ix.values[name]}

    def median(self, name: str, group: str, q: tuple):
        vals = list(self.values(name, group, q).values())
        return statistics.median(vals) if vals else None

    def change(self, name: str, code: str):
        if name in RATES or not self.year_before:
            return None
        now, before = self.ix.value(name, code, self.q), self.ix.value(name, code, self.year_before)
        return now / before - 1 if now is not None and before else None

    # ---- the tables
    def overview(self) -> Table:
        cols = [INDICATOR, QUARTER, N('value', 'Algeria, in the indicator’s unit'),
                N('year_earlier', 'Algeria in the same quarter a year earlier'),
                N('change', 'value / year_earlier − 1 (empty for yoy and since_2020, which are already changes)')]
        for group in GROUPS:
            cols += [N(f'{group}_median', f'Median across the members of {group} with data'),
                     I(f'{group}_rank', f'Algeria’s place in {group}: 1 is the highest, ties share a place'),
                     I(f'{group}_ranked', f'Members of {group} with data')]
        rows = []
        for name in INDICATORS:
            row = [name, qkey(self.q), self.ix.value(name, HOME, self.q),
                   self.ix.value(name, HOME, self.year_before) if self.year_before else None, self.change(name, HOME)]
            for group in GROUPS:
                vals = self.values(name, group, self.q)
                row += [self.median(name, group, self.q), rank_of(vals).get(HOME), len(vals)]
            rows.append(row)
        return Table('overview', 'Algeria at a glance',
                     'Algeria’s latest value of each indicator, the same quarter a year earlier, and its place and the median '
                     'in each peer group. One row per indicator.', cols, rows)

    def peers(self) -> Table:
        first = self.ds.quarters[0]
        level = INDICATORS[:-2]                                   # all but accounts_per_million and topics
        cols = [ECONOMY, B('north_africa', 'In the North Africa group'), B('core_peer', 'One of the six core peers'), QUARTER,
                I('accounts_2020_q1', 'Accounts in 2020 Q1')]
        cols += [COLUMNS[n] for n in level]
        cols += [COLUMNS['accounts_per_million'], I('population_year', 'Year of the World Bank population used'), COLUMNS['topics']]
        # The inputs, so every ratio above can be recomputed from this file.
        cols += [I('git_pushes', 'Git pushes during the quarter (Innovation Graph git_pushes)'),
                 I('repositories', 'Repositories, a running total (Innovation Graph repositories)'),
                 I('organizations', 'Organisations, a running total (Innovation Graph organizations)'),
                 I('population', 'World Bank population (SP.POP.TOTL) in population_year')]
        rows = []
        for code in PEERS:
            year, people = self.ix.population.get(code)
            counts = [self.ds.series[name].get((code, self.q)) for name in ('git_pushes', 'repositories', 'organizations')]
            rows.append([code, code in NORTH_AFRICA, code in CORE_PEERS, qkey(self.q), self.ix.value('accounts', code, first)]
                        + [self.ix.value(n, code, self.q) for n in level]
                        + [self.ix.value('accounts_per_million', code, self.q), year if people else None,
                           self.ix.value('topics', code, self.q)] + counts + [people])
        return Table('peers', 'Algeria and its peers',
                     'Algeria, the rest of North Africa and the core peers in the latest quarter, with the counts behind '
                     'each ratio.', cols, rows)

    def groups(self) -> Table:
        cols = [S('group', '; '.join(f'{g}: {t}' for g, t in GROUP_TEXT.items())), QUARTER, I('members', 'Members with data'),
                S('economies', 'Member codes, separated by spaces')]
        cols += [N(f'median_{n}', f'Median of {n} across the members with data') for n in INDICATORS]
        rows = []
        for group in GROUPS:
            for q in self.ds.quarters:
                members = self.members(group, q)
                if members:
                    rows.append([group, qkey(q), len(members), ' '.join(members)] + [self.median(n, group, q) for n in INDICATORS])
        return Table('groups', 'Peer groups and their medians',
                     'The members of each peer group in every quarter, and the median of each indicator across the members '
                     'with data.', cols, rows)

    def ranks(self) -> Table:
        cols = [S('group', 'Peer group (see the groups table)'), QUARTER, INDICATOR, ECONOMY, N('value', 'Value of the indicator'),
                I('rank', 'Place: 1 is the highest, ties share a place'), I('ranked', 'Members with data')]
        rows = []
        for group in GROUPS:
            for name in INDICATORS:
                vals = self.values(name, group, self.q)
                ranks = rank_of(vals)
                rows += [[group, qkey(self.q), name, c, vals[c], ranks[c], len(vals)]
                         for c in sorted(vals, key=lambda c: (ranks[c], c))]
        return Table('ranks', 'Ranks in each peer group',
                     'Every member’s place in each peer group for each indicator in the latest quarter, highest first. Earlier '
                     'quarters can be ranked from the indicators and groups tables.', cols, rows)

    def trends(self) -> Table:
        cols = [QUARTER, INDICATOR, S('series', 'ISO code of the economy, or median_<group> for a peer-group median'),
                N('value', 'Value; empty where an input is missing')]
        rows = []
        for q in self.ds.quarters:
            for name in INDICATORS:
                rows += [[qkey(q), name, code, self.ix.value(name, code, q)] for code in PEERS]
                rows += [[qkey(q), name, f'median_{g}', self.median(name, g, q)] for g in ('north_africa', 'core_peers', 'africa')]
        return Table('trends', 'Quarterly series',
                     'Every indicator in every quarter since 2020 Q1 for Algeria, the rest of North Africa and the core peers, '
                     'with the peer-group medians.', cols, rows)

    def languages(self) -> Table:
        cols = [ECONOMY, QUARTER, I('rank', 'Place by developers pushing'), S('language', 'Language, as GitHub Linguist names it'),
                S('language_type', 'programming, markup, data or prose'), I('pushers', 'Developers who pushed in the language'),
                I('rank_year_earlier', 'Place in the same quarter a year earlier'),
                I('pushers_year_earlier', 'Developers who pushed in it a year earlier'),
                N('change', 'pushers / pushers_year_earlier − 1')]
        rows = []
        for code in PEERS:
            before = ({lang: (rank, n) for rank, (lang, _, n) in enumerate(self.ix.languages(code, self.year_before), 1)}
                      if self.year_before else {})
            for rank, (lang, kind, n) in enumerate(self.ix.languages(code, self.q), 1):
                prev_rank, prev = before.get(lang, (None, None))
                rows.append([code, qkey(self.q), rank, lang, kind, n, prev_rank, prev, n / prev - 1 if prev else None])
        return Table('languages', 'Languages',
                     'Developers who pushed in each language in the latest quarter and a year earlier. One developer can push in '
                     'several languages, so the counts can’t be added up. GitHub lists a language once 100 or more developers '
                     'push in it.', cols, rows)

    def languages_algeria(self) -> Table:
        cols = [QUARTER, I('rank', 'Place by developers pushing'), S('language', 'Language, as GitHub Linguist names it'),
                S('language_type', 'programming, markup, data or prose'), I('pushers', 'Developers who pushed in the language')]
        rows = [[qkey(q), rank, lang, kind, n] for q in self.ds.quarters
                for rank, (lang, kind, n) in enumerate(self.ix.languages(HOME, q), 1)]
        return Table('languages_algeria', 'Languages in Algeria since 2020',
                     'Developers in Algeria who pushed in each language, every quarter since 2020 Q1.', cols, rows)

    def topics(self) -> Table:
        cols = [ECONOMY, QUARTER, I('rank', 'Place by developers pushing'), S('topic', 'Repository topic'),
                I('pushers', 'Developers who pushed to repositories with the topic')]
        rows = [[code, qkey(self.q), rank, topic, n] for code in PEERS
                for rank, (topic, n) in enumerate(self.ix.topic_list(code, self.q), 1)]
        return Table('topics', 'Topics',
                     'The topics GitHub publishes for each economy in the latest quarter: those with 100 or more developers '
                     'pushing.', cols, rows)

    def collaboration(self) -> Table:
        cols = [QUARTER, I('rank', 'Place by weight'), S('partner', 'ISO code of the partner economy'),
                I('weight', 'Collaboration weight between Algeria and the partner (GitHub economy_collaborators)')]
        rows = [[qkey(q), rank, partner, w] for q in self.ds.quarters
                for rank, (partner, w) in enumerate(self.ix.partners(HOME, q), 1)]
        return Table('collaboration', 'Algeria’s collaboration partners',
                     'The economies Algerian developers collaborate with, by GitHub’s collaboration weight, every quarter.',
                     cols, rows)

    def indicators(self) -> Table:
        cols = [ECONOMY, QUARTER] + [COLUMNS[n] for n in INDICATORS] + [I('population_year', 'Year of the population used')]
        rows = []
        for code in self.ds.economies():
            year, people = self.ix.population.get(code)
            rows += [[code, qkey(q)] + [self.ix.value(n, code, q) for n in INDICATORS] + [year if people else None]
                     for q in self.ds.quarters if (code, q) in self.ix.values['accounts']]
        return Table('indicators', 'Every economy, every quarter',
                     'Every indicator for every economy in the release, every quarter since 2020 Q1. Empty where an input is '
                     'missing, never zero.', cols, rows)

    def revisions(self) -> Table:
        cols = [S('series', 'Innovation Graph file'), ECONOMY, QUARTER, I('before', 'Value in the earlier release'),
                I('now', 'Value in this release')]
        found = self.revision_report.revisions if self.revision_report else []
        rows = [[r.series, r.code, r.quarter, r.old, r.new] for r in found]
        return Table('revisions', 'Revised past values',
                     'Past values this release changed, against the release archived before it (named in manifest.json). An '
                     'empty before or now means the value was added or removed.', cols, rows)

    def tables(self) -> list:
        return [self.overview(), self.peers(), self.groups(), self.ranks(), self.trends(), self.languages(),
                self.languages_algeria(), self.topics(), self.collaboration(), self.indicators(), self.revisions()]


def folder_name(quarter: str) -> str:
    """'2026-Q1' -> '2026-q1'."""
    return quarter.lower()


README = """# Algeria Developer Index, {quarter} data

Computed by [djazair.dev](https://djazair.dev) from GitHub Innovation Graph release
[`{short}`]({source}) ({date}).

- **Licence:** [CC0 1.0]({licence_url}), no rights reserved.
- **Attribution:** {attribution}. Population: World Bank (CC BY 4.0), each economy’s latest year.
- **Format:** every table as CSV (UTF-8, one header row) and as JSON (the same rows, plus the licence, the source
  release and a description of every column). Numbers are rounded to six decimal places. An empty CSV cell or a JSON
  `null` means the value is missing, never zero.
- **Checksums:** `manifest.json` lists every file with its size and SHA-256.

| Files | What they hold |
|---|---|
{rows}

Every column is described in [data/README.md](https://github.com/djazairdev/djazair.dev/blob/main/data/README.md).
"""


def render(archive: Archive, ix: Index, revisions: Optional[RevisionReport] = None) -> tuple:
    """(tables, {file name: bytes}) for every file of the folder except manifest.json."""
    meta = {'quarter': archive.quarter, 'release': archive.commit, 'release_date': archive.meta['date'],
            'source': f'{SOURCE_URL}/tree/{archive.commit}/data', 'licence': LICENCE, 'licence_url': LICENCE_URL,
            'attribution': ATTRIBUTION, 'format_version': FORMAT_VERSION}
    tables = Publisher(ix, revisions).tables()
    files = {}
    for table in tables:
        files[f'{table.name}.csv'] = table.csv()
        files[f'{table.name}.json'] = table.json(meta)
    rows = '\n'.join(f'| [`{t.name}.csv`]({t.name}.csv), [`{t.name}.json`]({t.name}.json) | {t.description} |' for t in tables)
    files['README.md'] = README.format(quarter=archive.quarter.replace('-', ' '), short=archive.commit[:12],
                                       source=meta['source'], date=archive.meta['date'][:10], licence_url=LICENCE_URL,
                                       attribution=ATTRIBUTION, rows=rows).encode('utf-8')
    return tables, files


def manifest(archive: Archive, ix: Index, tables: list, files: dict, revisions: Optional[RevisionReport]) -> dict:
    by_name = {t.name: t for t in tables}
    entries = {}
    for name, data in sorted(files.items()):
        entry = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        table = by_name.get(name.rsplit('.', 1)[0])
        if table:
            entry.update(table=table.name, title=table.title, rows=len(table.rows))
        entries[name] = entry
    totals = ix.population.data['series']['SP.POP.TOTL']
    return {'quarter': archive.quarter, 'quarters': [qkey(q) for q in ix.ds.quarters], 'release': archive.commit,
            'release_date': archive.meta['date'], 'source': f'{SOURCE_URL}/tree/{archive.commit}/data',
            'licence': LICENCE, 'licence_url': LICENCE_URL, 'attribution': ATTRIBUTION, 'format_version': FORMAT_VERSION,
            'population': {'source': 'World Bank, World Development Indicators (SP.POP.TOTL)', 'licence': 'CC BY 4.0',
                           'updated': totals.get('updated', ''), 'algeria_year': ix.population_year.get(HOME),
                           'years': sorted(set(ix.population_year.values()))},
            'revisions': {'compared_with': revisions.old if revisions else None,
                          'compared_quarter': revisions.old_quarter if revisions else None,
                          'changed': len(revisions.revisions) if revisions else 0},
            'files': entries}


def publish(archive: Archive, out_dir: Path = DERIVED_DIR, population: Optional[Population] = None,
            previous: Optional[Archive] = None, now: Optional[datetime] = None) -> Path:
    """Write the derived files for ``archive`` and return their folder. ``previous`` is the
    release archived before it: the revisions table lists what ``archive`` changed."""
    ix = Index(Dataset.load(archive), population or Population())
    report = compare(previous, archive) if previous and previous.commit != archive.commit else None
    tables, files = render(archive, ix, report)
    body = manifest(archive, ix, tables, files, report)

    out_dir = Path(out_dir)
    folder = out_dir / folder_name(archive.quarter)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'manifest.json'
    before = json.loads(path.read_text('utf-8')) if path.exists() else {}
    unchanged = {k: v for k, v in before.items() if k != 'generated_at'} == body
    stamp = before['generated_at'] if unchanged else (now or datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')
    files['manifest.json'] = _json({**body, 'generated_at': stamp})

    for old in folder.iterdir():                                   # e.g. a table a newer format dropped
        if old.is_file() and old.name not in files:
            old.unlink()
    for name, data in files.items():
        _write(folder / name, data)

    latest = out_dir / 'latest.json'
    current = json.loads(latest.read_text('utf-8')) if latest.exists() else None
    if current is None or current['quarter'] <= archive.quarter:
        _write(latest, _json({'quarter': archive.quarter, 'folder': folder.name, 'release': archive.commit,
                              'licence': LICENCE, 'licence_url': LICENCE_URL, 'attribution': ATTRIBUTION}))
    return folder


def _json(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode('utf-8')


def _write(path: Path, data: bytes) -> None:
    """Write only when the content changes, so unchanged files keep their timestamps."""
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)
