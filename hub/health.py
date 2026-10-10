"""Hub health checks (ticket #26; PRD HUB-06, AC-HUB-3).

Every sync (every 6 hours, so at least daily) checks each listed project with what it has
just fetched, at no extra cost. A project is flagged when it has no commit in 90 days, or no
longer carries the ``djazairdev`` topic. It is hidden after 14
days flagged, and at once when the topic is removed (only maintainers can set topics, so
removing it withdraws consent) or the repository is archived, private or gone. It shows
again as soon as the problem is fixed. A project with no open beginner issues is not flagged
(decision D27): the report lists it, and its card shows 0 open issues.

The date a project was first flagged is carried from one snapshot to the next in
``projects.json``. ``report`` writes ``HEALTH.md``, which lists every flagged and hidden
project with the reason and the date it was flagged, on the ``hub-data`` branch. It also names
the djazairdev repositories that carry the topic but whose topics don't give a category and
tags (``hub/discover.py``), with what to add.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from .checks import ACTIVE_DAYS, TOPIC

FLAGGED_DAYS = 14
# The reasons, in the order the report gives them; the first three hide a project at once.
REASONS = {
    'missing': 'The repository is gone or private',
    'archived': 'The repository is archived',
    'topic': f'The `{TOPIC}` topic was removed',
    'inactive': f'No commit in {ACTIVE_DAYS} days',
}
AT_ONCE = ('missing', 'archived', 'topic')


def _date(stamp: str) -> date:
    return datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone(timezone.utc).date()


def problems(project: dict, today: date) -> dict:
    """What is wrong with the project today: {reason: what was found}."""
    if not project.get('found'):
        return {'missing': 'GitHub doesn’t show it: deleted, or made private.'}
    out = {}
    if project.get('archived'):
        out['archived'] = 'Archived, so it takes no pull requests.'
    if not project.get('topic'):
        out['topic'] = 'Not among the repository’s topics.'
    last = project.get('last_commit')
    if not last:
        out['inactive'] = 'No commits on the default branch.'
    else:
        days = (today - _date(last)).days
        if days > ACTIVE_DAYS:
            out['inactive'] = f'Last commit on {_date(last).isoformat()}, {days} days ago.'
    return out


def apply(projects: list, previous: Optional[dict], today: date) -> None:
    """Set ``flags``, ``status`` (healthy, flagged or hidden), ``hide_on`` and ``shown`` on
    each project. ``previous``: the last snapshot's projects, by repository, for the dates
    flags were first raised."""
    previous = previous or {}
    for p in projects:
        since = {f['reason']: f['since'] for f in (previous.get(p['repository']) or {}).get('flags') or []}
        p['flags'] = [{'reason': reason, 'since': since.get(reason, today.isoformat()), 'found': found}
                      for reason, found in sorted(problems(p, today).items(), key=lambda kv: list(REASONS).index(kv[0]))]
        hide_on = [date.fromisoformat(f['since']) + (timedelta(0) if f['reason'] in AT_ONCE else timedelta(days=FLAGGED_DAYS))
                   for f in p['flags']]
        p['hide_on'] = min(hide_on).isoformat() if hide_on else None
        p['status'] = 'healthy' if not p['flags'] else 'hidden' if min(hide_on) <= today else 'flagged'
        p['shown'] = p['status'] != 'hidden'


def _project(p: dict) -> str:
    return f'[{p.get("name") or p["repository"]}](https://github.com/{p.get("name") or p["repository"]})'


def report(projects: list, now: datetime, skipped=()) -> str:
    """HEALTH.md: every flagged and hidden project, with the reason and the date it was flagged.
    ``skipped``: (repository, reason) for the djazairdev repositories that can't be listed."""
    counts = {s: sum(1 for p in projects if p['status'] == s) for s in ('healthy', 'flagged', 'hidden')}
    when = now.astimezone(timezone.utc)
    lines = ['# Hub health report', '',
             f'Checked on {when.day} {when:%B %Y} at {when:%H:%M} UTC by `python -m hub sync`, which runs every 6 hours.', '',
             f'A listed project is flagged when it has no commit in {ACTIVE_DAYS} days, or no longer carries the `{TOPIC}` '
             f'topic (PRD HUB-06). It is hidden from the Hub after '
             f'{FLAGGED_DAYS} days flagged, and at once when the topic is removed or the repository is archived, private or '
             'gone. It shows again as soon as the problem is fixed. Projects are listed in '
             '[`projects.yml`](https://github.com/djazairdev/djazair.dev/blob/main/projects.yml), or found in the '
             f'[djazairdev](https://github.com/djazairdev) organisation by the `{TOPIC}` topic (decision D29).', '']
    n = len(projects)
    lines += [f'**{n} project{"s" if n != 1 else ""}: {counts["healthy"]} healthy, {counts["flagged"]} flagged, '
              f'{counts["hidden"]} hidden.**', '']

    def table(status: str, title: str, last: str) -> None:
        rows = [p for p in projects if p['status'] == status]
        lines.extend([f'## {title}', ''])
        if not rows:
            lines.extend(['None.', ''])
            return
        lines.extend([f'| Project | Reason | Found | Flagged on | {last} |', '|---|---|---|---|---|'])
        for p in sorted(rows, key=lambda p: (p['hide_on'] or '', p['repository'].lower())):
            for i, f in enumerate(p['flags']):
                lines.append(f'| {_project(p) if i == 0 else ""} | {REASONS[f["reason"]]} | {f["found"]} | {f["since"]} | '
                             f'{p["hide_on"] if i == 0 else ""} |')
        lines.append('')

    table('flagged', 'Flagged', 'Hidden on, unless fixed')
    table('hidden', 'Hidden', 'Hidden since')
    healthy = sorted((p for p in projects if p['status'] == 'healthy'), key=lambda p: p['repository'].lower())
    lines.extend(['## Healthy', '', ', '.join(_project(p) for p in healthy) + '.' if healthy else 'None.', ''])
    quiet = sorted((p for p in projects if p['shown'] and not p.get('issues')), key=lambda p: p['repository'].lower())
    if quiet:
        lines.extend(['## No open beginner issues', '',
                      'Not a flag: these projects stay listed, with nothing in the Hub’s issue feed until they label an issue '
                      '`good first issue` or `help wanted`.', '', ', '.join(_project(p) for p in quiet) + '.', ''])
    if skipped:
        lines.extend(['## Found in djazairdev, not listed yet', '',
                      f'These repositories carry the `{TOPIC}` topic, but their topics don’t say how to list them. They join the '
                      'Hub at the next sync after the fix.', '', '| Repository | What to add |', '|---|---|'])
        lines.extend(f'| [{name}](https://github.com/{name}) | {reason} |' for name, reason in sorted(skipped, key=lambda s: s[0].lower()))
        lines.append('')
    return '\n'.join(lines)
