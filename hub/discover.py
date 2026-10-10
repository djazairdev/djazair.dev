"""Projects of the djazairdev organisation, found by their topic (decision D29).

Every sync also lists the organisation's public repositories. One that carries the
``djazairdev`` topic, and isn't a fork, archived, or already in ``projects.yml``, joins the Hub
without an entry: its topics give the category (one of ``app``, ``library``, ``tool`` or
``dataset``) and the tags, which ``projects.yml`` would otherwise hold. djazairdev's
repositories follow its project template, whose CONTRIBUTING file makes the maintainer pledge.

Only djazairdev's own repositories are found this way: only the organisation's maintainers can
create them or set their topics. Any other project applies with ``projects.yml`` or the issue
form, as before. An entry in ``projects.yml`` wins over the topics, and a repository that
carries the ``djazairdev`` topic but can't be listed is named in ``HEALTH.md`` with what to add.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Optional

from . import registry
from .checks import TOPIC

ORG = 'djazairdev'
PAGES = 3                       # at most 300 repositories
CATEGORIES = tuple(json.loads(registry.SCHEMA.read_text('utf-8'))['$defs']['project']['properties']['category']['enum'])
MAX_TAGS = 5


def keep_page(repos) -> dict:
    """A page of the organisation's repositories: how many GitHub sent, and only the fields the
    discovery needs."""
    return {'n': len(repos or []),
            'repos': [{'full_name': r.get('full_name'), 'topics': list(r.get('topics') or []), 'fork': bool(r.get('fork')),
                       'archived': bool(r.get('archived')), 'private': bool(r.get('private'))} for r in repos or []]}


def org_repos(cache, github, org: str = ORG) -> list:
    out = []
    for page in range(1, PAGES + 1):
        kept = cache.get(github, f'/orgs/{org}/repos?type=public&sort=full_name&per_page=100&page={page}', keep_page) \
            or {'n': 0, 'repos': []}
        out += kept['repos']
        if kept['n'] < 100:
            break
    return out


def entry(repo: dict, tags: list, added: str):
    """The registry entry a repository's topics give, or the reason there is none."""
    topics = repo['topics']
    categories = [c for c in CATEGORIES if c in topics]
    found = [t for t in tags if t in topics]
    if not categories:
        return f'No category: add one of the topics {", ".join(f"`{c}`" for c in CATEGORIES)}.'
    if len(categories) > 1:
        return f'Several categories ({", ".join(f"`{c}`" for c in categories)}): keep one of these topics.'
    if not found:
        return 'No tag: add at least one of the topics listed in CONTRIBUTING.md (`arabic`, `open-data`, `education`…).'
    if len(found) > MAX_TAGS:
        return f'{len(found)} tags ({", ".join(f"`{t}`" for t in found)}): keep at most {MAX_TAGS} of these topics.'
    return registry.Project(repo['full_name'], categories[0], found, True, added, source='topic')


def discover(cache, github, listed: list, previous: Optional[dict], today: date, org: str = ORG) -> tuple:
    """(projects, skipped): the organisation's repositories that join the Hub by their topic, as
    ``registry.Project``, and those that carry the topic but can't, as (repository, reason).
    ``listed``: the ``projects.yml`` entries; ``previous``: the last snapshot's projects, by
    repository, which keeps the date each was first listed."""
    previous = previous or {}
    names = {p.repository.lower() for p in listed}
    tags = registry.tags()
    projects, skipped = [], []
    for repo in org_repos(cache, github, org):
        name = repo['full_name']
        if (not name or repo['private'] or repo['fork'] or repo['archived'] or TOPIC not in repo['topics']
                or name.lower() in names):
            continue
        added = (previous.get(name) or {}).get('added') or today.isoformat()
        found = entry(repo, tags, added)
        if isinstance(found, str):
            skipped.append((name, found))
        else:
            projects.append(found)
    return projects, skipped
