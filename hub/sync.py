"""Sync the Hub from GitHub (ticket #25; PRD HUB-04, HUB-05, AC-HUB-4, AC-HUB-5).

``python -m hub sync`` reads ``projects.yml`` and asks GitHub, for each listed repository, for
the repository itself (description, primary language, licence, topics), its last commit on
the default branch, and its open issues labelled ``good first issue`` or ``help wanted``.
It writes the snapshot the site builds the Hub from, in ``data/derived/hub/``:

    projects.json   every listed project: its registry entry, what GitHub says about it, and
                    its health (``hub/health.py``)
    issues.json     the open beginner issues of the projects the Hub shows, newest first
    cache.json      the ETag of each answer and what was kept from it, for the next run
    HEALTH.md       the health report: every flagged or hidden project, why and since when

GitHub Actions runs it every 6 hours and keeps the snapshot on the ``hub-data`` branch
(``.github/workflows/hub.yml``); the site build reads it from there.

No personal data is kept (AC-HUB-5): nothing about who opened, commented on or was assigned
an issue, no avatars, and no issue text except the title and its "You'll need" line, with
@mentions taken out.

Every request is conditional: it carries the ETag of the last answer, and when nothing has
changed GitHub answers 304, which doesn't count against the rate limit. Before it starts,
the sync checks that the quota left covers a whole run, so it never runs into the limit
(AC-HUB-4), and it logs what is left at the end.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

from . import health, registry
from .checks import BEGINNER_LABELS, TOPIC
from .github import GitHub, GitHubError, _repo

OUT = registry.REPO_DIR / 'data' / 'derived' / 'hub'
PER_PROJECT = 4                 # the repository, its last commit, and one page of issues per label
PAGES = 5                       # at most 500 issues per label
LIMITS = {'title': 200, 'description': 300, 'needs': 120, 'labels': 8}

# "You'll need: Python, pytest" in an issue, or the "You'll need" field of an issue form.
NEEDS = re.compile(r"^\s*(?:[-*]\s+)?(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:you(?:'|’)ll need|you will need|skills(?: needed)?|"
                   r"ستحتاج(?: إلى)?|المهارات(?: المطلوبة)?)\s*(?:\*\*|__)?\s*(?:[:：]\s*(?:\*\*|__)?\s*(.*))?$", re.I)
README = '''# Hub snapshot

Written by `python -m hub sync` every 6 hours (`.github/workflows/hub.yml`), from the projects
listed in `projects.yml` on `main`. Don't edit it: the next sync replaces it. The site build
reads it from this branch (`.github/scripts/hub-snapshot.sh`).

| File | What it holds |
|---|---|
| `projects.json` | Every listed project: its registry entry and what GitHub says about it |
| `issues.json` | The open `good first issue` and `help wanted` issues of the projects the Hub shows |
| `cache.json` | The ETag of each GitHub answer and what was kept from it, for the next sync |
| `HEALTH.md` | The health report: every flagged or hidden project, why, and since when |

Nothing here identifies a person: no usernames, avatars or assignees, and no issue text but
the title and its "You'll need" line. See `hub/README.md` on `main`.
'''
MENTION = re.compile(r'(?<![\w.@])@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:/[\w.-]+)?')


def clean(text, limit: int) -> str:
    """One line of plain text, at most ``limit`` characters."""
    text = re.sub(r'[\x00-\x1f\x7f]+', ' ', str(text or ''))
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > limit:
        text = text[:limit - 1].rsplit(' ', 1)[0].rstrip(' ,;:.') + '…'
    return text


def needs(body: str) -> str:
    """What an issue says a newcomer needs ("You'll need: Python, pytest"), or ''."""
    lines = (body or '').replace('\r\n', '\n').split('\n')
    for i, line in enumerate(lines):
        m = NEEDS.match(line)
        if not m:
            continue
        value = m.group(1)
        if value is None:                          # a heading: the answer is the next line with text
            value = next((l for l in lines[i + 1:i + 4] if l.strip()), '')
        value = re.sub(r'<[^>]*>', '', value)
        value = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', value)
        value = re.sub(r'\s*\([^()]*\)', lambda m: '' if MENTION.search(m.group(0)) else m.group(0), value)
        if MENTION.search(value):                  # it names someone: leave it out
            return ''
        value = re.sub(r'[`*_~]+', '', value)
        value = clean(value, LIMITS['needs']).strip(' ,;').rstrip('.')
        if value and value.lower() not in ('no response', 'n/a', 'none', '-'):
            return value
        return ''
    return ''


# ---- what is kept from each answer: nothing about people
def keep_repository(r: dict) -> dict:
    lic = r.get('license') or {}
    spdx = lic.get('spdx_id')
    return {'full_name': r.get('full_name'), 'url': r.get('html_url'),
            'description': clean(r.get('description'), LIMITS['description']),
            'language': r.get('language'), 'licence': spdx if spdx not in (None, 'NOASSERTION') else None,
            'topic': TOPIC in (r.get('topics') or []), 'default_branch': r.get('default_branch') or 'main',
            'archived': bool(r.get('archived')), 'private': bool(r.get('private')),
            'has_issues': r.get('has_issues') is not False}


def keep_commit(commits) -> Optional[str]:
    if not commits:
        return None
    c = commits[0].get('commit') or {}
    return (c.get('committer') or {}).get('date') or (c.get('author') or {}).get('date')


def keep_issues(issues) -> list:
    out = []
    for i in issues or []:
        if 'pull_request' in i:
            continue
        labels = []
        for label in i.get('labels') or []:
            name = label.get('name') if isinstance(label, dict) else label
            if isinstance(name, str) and name not in labels:
                labels.append(clean(name, 50))
        out.append({'number': i['number'], 'url': i['html_url'], 'title': clean(i.get('title'), LIMITS['title']),
                    'labels': labels[:LIMITS['labels']], 'created_at': i['created_at'], 'needs': needs(i.get('body'))})
    return out


class Cache:
    """ETags and what was kept from the answers they stand for, by API path."""

    def __init__(self, entries: Optional[dict] = None):
        self.old = entries or {}
        self.new: dict = {}

    def get(self, github: GitHub, path: str, keep: Callable):
        """What ``keep`` takes from the answer at ``path``, or None if there is nothing there.
        GitHub only sends the answer again if it changed."""
        old = self.old.get(path)
        status, data, etag = github.get_if_changed(path, old['etag'] if old else None)
        if status == 304 and old:
            self.new[path] = old
            return old['data']
        if data is None:
            return None
        kept = keep(data)
        if etag:
            self.new[path] = {'etag': etag, 'data': kept}
        return kept


def keep_page(issues) -> dict:
    """A page of issues: how many GitHub sent (pull requests count, to know if another page
    follows) and the issues kept from it."""
    return {'n': len(issues or []), 'issues': keep_issues(issues)}


def labelled(cache: Cache, github: GitHub, repo: str, label: str) -> list:
    out = []
    for page in range(1, PAGES + 1):
        path = f'/repos/{_repo(repo)}/issues?state=open&labels={quote(label, safe="")}&per_page=100&page={page}'
        kept = cache.get(github, path, keep_page) or {'n': 0, 'issues': []}
        out += kept['issues']
        if kept['n'] < 100:
            break
    return out


@dataclass
class Snapshot:
    checked: datetime
    projects: list
    issues: list
    cache: dict

    @property
    def generated_at(self) -> str:
        return self.checked.strftime('%Y-%m-%dT%H:%M:%SZ')


def collect(projects: list, github: GitHub, cache_entries: Optional[dict] = None, now: Optional[datetime] = None,
            previous: Optional[dict] = None) -> Snapshot:
    """Ask GitHub about every registry project (``registry.Project``), then run the health
    checks (``previous``: the last snapshot's projects, by repository)."""
    now = now or datetime.now(timezone.utc)
    cache = Cache(cache_entries)
    out, found_issues = [], {}
    for p in projects:
        project = {'repository': p.repository, 'category': p.category, 'tags': list(p.tags), 'pledge': p.maintainer_pledge,
                   'added': p.added}
        out.append(project)
        info = cache.get(github, f'/repos/{_repo(p.repository)}', keep_repository)
        if info is None or info['private']:
            project.update(found=False, topic=False, archived=False, issues=0)
            continue
        name = info['full_name'] or p.repository
        project.update(found=True, name=name, url=info['url'] or f'https://github.com/{name}',
                       description=info['description'], language=info['language'], licence=info['licence'],
                       topic=info['topic'], archived=info['archived'])
        branch = info['default_branch']
        project['last_commit'] = cache.get(github, f'/repos/{_repo(name)}/commits?sha={quote(branch, safe="")}&per_page=1',
                                           keep_commit)
        found = {}
        if info['has_issues']:
            for label in BEGINNER_LABELS:
                for issue in labelled(cache, github, name, label):
                    found.setdefault(issue['number'], issue)
        project['issues'] = len(found)
        found_issues[p.repository] = [dict(issue, repo=name, language=info['language']) for issue in found.values()]
    health.apply(out, previous, now.astimezone(timezone.utc).date())
    issues = [i for p in out if p['shown'] for i in found_issues.get(p['repository'], [])]
    issues.sort(key=lambda i: (i['created_at'], i['repo'], i['number']), reverse=True)
    return Snapshot(now, out, issues, cache.new)


def write(snapshot: Snapshot, out: Path = OUT) -> None:
    """Write the three files together: each is complete or not replaced."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    docs = {'projects.json': {'generated_at': snapshot.generated_at, 'projects': snapshot.projects},
            'issues.json': {'generated_at': snapshot.generated_at, 'issues': snapshot.issues},
            'cache.json': {'about': 'ETags from the last Hub sync and what was kept from each answer (hub/sync.py).',
                           'entries': snapshot.cache}}
    texts = {name: json.dumps(doc, ensure_ascii=False, indent=1) + '\n' for name, doc in docs.items()}
    texts['README.md'] = README
    texts['HEALTH.md'] = health.report(snapshot.projects, snapshot.checked)
    for name, text in texts.items():
        (out / f'{name}.tmp').write_text(text, 'utf-8')
    for name in texts:
        (out / f'{name}.tmp').replace(out / name)


def _last(out: Path, name: str, key: str):
    path = Path(out) / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text('utf-8')).get(key)
    except (ValueError, AttributeError):
        return None


def load_cache(out: Path = OUT) -> dict:
    return _last(out, 'cache.json', 'entries') or {}


def load_previous(out: Path = OUT) -> dict:
    """The last snapshot's projects, by repository: when each flag was first raised."""
    return {p['repository']: p for p in _last(out, 'projects.json', 'projects') or [] if isinstance(p, dict) and 'repository' in p}


def _reset(rate: dict) -> str:
    try:
        return datetime.fromtimestamp(int(rate['reset']), timezone.utc).strftime('%H:%M UTC')
    except (KeyError, TypeError, ValueError):
        return 'later'


def run(registry_path: Path = registry.REGISTRY, out: Path = OUT, github: Optional[GitHub] = None,
        now: Optional[datetime] = None) -> str:
    """Sync and write the snapshot; returns the log line. Raises GitHubError (nothing written)
    if GitHub fails or the quota left doesn't cover a run, and ValueError for a broken registry."""
    github = github or GitHub()
    reg = registry.load(registry_path)
    if not reg.ok:
        raise ValueError(f'{registry_path} has {len(reg.problems)} problem(s): run python -m hub check-registry')
    needed = PER_PROJECT * len(reg.projects) + 2
    before = github.rate_limit() or {}
    if before and int(before.get('remaining', 0)) < needed:
        raise GitHubError(f'only {before["remaining"]} of {before.get("limit")} API requests are left until {_reset(before)}, '
                          f'and a sync needs up to {needed}. Set GITHUB_TOKEN, or wait.')
    snapshot = collect(reg.projects, github, load_cache(out), now, load_previous(out))
    write(snapshot, out)
    after = github.rate_limit() or github.rate or {}
    status = {k: sum(1 for p in snapshot.projects if p['status'] == k) for k in ('healthy', 'flagged', 'hidden')}
    quota = (f'{int(after["remaining"]):,} of {int(after["limit"]):,} left, resets at {_reset(after)}'
             if after.get('remaining') not in (None, '') else 'quota unknown')
    return (f'Hub: {len(snapshot.projects)} project{"s" if len(snapshot.projects) != 1 else ""} ({status["healthy"]} healthy, '
            f'{status["flagged"]} flagged, {status["hidden"]} hidden), '
            f'{len(snapshot.issues)} open issue{"s" if len(snapshot.issues) != 1 else ""}. GitHub API: {github.calls} '
            f'request{"s" if github.calls != 1 else ""}, {github.unchanged} unchanged (304{", free" if github.token else ""}); '
            f'{quota}.')

