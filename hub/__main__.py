"""Command line: ``python3 -m hub <command>``.

    check-registry     validate projects.yml (or another file) against hub/projects.schema.json
    check-submission   run the inclusion checks on the entries a pull request adds or changes
    check-issue        run the inclusion checks on a listing request made with the issue form
    check-project      run the inclusion checks on one repository
    sync               fetch the listed projects and their beginner issues into data/derived/hub/
    metrics            count new contributors and response times, counts only (data/derived/hub/metrics.json)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import checks, metrics, registry, submission, sync
from .github import GitHub, GitHubError


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


def _deliver(outcome: submission.Outcome, args) -> None:
    """Print the comment, write it to --comment, and post it to --post-to (an issue or pull request)."""
    print(outcome.body)
    if args.comment:
        Path(args.comment).write_text(outcome.body, 'utf-8')
    if args.post_to:
        repo = os.environ.get('GITHUB_REPOSITORY', 'djazairdev/djazair.dev')
        action = GitHub().upsert_comment(repo, int(args.post_to), submission.MARKER, outcome.body)
        print(f'Comment {action} on #{args.post_to}.')


def cmd_check_submission(args) -> int:
    proposed = Path(args.proposed).read_text('utf-8')
    base = Path(args.base).read_text('utf-8') if args.base and Path(args.base).exists() else None
    outcome = submission.check_pull_request(proposed, base, GitHub())
    _deliver(outcome, args)
    return 0 if outcome.ok else 1


def cmd_check_issue(args) -> int:
    body = Path(args.body_file).read_text('utf-8') if args.body_file else os.environ.get('ISSUE_BODY', '')
    outcome = submission.check_issue(body, GitHub())
    _deliver(outcome, args)
    return 0 if outcome.ok or not args.strict else 1


def cmd_check_project(args) -> int:
    entry = {'category': args.category, 'tags': args.tags.split(',') if args.tags else [], 'maintainer_pledge': args.pledge}
    report = checks.run(args.repository, entry, GitHub(), reviewed=args.reviewed)
    print(submission.report_markdown(report))
    return 0 if report.ok else 1


def cmd_sync(args) -> int:
    try:
        print(sync.run(Path(args.registry), Path(args.out)))
    except (GitHubError, ValueError) as err:
        print(f'Hub sync stopped, nothing was written: {err}', file=sys.stderr)
        return 1
    return 0


def cmd_metrics(args) -> int:
    try:
        print(metrics.run(Path(args.out), daily=args.daily))
    except (GitHubError, ValueError) as err:
        print(f'Hub metrics stopped, nothing was written: {err}', file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python3 -m hub', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('check-registry', help='validate projects.yml against hub/projects.schema.json')
    c.add_argument('path', nargs='?', default=str(registry.REGISTRY), help='the file to check (default: projects.yml)')
    c.set_defaults(run=cmd_check_registry)

    def outputs(p):
        p.add_argument('--comment', help='also write the comment, as Markdown, to this file')
        p.add_argument('--post-to', help='post the comment on this issue or pull request number ($GITHUB_REPOSITORY)')

    s = sub.add_parser('check-submission', help='check the entries a pull request adds or changes in projects.yml')
    s.add_argument('--proposed', required=True, help='the projects.yml the pull request proposes')
    s.add_argument('--base', default=str(registry.REGISTRY), help='the current projects.yml (default: this checkout)')
    outputs(s)
    s.set_defaults(run=cmd_check_submission)
    i = sub.add_parser('check-issue', help='check a listing request made with the issue form')
    i.add_argument('--body-file', help='the issue body (default: $ISSUE_BODY)')
    i.add_argument('--strict', action='store_true', help='exit 1 when a check fails')
    outputs(i)
    i.set_defaults(run=cmd_check_issue)
    p = sub.add_parser('check-project', help='run the inclusion checks on one repository')
    p.add_argument('repository', help='owner/name')
    p.add_argument('--category', default='tool')
    p.add_argument('--tags', default='', help='comma-separated')
    p.add_argument('--pledge', action='store_true', help='the maintainers made the pledge')
    p.add_argument('--reviewed', action='store_true', help='a person has confirmed relevance')
    p.set_defaults(run=cmd_check_project)
    y = sub.add_parser('sync', help='fetch the listed projects and their beginner issues from GitHub')
    y.add_argument('--registry', default=str(registry.REGISTRY), help='the registry (default: projects.yml)')
    y.add_argument('--out', default=str(sync.OUT), help='where to write the snapshot (default: data/derived/hub)')
    y.set_defaults(run=cmd_sync)
    m = sub.add_parser('metrics', help='count new contributors and response times, counts only (PRD HUB-10)')
    m.add_argument('--out', default=str(sync.OUT), help='the snapshot to read and write (default: data/derived/hub)')
    m.add_argument('--daily', action='store_true', help='do nothing if the counts were already made today')
    m.set_defaults(run=cmd_metrics)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == '__main__':
    sys.exit(main())
