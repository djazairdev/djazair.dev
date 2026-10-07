"""Project ideas and their votes (ticket #39, PRD HUB-07).

``python -m hub ideas`` reads the Ideas category of GitHub Discussions on djazairdev/djazair.dev
through GitHub's GraphQL API, and writes ``data/derived/hub/ideas.json``: every idea that is open
or adopted, ranked by votes. Votes are GitHub upvotes, one per account. For each idea it keeps
the title, the number of votes and comments, whether the idea has a champion, the skills its
form asks for, and whether it was adopted (the ``adopted`` label). Closed ideas that weren't
adopted leave the list.

Every quarter is a round. The first run after a round closes saves that round's count in
``rounds``: the open ideas by votes, as GitHub counted them then. The maintainers review the
ideas from that count, top first, and adopt one (docs/hub-ideas.md).

Nothing about people is kept: no authors, no champion's name (only whether there is one), and
no text but the title, with @mentions taken out. The idea's text is read in memory, for the
champion and the skills, and never written.

While Discussions is off, or the repository has no Ideas category, it writes an empty list.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .github import GitHub
from .metrics import Reader, quarter, when
from .sync import MENTION, OUT, clean

REPO = 'djazairdev/djazair.dev'
CATEGORY = 'ideas'                  # the category's slug, and the name of its form in .github/DISCUSSION_TEMPLATE/
ADOPTED = 'adopted'                 # the label a maintainer adds to the idea the organisation takes on
PAGES = 10                          # up to 1,000 ideas
RANKED = 10                         # ideas saved in each round's count
TITLE = 200

# The form's skill options (.github/DISCUSSION_TEMPLATE/ideas.yml), as keys the site translates.
SKILLS = {
    'Web front end': 'web',
    'Back end and APIs': 'backend',
    'Mobile apps': 'mobile',
    'Data and open data': 'data',
    'Machine learning': 'ml',
    'Design and UX': 'design',
    'Arabic, Tamazight or Darija language work': 'language',
    'Translation and localisation': 'translation',
    'Documentation': 'docs',
    'Infrastructure and operations': 'ops',
    'Hardware': 'hardware',
}
# What the Champion field says when nobody leads the idea yet.
NO_CHAMPION = ('wanted', 'no response', 'none', 'n/a', 'nobody', 'tbd', '-', 'مطلوب')

CATEGORY_QUERY = '''query($owner: String!, $name: String!, $slug: String!) {
  rateLimit { remaining }
  repository(owner: $owner, name: $name) {
    hasDiscussionsEnabled
    discussionCategory(slug: $slug) { id }
  }
}'''
IDEAS_QUERY = '''query($owner: String!, $name: String!, $category: ID!, $cursor: String) {
  rateLimit { remaining }
  repository(owner: $owner, name: $name) {
    discussions(first: 100, after: $cursor, categoryId: $category, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes { number url title body createdAt closed upvoteCount comments { totalCount } labels(first: 20) { nodes { name } } }
    }
  }
}'''
TITLE_PREFIX = re.compile(r'^\s*(?:idea|فكرة)\s*[:：\-–—]\s*', re.I)
HEADING = re.compile(r'^#{2,4}\s+(.+?)\s*#*\s*$')


def form_fields(body: str) -> dict:
    """The answers of a form-made discussion, by lower-case label: GitHub writes each field as a
    ``### Label`` heading followed by the answer."""
    fields, label, lines = {}, None, []
    for line in (body or '').replace('\r\n', '\n').split('\n'):
        m = HEADING.match(line)
        if m:
            if label is not None:
                fields[label] = '\n'.join(lines).strip()
            label, lines = m.group(1).strip().lower(), []
        elif label is not None:
            lines.append(line)
    if label is not None:
        fields[label] = '\n'.join(lines).strip()
    return fields


def has_champion(answer: Optional[str]) -> bool:
    """Whether the Champion field names someone. The name itself is never kept."""
    text = re.sub(r'[`*_~>]+', ' ', answer or '')
    text = re.sub(r'\s+', ' ', text).strip(' .!').lower()
    if not text or text in NO_CHAMPION:
        return False
    return not text.startswith('wanted')


def skills(answer: Optional[str]) -> list:
    """The form's skill options in the answer, in the form's order. One option has commas in
    it, so options are looked for whole rather than split on commas."""
    text = answer or ''
    return [key for option, key in SKILLS.items() if option.lower() in text.lower()]


def title(text: Optional[str]) -> str:
    """The title without the form's "Idea: " and without @mentions."""
    raw = clean(text, TITLE)
    out = clean(MENTION.sub('', TITLE_PREFIX.sub('', raw)), TITLE)
    return out or raw


def keep(node: dict) -> Optional[dict]:
    """What is kept of a discussion: nothing about who wrote it. None for a closed idea that
    wasn't adopted."""
    labels = {(label or {}).get('name', '').lower() for label in (node.get('labels') or {}).get('nodes') or []}
    adopted = ADOPTED in labels
    if node.get('closed') and not adopted:
        return None
    fields = form_fields(node.get('body'))
    return {'number': node['number'], 'url': node['url'], 'title': title(node.get('title')),
            'created_at': node['createdAt'], 'votes': int(node.get('upvoteCount') or 0),
            'comments': int(((node.get('comments') or {}).get('totalCount')) or 0),
            'champion': has_champion(fields.get('champion')), 'skills': skills(fields.get('skills needed')),
            'status': 'adopted' if adopted else 'open'}


def ranked(ideas: list) -> list:
    """Open ideas first, by votes, then the earlier idea; adopted ideas after them, the same way."""
    return sorted(ideas, key=lambda i: (i['status'] != 'open', -i['votes'], i['created_at'], i['number']))


def read(github: GitHub, repo: str = REPO, slug: str = CATEGORY) -> Optional[list]:
    """The ideas, or None if the repository has Discussions off or no such category."""
    owner, name = repo.split('/', 1)
    reader = Reader(github)
    found = (reader.query(CATEGORY_QUERY, owner=owner, name=name, slug=slug) or {}).get('repository') or {}
    category = found.get('discussionCategory') if found.get('hasDiscussionsEnabled') else None
    if not category:
        return None
    kept = (keep(node) for node in reader.pages(IDEAS_QUERY, 'discussions', PAGES, owner=owner, name=name,
                                                 category=category['id']))
    return ranked([idea for idea in kept if idea])


def count(ideas: list, now: datetime) -> dict:
    """A round's count: the open ideas by votes, as they stand at ``now``."""
    return {'counted_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'ranking': [{k: i[k] for k in ('number', 'url', 'title', 'votes', 'champion')}
                        for i in ideas if i['status'] == 'open'][:RANKED]}


def load(out: Path = OUT) -> Optional[dict]:
    path = Path(out) / 'ideas.json'
    try:
        doc = json.loads(path.read_text('utf-8'))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def run(out: Path = OUT, github: Optional[GitHub] = None, now: Optional[datetime] = None, repo: str = REPO) -> str:
    """Read the ideas and write ``ideas.json``; returns the log line, which names no one.
    Raises GitHubError (nothing written) if GitHub fails or its quota runs low."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    github = github or GitHub()
    ideas = read(github, repo)
    previous = load(out) or {}
    rounds = [r for r in previous.get('rounds') or [] if isinstance(r, dict) and r.get('quarter')]
    # The last run was in an earlier quarter, so that round has closed since: save its count.
    counted = None
    last = when(previous.get('generated_at'))
    if ideas is not None and previous.get('category') and last and quarter(last) < quarter(now):
        if all(r['quarter'] != quarter(last) for r in rounds):
            counted = quarter(last)
            rounds.append({'quarter': counted, **count(ideas, now)})
    doc = {'about': 'Project ideas from the Ideas category of GitHub Discussions, ranked by votes (hub/ideas.py, '
                    'docs/hub-ideas.md). Titles and counts only: no usernames.',
           'generated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
           'category': f'https://github.com/{repo}/discussions/categories/{CATEGORY}' if ideas is not None else None,
           'ideas': ideas or [], 'rounds': rounds}
    path = Path(out) / 'ideas.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix('.json.tmp').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    path.with_suffix('.json.tmp').replace(path)
    if ideas is None:
        return f'Hub ideas: {repo} has Discussions off or no "{CATEGORY}" category; wrote an empty list.'
    open_ = [i for i in ideas if i['status'] == 'open']
    votes = sum(i['votes'] for i in open_)
    line = (f'Hub ideas: {len(open_)} open idea{"s" if len(open_) != 1 else ""} ({votes} vote{"s" if votes != 1 else ""}), '
            f'{len(ideas) - len(open_)} adopted.')
    if counted:
        top = rounds[-1]['ranking'][:1]
        lead = f' #{top[0]["number"]} leads with {top[0]["votes"]} vote{"s" if top[0]["votes"] != 1 else ""}.' if top else ' no open ideas.'
        line += f' Round {counted} counted:{lead}'
    return f'{line} GitHub API: {github.calls} request{"s" if github.calls != 1 else ""}.'

