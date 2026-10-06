"""The seven inclusion checks (ticket #16; PRD §8 inclusion criteria, HUB-03).

Six run against GitHub; the seventh, Algerian maintainers or clear relevance to Algeria, is
checked by a person, so a submission shows it as waiting for a reviewer. Every failure says
what was found and how to fix it. The health checks (#26, ``health.py``) use the same 90 days
and topic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from .github import GitHub, GitHubError

TOPIC = 'djazairdev'
ACTIVE_DAYS = 90
MIN_ISSUES = 3
BEGINNER_LABELS = ('good first issue', 'help wanted')

CHECKS = (
    ('licence', 'An OSI-approved open-source licence'),
    ('activity', 'At least one commit in the last 90 days'),
    ('docs', 'A README and a CONTRIBUTING file'),
    ('issues', 'At least 3 open issues labelled good first issue or help wanted'),
    ('pledge', 'Maintainers pledge to reply to newcomer pull requests within 7 days'),
    ('topic', 'The repository carries the GitHub topic djazairdev'),
    ('relevance', 'Algerian maintainers, or clear relevance to Algeria'),
)

# SPDX identifiers of OSI-approved licences, as GitHub reports them (opensource.org/licenses).
OSI = frozenset('''
0BSD AFL-3.0 AGPL-3.0 AGPL-3.0-only AGPL-3.0-or-later Apache-2.0 APSL-2.0 Artistic-2.0 BSD-1-Clause BSD-2-Clause
BSD-2-Clause-Patent BSD-3-Clause BSL-1.0 CAL-1.0 CDDL-1.0 CECILL-2.1 CERN-OHL-P-2.0 CERN-OHL-S-2.0 CERN-OHL-W-2.0
ECL-2.0 EFL-2.0 EPL-1.0 EPL-2.0 EUPL-1.1 EUPL-1.2 GPL-2.0 GPL-2.0-only GPL-2.0-or-later GPL-3.0 GPL-3.0-only
GPL-3.0-or-later ISC LGPL-2.1 LGPL-2.1-only LGPL-2.1-or-later LGPL-3.0 LGPL-3.0-only LGPL-3.0-or-later LPPL-1.3c MIT
MIT-0 MPL-2.0 MS-PL MS-RL MulanPSL-2.0 NCSA OFL-1.1 OSL-3.0 PostgreSQL Python-2.0 UPL-1.0 Unlicense Zlib
'''.split())
# Datasets may also use an open data licence (Open Definition conformant).
OPEN_DATA = frozenset('CC0-1.0 CC-BY-4.0 CC-BY-SA-4.0 ODbL-1.0 ODC-By-1.0 PDDL-1.0'.split())


@dataclass
class Result:
    key: str
    status: str              # pass, fail, review (a person checks it) or error (GitHub didn't answer)
    found: str               # what the check found
    fix: str = ''            # how to fix a failure

    @property
    def title(self) -> str:
        return dict(CHECKS)[self.key]


@dataclass
class Report:
    repository: str
    results: list = field(default_factory=list)
    notes: list = field(default_factory=list)     # recommendations; never block a listing

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def ok(self) -> bool:
        """Nothing failed and nothing is unknown (a review may still be pending)."""
        return not any(r.status in ('fail', 'error') for r in self.results)

    def summary(self) -> str:
        parts = [f'{self.count("pass")} of {len(CHECKS)} passed']
        if self.count('fail'):
            parts.append(f'{self.count("fail")} to fix')
        if self.count('error'):
            parts.append(f'{self.count("error")} could not run')
        if self.count('review'):
            parts.append(f'{self.count("review")} waits for a reviewer')
        return ', '.join(parts)


def _days(stamp: str, today: date) -> int:
    when = datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone(timezone.utc).date()
    return (today - when).days


def run(repo: str, entry: dict, github: GitHub, today: Optional[date] = None, reviewed: bool = False) -> Report:
    """Check ``repo`` (owner/name) for the registry ``entry`` (category, tags, maintainer_pledge).
    ``reviewed``: a person has already confirmed relevance (a listed project)."""
    today = today or datetime.now(timezone.utc).date()
    report = Report(repo)
    add = report.results.append
    try:
        info = github.repository(repo)
    except GitHubError as err:
        report.results = [Result(k, 'error', f'GitHub didn’t answer: {err}.', 'Run the check again later.') for k, _ in CHECKS]
        return report
    if info is None or info.get('private'):
        missing = Result('licence', 'fail', f'`{repo}` isn’t a public repository on GitHub.',
                         'Check the owner/name spelling. Listed repositories must be public.')
        report.results = [missing] + [Result(k, 'fail', 'Not checked: the repository wasn’t found.', 'Fix the repository name first.')
                                      for k, _ in CHECKS[1:6]] + [_relevance(entry, reviewed)]
        return report
    if info.get('full_name') and info['full_name'].lower() != repo.lower():
        report.notes.append(f'GitHub redirects `{repo}` to `{info["full_name"]}`: list the current name.')

    add(_licence(info, entry))
    for key, check in (('activity', _activity), ('docs', _docs), ('issues', _issues)):
        try:
            add(check(repo, info, github, today, report))
        except GitHubError as err:
            add(Result(key, 'error', f'GitHub didn’t answer: {err}.', 'Run the check again later.'))
    add(_pledge(entry))
    add(_topic(info))
    add(_relevance(entry, reviewed))
    return report


def _licence(info: dict, entry: dict) -> Result:
    lic = info.get('license') or {}
    spdx, name = lic.get('spdx_id'), lic.get('name') or ''
    if not lic:
        return Result('licence', 'fail', 'No licence found.',
                      'Add a LICENSE file with an OSI-approved licence, such as MIT or Apache-2.0 (see choosealicense.com).')
    if spdx in (None, 'NOASSERTION'):
        return Result('licence', 'fail', 'GitHub can’t tell which licence the LICENSE file holds.',
                      'Use the unchanged text of an OSI-approved licence, so GitHub can recognise it.')
    if spdx in OSI:
        return Result('licence', 'pass', f'{name} (`{spdx}`), approved by the OSI.')
    if entry.get('category') == 'dataset' and spdx in OPEN_DATA:
        return Result('licence', 'pass', f'{name} (`{spdx}`), an open data licence, accepted for datasets.')
    return Result('licence', 'fail', f'{name} (`{spdx}`) isn’t OSI-approved.',
                  'Use an OSI-approved licence (opensource.org/licenses). If it is approved and we missed it, say so here.')


def _activity(repo: str, info: dict, github: GitHub, today: date, report: Report) -> Result:
    branch = info.get('default_branch') or 'main'
    if info.get('archived'):
        return Result('activity', 'fail', 'The repository is archived.', 'Unarchive it and keep committing to list it.')
    commit = github.last_commit(repo, branch)
    if not commit:
        return Result('activity', 'fail', f'No commits on `{branch}`.', 'Push the project’s code to its default branch.')
    stamp = (commit.get('commit') or {}).get('committer', {}).get('date') or (commit.get('commit') or {}).get('author', {}).get('date')
    days = _days(stamp, today)
    found = f'Last commit on `{branch}` on {stamp[:10]}, {days} day{"s" if days != 1 else ""} ago.'
    if days <= ACTIVE_DAYS:
        return Result('activity', 'pass', found)
    return Result('activity', 'fail', found, f'Listed projects need a commit on the default branch in the last {ACTIVE_DAYS} days.')


def _docs(repo: str, info: dict, github: GitHub, today: date, report: Report) -> Result:
    profile = github.community(repo) or {}
    files = profile.get('files') or {}
    readme, contributing = files.get('readme') is not None, files.get('contributing') is not None
    if files.get('code_of_conduct') is None and files.get('code_of_conduct_file') is None:
        report.notes.append('A code of conduct is recommended, not required: none found.')
    if readme and contributing:
        return Result('docs', 'pass', 'README and CONTRIBUTING found.')
    missing = [name for name, found in (('README', readme), ('CONTRIBUTING', contributing)) if not found]
    fixes = {'README': 'a README saying what the project does and how to run it',
             'CONTRIBUTING': 'a CONTRIBUTING.md (in the root, docs/ or .github/) saying how to set the project up and send a pull request'}
    return Result('docs', 'fail', f'No {" or ".join(missing)} file found.', 'Add ' + ', and '.join(fixes[m] for m in missing) + '.')


def _issues(repo: str, info: dict, github: GitHub, today: date, report: Report) -> Result:
    if info.get('has_issues') is False:
        return Result('issues', 'fail', 'Issues are turned off.', 'Turn on issues, then label at least 3 for newcomers.')
    found = {}
    for label in BEGINNER_LABELS:
        for issue in github.labelled_issues(repo, label):
            found[issue['number']] = issue
    n = len(found)
    text = f'{n} open issue{"s" if n != 1 else ""} labelled `good first issue` or `help wanted`.'
    if n >= MIN_ISSUES:
        return Result('issues', 'pass', text)
    return Result('issues', 'fail', text, f'Label at least {MIN_ISSUES} open issues `good first issue` or `help wanted`, each '
                                          'described well enough for a newcomer to start.')


def _pledge(entry: dict) -> Result:
    if entry.get('maintainer_pledge') is True:
        return Result('pledge', 'pass', 'The maintainers pledge to reply to newcomer pull requests within 7 days.')
    return Result('pledge', 'fail', 'No maintainer pledge.', 'Set `maintainer_pledge: true` (or tick the pledge in the issue form).')


def _topic(info: dict) -> Result:
    if TOPIC in (info.get('topics') or []):
        return Result('topic', 'pass', f'The repository carries the topic `{TOPIC}`.')
    return Result('topic', 'fail', f'The topic `{TOPIC}` is missing.',
                  f'Add `{TOPIC}` under *About → Topics* on the repository page. Only maintainers can, so it shows the request '
                  'is yours.')


def _relevance(entry: dict, reviewed: bool) -> Result:
    tags = ', '.join(f'`{t}`' for t in entry.get('tags') or []) or 'none'
    if reviewed:
        return Result('relevance', 'pass', f'Confirmed when the project was listed. Tags: {tags}.')
    return Result('relevance', 'review', f'A reviewer checks this. Tags: {tags}.')
