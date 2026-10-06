"""Command line: ``python3 -m pipeline <command>``.

    fetch     archive the latest Innovation Graph release if it is new
"""
from __future__ import annotations

import argparse
import os
import sys

from . import release


def _output(**values) -> None:
    """Pass values to later GitHub Actions steps (no-op elsewhere)."""
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            for key, value in values.items():
                f.write(f'{key}={value}\n')


def cmd_fetch(args) -> int:
    latest = release.latest()
    folder, new = release.archive(latest)
    meta = release.verify(folder)
    print(f'{"Archived" if new else "Already archived"}: {meta["quarter"]} data, commit {meta["commit"][:12]} '
          f'({meta["date"][:10]}) in {folder.relative_to(release.RAW_DIR.parent.parent)}')
    _output(new='true' if new else 'false', commit=meta['commit'], quarter=meta['quarter'])
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python3 -m pipeline', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('fetch', help='archive the latest Innovation Graph release if it is new').set_defaults(run=cmd_fetch)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == '__main__':
    sys.exit(main())
