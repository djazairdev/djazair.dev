"""World Bank population, for accounts per million people (PRD §9.1, §9.2).

Fetched from the World Bank API and kept, every year since 2015, in ``data/population.json``
so the pipeline doesn't need the network. Indicators use each economy's latest year with a
value (PRD §9.2), and the published data records that year. Refresh with
``python3 -m pipeline population``; the World Bank updates these series once a year.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .config import REPO_DIR
from .release import Fetch, fetch

PATH = REPO_DIR / 'data' / 'population.json'
SERIES = {'SP.POP.TOTL': 'Population, total', 'SP.POP.1564.TO': 'Population ages 15-64, total'}
API = 'https://api.worldbank.org/v2/country/all/indicator/{series}?format=json&per_page=20000&date={start}:{end}'
LICENCE = 'CC BY 4.0'
SOURCE = 'World Bank, World Development Indicators'
FIRST_YEAR = 2015


def download(get: Fetch = fetch, today: date = None) -> dict:
    """Both series for every economy with a two-letter code, every year with a value."""
    today = today or date.today()
    out = {'source': SOURCE, 'licence': LICENCE, 'retrieved': today.isoformat(), 'series': {}}
    for series, title in SERIES.items():
        meta, rows = json.loads(get(API.format(series=series, start=FIRST_YEAR, end=today.year)))
        values = {}
        for row in rows or []:
            code, value = row['country']['id'], row['value']
            if value is None or len(code) != 2 or not code.isalpha():
                continue
            values.setdefault(code, {})[row['date']] = int(value)
        out['series'][series] = {'title': title, 'updated': meta.get('lastupdated', ''),
                                 'values': {c: dict(sorted(v.items())) for c, v in sorted(values.items())}}
    return out


def save(data: dict, path: Path = PATH) -> None:
    path.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + '\n', 'utf-8')


class Population:
    """The cached series. ``year`` caps the year used (None: each economy's latest)."""

    def __init__(self, path: Path = PATH, year: int = None):
        self.data = json.loads(Path(path).read_text('utf-8'))
        self.cap = year

    def get(self, code: str, series: str = 'SP.POP.TOTL') -> tuple:
        """(year, value) for ``code``, or (None, None) without data."""
        years = self.data['series'][series]['values'].get(code, {})
        usable = [y for y in years if self.cap is None or int(y) <= self.cap]
        if not usable:
            return None, None
        year = max(usable, key=int)
        return int(year), years[year]
