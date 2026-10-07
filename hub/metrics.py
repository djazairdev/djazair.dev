"""Hub contributor metrics (ticket #41, PRD HUB-10), published as counts only.

``python -m hub metrics`` reads the pull requests and issues of the projects the Hub shows
(the snapshot's ``projects.json``) through GitHub's GraphQL API, and writes
``data/derived/hub/metrics.json`` with, for each quarter from 2026 Q1:

- ``new_contributors``: people whose first merged pull request to any of these repositories
  was merged that quarter. Bots and the repositories' maintainers (GitHub's author
  association ``OWNER``, ``MEMBER`` or ``COLLABORATOR``) are left out.
- for the issues and pull requests those newcomers (anyone but bots and maintainers) opened
  that quarter: ``opened``; ``answered``, those a maintainer has responded to (a comment, a
  review, or merging the pull request); ``within_pledge``, answered within the 7 days every
  listed project pledges; ``waiting``, not answered yet; and ``median_hours``, the median time
  to that first response among those answered.

Usernames are read only in memory, to tell people apart and to know who answered; they are
never written, logged or published. ``metrics.json`` holds counts only. PRD §12 asks for a
review with counsel before this runs on real data, so the Hub sync runs it only when the
repository variable ``HUB_METRICS`` is ``true`` (docs/deploy.md).

The counts follow the projects the Hub shows on the day they are made: when a project joins
or leaves, past quarters change with it.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .github import GitHub, GitHubError
from .sync import OUT

START = (2026, 1)                   # the first quarter counted: the year the Hub was built
MAINTAINERS = frozenset({'OWNER', 'MEMBER', 'COLLABORATOR'})
PLEDGE = timedelta(days=7)
HISTORY_PAGES = 30                  # merged pull requests: up to 3,000 per repository
RECENT_PAGES = 10                   # issues and pull requests opened since START: up to 500 of each
FLOOR = 100                         # stop, writing nothing, if GitHub's GraphQL quota falls below this

ACTOR = 'author { __typename login }'
RESPONSES = f'comments(first: 30) {{ nodes {{ createdAt authorAssociation {ACTOR} }} }}'
HISTORY = '''query($owner: String!, $name: String!, $cursor: String) {
  rateLimit { remaining }
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes { mergedAt authorAssociation %s }
    }
  }
}''' % ACTOR
RECENT_PULLS = '''query($owner: String!, $name: String!, $cursor: String) {
  rateLimit { remaining }
  repository(owner: $owner, name: $name) {
    pullRequests(first: 50, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { createdAt mergedAt authorAssociation %s %s
              reviews(first: 30) { nodes { submittedAt authorAssociation %s } } }
    }
  }
}''' % (ACTOR, RESPONSES, ACTOR)
RECENT_ISSUES = '''query($owner: String!, $name: String!, $cursor: String, $since: DateTime) {
  rateLimit { remaining }
  repository(owner: $owner, name: $name) {
    issues(first: 50, after: $cursor, filterBy: {since: $since}, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { createdAt authorAssociation %s %s }
    }
  }
}''' % (ACTOR, RESPONSES)


def quarter(when: datetime) -> str:
    return f'{when.year}-Q{(when.month - 1) // 3 + 1}'


def quarters(start: tuple, now: datetime) -> list:
    """'2026-Q1' ... the quarter of ``now``."""
    (y, q), out = start, []
    while (y, q) <= (now.year, (now.month - 1) // 3 + 1):
        out.append(f'{y}-Q{q}')
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def when(stamp: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(stamp.replace('Z', '+00:00')) if stamp else None


def person(node: dict) -> Optional[str]:
    """Who wrote ``node``, for telling people apart in memory; None for bots and deleted accounts."""
    author = node.get('author') or {}
    login = author.get('login')
    if not login or author.get('__typename') == 'Bot' or login.endswith('[bot]'):
        return None
    return login


def newcomer(node: dict) -> Optional[str]:
    """The author of an issue or pull request, unless a bot or one of the repository's maintainers."""
    who = person(node)
    return who if who and node.get('authorAssociation') not in MAINTAINERS else None


@dataclass
class Item:
    """An issue or pull request a newcomer opened: when, and when a maintainer first responded."""
    opened: datetime
    answered: Optional[datetime]


def first_response(node: dict, author: str) -> Optional[datetime]:
    """The first comment or review by a maintainer other than the author, or the merge."""
    times = []
    for kind, stamp in (('comments', 'createdAt'), ('reviews', 'submittedAt')):
        for reply in (node.get(kind) or {}).get('nodes') or []:
            who = person(reply)
            if who and who != author and reply.get('authorAssociation') in MAINTAINERS and reply.get(stamp):
                times.append(when(reply[stamp]))
    if node.get('mergedAt'):
        times.append(when(node['mergedAt']))          # only maintainers can merge
    return min(times) if times else None


@dataclass
class Tally:
    """What is learnt from GitHub, in memory only: each person's first merge, and newcomers' items."""
    first_merge: dict = field(default_factory=dict)   # login -> datetime; never written
    items: list = field(default_factory=list)          # Item: times only
    projects: int = 0


class Reader:
    def __init__(self, github: GitHub):
        self.github = github

    def query(self, text: str, **variables) -> dict:
        status, data = self.github.request('POST', '/graphql', {'query': text, 'variables': variables})
        if status == 401:
            raise GitHubError('GitHub’s GraphQL API needs a token: set GITHUB_TOKEN')
        if status >= 400 or not isinstance(data, dict):
            raise GitHubError(f'GitHub answered {status} to a GraphQL query')
        errors = data.get('errors') or []
        if any(e.get('type') == 'NOT_FOUND' for e in errors):
            return {}
        if errors:
            raise GitHubError('GitHub’s GraphQL API: ' + '; '.join(e.get('message', '?') for e in errors[:3]))
        result = data.get('data') or {}
        left = (result.get('rateLimit') or {}).get('remaining')
        if left is not None and left < FLOOR:
            raise GitHubError(f'only {left} GraphQL points are left; try again after the hourly reset')
        return result

    def pages(self, text: str, key: str, limit: int, **variables):
        """The nodes of ``repository.<key>``, page by page."""
        cursor = None
        for _ in range(limit):
            repo = (self.query(text, cursor=cursor, **variables) or {}).get('repository')
            if not repo:
                return
            conn = repo[key]
            yield from conn['nodes']
            if not conn['pageInfo']['hasNextPage']:
                return
            cursor = conn['pageInfo']['endCursor']

    def read(self, repository: str, since: datetime, tally: Tally) -> None:
        owner, name = repository.split('/', 1)
        for pr in self.pages(HISTORY, 'pullRequests', HISTORY_PAGES, owner=owner, name=name):
            who, merged = newcomer(pr), when(pr.get('mergedAt'))
            if who and merged and (who not in tally.first_merge or merged < tally.first_merge[who]):
                tally.first_merge[who] = merged
        stamp = since.strftime('%Y-%m-%dT%H:%M:%SZ')
        for text, key, extra in ((RECENT_PULLS, 'pullRequests', {}), (RECENT_ISSUES, 'issues', {'since': stamp})):
            for node in self.pages(text, key, RECENT_PAGES, owner=owner, name=name, **extra):
                opened = when(node['createdAt'])
                if opened < since:
                    break                               # newest first: the rest are older
                who = newcomer(node)
                if who:
                    tally.items.append(Item(opened, first_response(node, who)))
        tally.projects += 1


def summarise(tally: Tally, now: datetime, start: tuple = START) -> list:
    """One row of counts per quarter. Nothing in it names anyone."""
    rows = []
    current = quarter(now)
    new = {}
    for merged in tally.first_merge.values():
        new[quarter(merged)] = new.get(quarter(merged), 0) + 1
    for q in quarters(start, now):
        items = [i for i in tally.items if quarter(i.opened) == q]
        waits = [(i.answered - i.opened).total_seconds() / 3600 for i in items if i.answered]
        rows.append({'quarter': q, 'complete': q != current, 'new_contributors': new.get(q, 0), 'opened': len(items),
                     'answered': len(waits), 'within_pledge': sum(1 for h in waits if h <= PLEDGE.total_seconds() / 3600),
                     'waiting': len(items) - len(waits),
                     'median_hours': round(statistics.median(waits), 1) if waits else None})
    return rows


def shown(out: Path) -> list:
    """The repositories the Hub shows, from the snapshot the sync wrote."""
    path = Path(out) / 'projects.json'
    if not path.is_file():
        raise ValueError(f'{path} is missing: run python -m hub sync first')
    projects = json.loads(path.read_text('utf-8')).get('projects', [])
    return [p.get('name') or p['repository'] for p in projects if p.get('shown')]


def counted_today(out: Path, now: datetime) -> bool:
    path = Path(out) / 'metrics.json'
    try:
        return json.loads(path.read_text('utf-8'))['generated_at'][:10] == now.strftime('%Y-%m-%d')
    except (OSError, ValueError, KeyError, TypeError):
        return False


def run(out: Path = OUT, github: Optional[GitHub] = None, now: Optional[datetime] = None, daily: bool = False) -> str:
    """Count and write ``metrics.json``; returns the log line, which names no one. Raises
    GitHubError (nothing written) if GitHub fails or its quota runs low."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if daily and counted_today(out, now):
        return 'Hub metrics: already counted today.'
    github = github or GitHub()
    since = datetime(START[0], 3 * START[1] - 2, 1, tzinfo=timezone.utc)
    tally, reader = Tally(), Reader(github)
    for repository in shown(out):
        reader.read(repository, since, tally)
    rows = summarise(tally, now)
    doc = {'about': 'Hub contributor metrics (PRD HUB-10, hub/metrics.py): counts only, for the projects the Hub '
                    'showed on the day. No usernames are stored.',
           'generated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'projects': tally.projects,
           'pledge_days': PLEDGE.days, 'quarters': rows}
    path = Path(out) / 'metrics.json'
    path.with_suffix('.json.tmp').write_text(json.dumps(doc, indent=1) + '\n', 'utf-8')
    path.with_suffix('.json.tmp').replace(path)
    del tally                                           # the usernames go with it
    new = sum(r['new_contributors'] for r in rows)
    opened, answered = sum(r['opened'] for r in rows), sum(r['answered'] for r in rows)
    return (f'Hub metrics: {doc["projects"]} projects, {rows[0]["quarter"]} to {rows[-1]["quarter"]}: {new} new contributors; '
            f'{opened} issues and pull requests from newcomers, {answered} answered. GitHub API: {github.calls} requests.')
