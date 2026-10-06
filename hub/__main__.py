"""Command line: ``python3 -m hub <command>``.

    check-registry   validate projects.yml (or another file) against hub/projects.schema.json
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import registry


def cmd_check_registry(args) -> int:
    path = Path(args.path)
    result = registry.load(path)
    try:
        shown = str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        shown = str(path)
    if result.ok:
        n = len(result.projects)
        print(f'{shown}: {n} project{"s" if n != 1 else ""}, valid.')
        return 0
    annotate = os.environ.get('GITHUB_ACTIONS') == 'true'
    for p in result.problems:
        print(f'{shown}:{p.line or 1}: {p}')
        if annotate:
            message = str(p).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print(f'::error file={shown},line={p.line or 1},title=projects.yml::{message}')
    print(f'{len(result.problems)} problem{"s" if len(result.problems) != 1 else ""} in {shown}. '
          'See CONTRIBUTING.md for the format.')
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python3 -m hub', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('check-registry', help='validate projects.yml against hub/projects.schema.json')
    c.add_argument('path', nargs='?', default=str(registry.REGISTRY), help='the file to check (default: projects.yml)')
    c.set_defaults(run=cmd_check_registry)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == '__main__':
    sys.exit(main())
