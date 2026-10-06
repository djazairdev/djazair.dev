"""Arabic review kit (ticket #33): every interface string side by side, for a reviewer who
works in a spreadsheet rather than in JSON.

    python3 site/tools/strings.py export arabic-review.csv   # key, English, Arabic, a column for corrections
    python3 site/tools/strings.py import arabic-review.csv   # applies the corrections to site/i18n/ar.json

The CSV is UTF-8 with a byte-order mark, so spreadsheet apps show the Arabic correctly. Lists
(the "does / doesn't" notes on the Overview) get one row per item: ``ind.accounts.does[0]``.
Import only changes strings whose *Corrected Arabic* cell isn't empty, refuses a correction
that drops or adds a ``{placeholder}``, and never sets ``_meta.reviewed``: that is the sign-off,
made by hand once every page is checked (docs/arabic-review.md).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

I18N = Path(__file__).resolve().parent.parent / 'i18n'
HEADER = ['Key', 'English', 'Arabic now', 'Corrected Arabic', 'Notes']
PLACEHOLDER = re.compile(r'\{(\w+)\}')
ITEM = re.compile(r'^(.*)\[(\d+)\]$')


def rows(en: dict, ar: dict, prefix: str = ''):
    """(key, English, Arabic) for every string, in en.json's order."""
    for key, value in en.items():
        if key.startswith('_'):
            continue
        name, other = prefix + key, ar.get(key) if isinstance(ar, dict) else None
        if isinstance(value, dict):
            yield from rows(value, other if isinstance(other, dict) else {}, name + '.')
        elif isinstance(value, list):
            for i, item in enumerate(value):
                yield f'{name}[{i}]', item, (other[i] if isinstance(other, list) and i < len(other) else '')
        else:
            yield name, value, other if isinstance(other, str) else ''


def export(path: Path, i18n: Path = I18N) -> int:
    en = json.loads((i18n / 'en.json').read_text('utf-8'))
    ar = json.loads((i18n / 'ar.json').read_text('utf-8'))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        out = csv.writer(f)
        out.writerow(HEADER)
        n = 0
        for key, english, arabic in rows(en, ar):
            out.writerow([key, english, arabic, '', ''])
            n += 1
    return n


def _lookup(tree: dict, key: str):
    """(container, index) where ``key`` lives in a nested catalog."""
    m = ITEM.match(key)
    path, index = (m.group(1), int(m.group(2))) if m else (key, None)
    *parents, last = path.split('.')
    node = tree
    for part in parents:
        node = node.setdefault(part, {})
    if index is None:
        return node, last
    return node.setdefault(last, []), index


def apply(path: Path, i18n: Path = I18N) -> list:
    """Write the non-empty corrections into ar.json; returns the keys changed."""
    en = json.loads((i18n / 'en.json').read_text('utf-8'))
    ar = json.loads((i18n / 'ar.json').read_text('utf-8'))
    english = {key: text for key, text, _ in rows(en, ar)}
    changed, problems = [], []
    with path.open(encoding='utf-8-sig', newline='') as f:
        for n, row in enumerate(csv.DictReader(f), 2):
            key, fix = (row.get('Key') or '').strip(), (row.get('Corrected Arabic') or '').strip()
            if not fix:
                continue
            if key not in english:
                problems.append(f'line {n}: {key!r} is not a string in en.json')
                continue
            if set(PLACEHOLDER.findall(fix)) != set(PLACEHOLDER.findall(english[key])):
                problems.append(f'line {n}: {key} must keep the placeholders {sorted(set(PLACEHOLDER.findall(english[key])))}')
                continue
            node, slot = _lookup(ar, key)
            if isinstance(node, list):
                node.extend([''] * (slot + 1 - len(node)))
            if node[slot] != fix:
                node[slot] = fix
                changed.append(key)
    if problems:
        raise SystemExit('Nothing was changed:\n  ' + '\n  '.join(problems))
    (i18n / 'ar.json').write_text(json.dumps(ar, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('action', choices=('export', 'import'))
    parser.add_argument('csv', type=Path)
    args = parser.parse_args(argv)
    if args.action == 'export':
        print(f'{export(args.csv)} strings written to {args.csv}')
    else:
        changed = apply(args.csv)
        print(f'{len(changed)} strings changed in {I18N / "ar.json"}' + (f': {", ".join(changed[:10])}…' if len(changed) > 10 else
                                                                          f': {", ".join(changed)}' if changed else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
