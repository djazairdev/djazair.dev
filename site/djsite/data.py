"""The Index data the site is built from (ticket #13).

The site reads only ``data/derived/``: ``latest.json`` names the quarter to build, and every
table comes from that quarter's JSON files, each checked against ``manifest.json`` first.
``python3 -m pipeline publish`` writes them.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import DATA_DIR

DERIVED_DIR = DATA_DIR / 'derived'
HUB_DIR = DERIVED_DIR / 'hub'


class DataError(Exception):
    """The derived data is missing or doesn't match its manifest."""


class Derived:
    """One quarter of derived data."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        path = self.folder / 'manifest.json'
        if not path.is_file():
            raise DataError(f'{path} is missing: run `python3 -m pipeline publish`')
        self.manifest = json.loads(path.read_text('utf-8'))
        self._tables: dict = {}
        self._trends: Optional[dict] = None
        self._series: set = set()

    @property
    def quarter(self) -> str:                  # '2026-Q1'
        return self.manifest['quarter']

    @property
    def quarters(self) -> list:                # '2020-Q1' … quarter
        return self.manifest['quarters']

    @property
    def release(self) -> str:
        return self.manifest['release']

    @property
    def release_date(self) -> str:             # '2026-07-07'
        return self.manifest['release_date'][:10]

    @property
    def files(self) -> dict:                   # file name -> {bytes, sha256, table, title, rows}
        return self.manifest['files']

    @property
    def zip_name(self) -> str:
        """Every CSV table of the quarter in one file, which the build writes next to them."""
        return f'djazair.dev-index-{self.folder.name}-csv.zip'

    def read(self, name: str) -> bytes:
        """A file of the folder, after checking it against the manifest."""
        entry = self.files.get(name)
        if entry is None:
            raise DataError(f'{name} is not listed in {self.folder.name}/manifest.json')
        data = (self.folder / name).read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise DataError(f'{self.folder.name}/{name} does not match manifest.json: publish the data again')
        return data

    def table(self, name: str) -> dict:
        if name not in self._tables:
            self._tables[name] = json.loads(self.read(f'{name}.json'))
        return self._tables[name]

    def rows(self, name: str) -> list:
        return self.table(name)['rows']

    # ---- shortcuts the pages use
    def overview(self) -> dict:
        """Algeria's overview row for each indicator: {indicator: row}."""
        return {r['indicator']: r for r in self.rows('overview')}

    def peers(self) -> dict:
        return {r['economy']: r for r in self.rows('peers')}

    def series(self, indicator: str, series: str) -> list:
        """One value per quarter, oldest first (None where missing). ``series`` is an ISO code
        or ``median_<group>``."""
        if self._trends is None:
            self._trends = {(r['quarter'], r['indicator'], r['series']): r['value'] for r in self.rows('trends')}
            self._series = {k[1:] for k in self._trends}
        if (indicator, series) not in self._series:
            raise DataError(f'the trends table has no {indicator} series for {series}')
        return [self._trends.get((q, indicator, series)) for q in self.quarters]


def load(root: Path = DERIVED_DIR) -> Derived:
    """The quarter ``latest.json`` points at."""
    pointer = Path(root) / 'latest.json'
    if not pointer.is_file():
        raise DataError(f'{pointer} is missing: run `python3 -m pipeline publish`')
    return Derived(Path(root) / json.loads(pointer.read_text('utf-8'))['folder'])


def _time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def hub_issues(root: Path = HUB_DIR) -> list:
    """Beginner issues from the Hub's listed projects, newest first, each with ``days``: its age
    when the Hub was last synced (so a build gives the same page for the same data). Empty
    until the first sync writes ``hub/issues.json`` (ticket #25)."""
    path = Path(root) / 'issues.json'
    if not path.is_file():
        return []
    doc = json.loads(path.read_text('utf-8'))
    synced = _time(doc['generated_at'])
    out = [dict(issue, days=max(0, (synced - _time(issue['created_at'])).days)) for issue in doc['issues']]
    return sorted(out, key=lambda i: i['created_at'], reverse=True)
