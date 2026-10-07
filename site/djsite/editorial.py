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
        if 'language' in check:
            failures += verify_language(check, data)
            continue
        ind = check['indicator']
        # A claim runs to the file's own quarter unless it says otherwise.
        span = [q for q in quarters if check.get('from', quarters[0]) <= q <= check.get('to', doc['quarter'])]
        if not span:
            failures.append(f'{check.get("claim", check)}: no data for the quarters it covers')
            continue
        claim = check.get('claim', str(check))
        if 'rising' in check or 'falling' in check:
            up = 'rising' in check
            for series in check['rising' if up else 'falling']:
                values = dict(zip(quarters, data.series(ind, series)))
                start, end = values.get(span[0]), values.get(span[-1])
                if start is None or end is None or not (end > start if up else end < start):
                    failures.append(f'{claim}: {series} did not {"rise" if up else "fall"} from {span[0]} to {span[-1]}')
        elif 'grew_at_least' in check:
            values = dict(zip(quarters, data.series(ind, check['series'])))
            start, end = values.get(span[0]), values.get(span[-1])
            if not start or end is None or end / start - 1 < check['grew_at_least']:
                failures.append(f'{claim}: {check["series"]} grew less than {check["grew_at_least"]:.0%} from {span[0]} to {span[-1]}')
        elif 'streak' in check:
            values = [v for q, v in zip(quarters, data.series(ind, check['series'])) if q <= span[-1]]
            n, direction, _ = streak(values)
            if direction != (1 if check['streak'] == 'up' else -1) or n < check.get('min', 2):
                failures.append(f'{claim}: {check["series"]} has not moved {check["streak"]} for {check.get("min", 2)} quarters in a row')
        elif 'at_least' in check or 'below' in check or 'equals' in check:
            mine = dict(zip(quarters, data.series(ind, check['series'])))
            other_key = check.get('at_least') or check.get('below') or check.get('equals')
            other = dict(zip(quarters, data.series(ind, other_key)))
            for q in span:
                a, b = mine.get(q), other.get(q)
                if a is None or b is None:
                    failures.append(f'{claim}: no value in {q}')
                elif 'at_least' in check and round(a, 6) < round(b, 6):
                    failures.append(f'{claim}: {check["series"]} {a:.4f} < {other_key} {b:.4f} in {q}')
                elif 'below' in check and not a < b:
                    failures.append(f'{claim}: {check["series"]} {a:.4f} is not below {other_key} {b:.4f} in {q}')
                elif 'equals' in check and round(a, 6) != round(b, 6):
                    failures.append(f'{claim}: {check["series"]} {a:.4f} is not {other_key} {b:.4f} in {q}')
        elif 'bottom' in check:
            # Algeria's rank in a group in the data's quarter: among the last ``bottom`` places.
            row = data.overview()[ind]
            rank, ranked = row[f'{check["group"]}_rank'], row[f'{check["group"]}_ranked']
            if rank is None or rank <= ranked - check['bottom']:
                failures.append(f'{claim}: Algeria is {rank} of {ranked} in {check["group"]}, not in the last {check["bottom"]}')
        else:
            failures.append(f'{claim}: unknown check {check}')
    return failures


def verify_language(check: dict, data) -> list:
    """A claim about one of Algeria's languages in the data's quarter: ``grew_at_least`` (change
    on a year earlier), ``rank_at_most`` (in the top n), ``rank_over`` (outside it),
    ``entered_top`` and ``left_top`` (in the top n now and not a year earlier, or the reverse) or
    ``always_first`` (first in every quarter since the series starts)."""
    claim, name = check.get('claim', str(check)), check['language']
    row = next((r for r in data.rows('languages') if r['economy'] == 'DZ' and r['quarter'] == data.quarter
                and r['language'] == name), None)
    if row is None:
        return [f'{claim}: {name} is not in Algeria’s languages in {data.quarter}']
    out = []
    if 'grew_at_least' in check and (row['change'] is None or row['change'] < check['grew_at_least']):
        out.append(f'{claim}: {name} grew {row["change"]} on a year earlier, less than {check["grew_at_least"]}')
    if 'rank_at_most' in check and row['rank'] > check['rank_at_most']:
        out.append(f'{claim}: {name} is ranked {row["rank"]}, not in the top {check["rank_at_most"]}')
    if 'rank_over' in check and row['rank'] <= check['rank_over']:
        out.append(f'{claim}: {name} is ranked {row["rank"]}, inside the top {check["rank_over"]}')
    before = row['rank_year_earlier']
    if 'entered_top' in check and not (row['rank'] <= check['entered_top'] and (before is None or before > check['entered_top'])):
        out.append(f'{claim}: {name} went from {before} to {row["rank"]}, so it did not enter the top {check["entered_top"]}')
    if 'left_top' in check and not (row['rank'] > check['left_top'] and before is not None and before <= check['left_top']):
        out.append(f'{claim}: {name} went from {before} to {row["rank"]}, so it did not leave the top {check["left_top"]}')
    if check.get('always_first'):
        first = {r['quarter']: r['language'] for r in data.rows('languages_algeria') if r['rank'] == 1}
        if any(first.get(q) != name for q in data.quarters):
            out.append(f'{claim}: {name} was not first in every quarter')
    known = {'language', 'claim', 'grew_at_least', 'rank_at_most', 'rank_over', 'entered_top', 'left_top', 'always_first'}
    if set(check) - known or not set(check) & (known - {'language', 'claim'}):
        out.append(f'{claim}: unknown check {check}')
    return out
