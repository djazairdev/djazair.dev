"""Quarterly reports (ticket #34; PRD §13, IDX-17).

Each report lives in ``content/reports/<yyyy-qN>/``:

- ``report.json``: the data quarter and the release it was written from, its number, whether
  it is still a draft, the Hub numbers it quotes (fixed when it is published) and ``checks``,
  the claims its words make, tested against that quarter's data (``editorial.verify``);
- ``en.md`` and ``ar.md``: the text. A title and a standfirst at the top, between ``---``
  lines; then ``##`` sections in the order of PRD §13, with ``{{name}}`` figures computed from
  the quarter's data and ``:::`` blocks for the figures, tables and the press kit.

A report reads its own quarter's folder in ``data/derived/``, not the latest one, so its
numbers stay as published when newer data arrives. ``docs/reports.md`` explains how to write
and publish one.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import CONTENT_DIR
from .fmt import parse_quarter

REPORTS_DIR = CONTENT_DIR / 'reports'
STATUSES = ('draft', 'published')
FRONT = re.compile(r'\A---\n(.*?)\n---\n', re.S)


@dataclass(frozen=True)
class Report:
    slug: str                      # '2026-q1': the folder, and the page's address
    quarter: str                   # '2026-Q1'
    number: int                    # 1 for the first report
    release: str                   # Innovation Graph commit the text was written from
    status: str = 'draft'          # draft | published
    published: Optional[str] = None   # 'YYYY-MM-DD' once published
    hub: dict = field(default_factory=dict)   # {'projects', 'issues', 'date'}: the Hub when it was written
    checks: tuple = ()
    folder: Path = REPORTS_DIR

    @property
    def key(self) -> str:          # route key
        return f'report-{self.slug}'

    @property
    def path(self) -> str:         # under /<lang>/
        return f'reports/{self.slug}/'

    @property
    def draft(self) -> bool:
        return self.status != 'published'

    def source(self, lang: str) -> tuple:
        """(front matter, body) of ``<lang>.md``."""
        return front_matter((self.folder / f'{lang}.md').read_text('utf-8'))

    def doc(self) -> dict:
        """The claims, in the shape ``editorial.verify`` reads."""
        return {'quarter': self.quarter, 'checks': list(self.checks)}


def front_matter(text: str) -> tuple:
    """``---`` / ``key: value`` lines / ``---`` at the top of a file, and the text after it."""
    m = FRONT.match(text)
    if not m:
        raise ValueError('a report starts with a front matter block: ---, title: …, standfirst: …, ---')
    meta = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(':')
        if not sep or not key.strip():
            raise ValueError(f'front matter line not understood: {line!r}')
        meta[key.strip()] = value.strip()
    missing = {'title', 'standfirst'} - set(meta)
    if missing:
        raise ValueError(f'front matter is missing {", ".join(sorted(missing))}')
    return meta, text[m.end():]


def load(folder: Path) -> Report:
    doc = json.loads((folder / 'report.json').read_text('utf-8'))
    year, n = parse_quarter(doc['quarter'])
    if folder.name != f'{year}-q{n}':
        raise ValueError(f'{folder.name}/report.json is for {doc["quarter"]}: the folder must be named {year}-q{n}')
    if doc.get('status', 'draft') not in STATUSES:
        raise ValueError(f'{folder.name}/report.json: status must be one of {", ".join(STATUSES)}')
    if doc.get('status') == 'published' and not doc.get('published'):
        raise ValueError(f'{folder.name}/report.json: a published report needs its "published" date')
    return Report(slug=folder.name, quarter=f'{year}-Q{n}', number=int(doc['number']), release=doc['release'],
                  status=doc.get('status', 'draft'), published=doc.get('published'), hub=dict(doc.get('hub') or {}),
                  checks=tuple(doc.get('checks', ())), folder=folder)


def all_reports(root: Optional[Path] = None) -> list:
    """Every report, newest first."""
    root = Path(root or REPORTS_DIR)
    if not root.is_dir():
        return []
    found = [load(p) for p in root.iterdir() if (p / 'report.json').is_file()]
    return sorted(found, key=lambda r: r.quarter, reverse=True)
