"""Command line: ``python3 -m pipeline <command>``.

    fetch       archive the latest Innovation Graph release if it is new
    validate    check an archived release (the latest by default)
    publish     validate a release, then write data/derived/<yyyy-qN>/ from it
    population  refresh the World Bank population cache (data/population.json)
    revisions   list past values a release changed, against the release before it
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import population, publish, release, revisions
from .config import RAW_DIR
from .run import ValidationFailed, process


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


def pick(commit: str) -> release.Archive:
    """An archived release by commit (a prefix is enough), or the latest one."""
    found = release.archives(RAW_DIR)
    if not found:
        raise SystemExit('No archived release yet: run `python3 -m pipeline fetch` first.')
    if commit == 'latest':
        return found[-1]
    matches = [a for a in found if a.commit.startswith(commit)]
    if len(matches) != 1:
        raise SystemExit(f'No single archived release matches {commit!r}.')
    return matches[0]


def earlier(archive: release.Archive):
    """The release archived before ``archive``, or None."""
    found = [a for a in release.archives(RAW_DIR) if a.meta['date'] < archive.meta['date']]
    return found[-1] if found else None


def cmd_validate(args) -> int:
    archive = pick(args.release)
    try:
        report = process(archive, report_path=args.report)
    except ValidationFailed as failed:
        print(failed.report.markdown())
        return 1
    print(report.markdown())
    return 0


def cmd_publish(args) -> int:
    archive = pick(args.release)
    written = []
    step = lambda a: written.append(publish.publish(a, previous=earlier(a)))
    try:
        report = process(archive, steps=[step], report_path=args.report)
    except ValidationFailed as failed:
        print(failed.report.markdown())
        print('Nothing was published.')
        return 1
    folder = written[0]
    manifest = json.loads((folder / 'manifest.json').read_text('utf-8'))
    tables = sorted({f['table'] for f in manifest['files'].values() if 'table' in f})
    print(f'{report.quarter} data from {archive.commit[:12]}: {len(tables)} tables written to '
          f'{folder.relative_to(RAW_DIR.parent.parent)} (generated {manifest["generated_at"]})')
    if report.warnings:
        print(f'{len(report.warnings)} validation warnings; see `python3 -m pipeline validate`.')
    _output(quarter=report.quarter, folder=str(folder.relative_to(RAW_DIR.parent.parent)))
    return 0


def cmd_population(args) -> int:
    data = population.download()
    population.save(data)
    totals = data['series']['SP.POP.TOTL']
    print(f'World Bank population for {len(totals["values"])} economies (updated {totals["updated"]}) '
          f'saved to {population.PATH.relative_to(population.PATH.parent.parent)}')
    return 0


def cmd_revisions(args) -> int:
    archive = pick(args.release)
    before = earlier(archive)
    if before is None:
        print(f'{archive.commit[:12]} is the first archived release: nothing to compare.')
        _output(revisions='false')
        return 0
    report = revisions.compare(before, archive)
    body = report.markdown()
    print(body)
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(body)
    _output(revisions='true' if report.found else 'false')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python3 -m pipeline', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('fetch', help='archive the latest Innovation Graph release if it is new').set_defaults(run=cmd_fetch)
    v = sub.add_parser('validate', help='check an archived release')
    v.add_argument('--release', default='latest', help='commit of an archived release (default: the latest)')
    v.add_argument('--report', type=str, help='also write the report, as Markdown, to this file')
    v.set_defaults(run=cmd_validate)
    p = sub.add_parser('publish', help='validate a release, then write data/derived/<yyyy-qN>/ from it')
    p.add_argument('--release', default='latest', help='commit of an archived release (default: the latest)')
    p.add_argument('--report', type=str, help='also write the validation report, as Markdown, to this file')
    p.set_defaults(run=cmd_publish)
    sub.add_parser('population', help='refresh the World Bank population cache').set_defaults(run=cmd_population)
    r = sub.add_parser('revisions', help='list past values a release changed')
    r.add_argument('--release', default='latest', help='commit of an archived release (default: the latest)')
    r.add_argument('--report', type=str, help='also write the report, as Markdown, to this file')
    r.set_defaults(run=cmd_revisions)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == '__main__':
    sys.exit(main())
