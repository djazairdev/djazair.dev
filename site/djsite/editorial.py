"""Words tied to a data quarter (ticket #18).

Two kinds:

- **Facts stated as text are computed** from the derived data, so they stay true: how many
  quarters in a row growth has sped up or slowed, and from what to what.
- **Headlines written by a person** for a quarter live in ``content/editorial/<yyyy-qN>.json``,
  in English and Arabic. Each file lists the factual claims its words make under ``checks``,
  and ``verify`` tests them against the data, so a revised release can't leave a false
  headline in place. When the latest quarter has no file yet (the daily job published new
  data before anyone wrote about it), pages fall back to neutral, computed text.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from typing import Optional

from .config import CONTENT_DIR

EDITORIAL_DIR = CONTENT_DIR / 'editorial'


def load(quarter: str) -> Optional[dict]:
    """The editorial file for ``quarter`` ('2026-Q1'), or None."""
    path = EDITORIAL_DIR / f'{quarter.lower()}.json'
    if not path.is_file():
        return None
    doc = json.loads(path.read_text('utf-8'))
    if doc.get('quarter') != quarter:
        raise ValueError(f'{path.name} says it is for {doc.get("quarter")}, not {quarter}')
    return doc


@lru_cache(maxsize=4)
def current(data) -> Optional[dict]:
    """The editorial file for the data's quarter, only if every claim in it still holds: when
    a revised release breaks one, pages use their computed text until someone updates it."""
    doc = load(data.quarter)
    if doc is None:
        return None
    failures = verify(doc, data)
    if failures:
        print(f'  content/editorial/{data.quarter.lower()}.json is not used: ' + '; '.join(failures), file=sys.stderr)
        return None
    return doc


def text(doc: Optional[dict], lang: str, key: str) -> Optional[str]:
    """A headline from the file, or None (then the page uses its computed text)."""
    if not doc:
        return None
    return (doc.get(lang) or {}).get(key) or None


def streak(values: list) -> tuple:
    """(n, direction, start): growth rose (direction 1) or fell (-1) in each of the last n
    quarters, starting from index ``start``. Missing values end the run."""
    n, direction = 0, 0
    i = len(values) - 1
    while i > 0 and values[i] is not None and values[i - 1] is not None and values[i] != values[i - 1]:
        step = 1 if values[i] > values[i - 1] else -1
        if direction and step != direction:
            break
        direction = step
        n += 1
        i -= 1
    return n, direction, len(values) - 1 - n


def count_phrase(ctx, n: int, capital: bool = False, lang: Optional[str] = None) -> str:
    """'four quarters' / 'أربعة أرباع متتالية', in ``lang`` (default: the page's language)."""
    group = 'home.quarters_cap' if capital else 'home.quarters'
    key = f'{group}.{n if 1 <= n <= 10 and (n > 1 or not capital) else "many"}'
    phrase = ctx.s(key) if lang is None else ctx.site.catalog.lookup(lang, key)[0]
    return phrase.replace('{n}', str(n))


def verify(doc: dict, data) -> list:
    """Claims in ``doc['checks']`` that the data doesn't support (empty when all hold)."""
    quarters = data.quarters
    failures = []
    for check in doc.get('checks', []):
        ind = check['indicator']
        # A claim runs to the file's own quarter unless it says otherwise.
        span = [q for q in quarters if check.get('from', quarters[0]) <= q <= check.get('to', doc['quarter'])]
        if not span:
            failures.append(f'{check.get("claim", check)}: no data for the quarters it covers')
            continue
        claim = check.get('claim', str(check))
        if 'rising' in check:
            for series in check['rising']:
                values = dict(zip(quarters, data.series(ind, series)))
                start, end = values.get(span[0]), values.get(span[-1])
                if start is None or end is None or not end > start:
                    failures.append(f'{claim}: {series} did not rise from {span[0]} to {span[-1]}')
        elif 'at_least' in check or 'below' in check:
            mine = dict(zip(quarters, data.series(ind, check['series'])))
            other_key = check.get('at_least') or check.get('below')
            other = dict(zip(quarters, data.series(ind, other_key)))
            for q in span:
                a, b = mine.get(q), other.get(q)
                if a is None or b is None:
                    failures.append(f'{claim}: no value in {q}')
                elif 'at_least' in check and round(a, 6) < round(b, 6):
                    failures.append(f'{claim}: {check["series"]} {a:.4f} < {other_key} {b:.4f} in {q}')
                elif 'below' in check and not a < b:
                    failures.append(f'{claim}: {check["series"]} {a:.4f} is not below {other_key} {b:.4f} in {q}')
        else:
            failures.append(f'{claim}: unknown check {check}')
    return failures
