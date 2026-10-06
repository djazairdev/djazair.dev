"""Hub submissions (ticket #16; PRD HUB-02, HUB-03, AC-HUB-2).

A project asks to be listed in one of two ways, and neither needs a djazair.dev account:

- a pull request that adds an entry to ``projects.yml``: the new or changed entries are
  checked, and the proposed file must pass the registry schema;
- the "List a project in the Hub" issue form, for people less familiar with git: the
  answers become an entry, which is checked the same way.

Either way one comment shows the result ("6 of 7 passed, 1 waits for a reviewer"), with
what was found and how to fix each failure, and is updated when the checks run again.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from . import checks, registry
from .github import GitHub
from .schemacheck import Checker

MARKER = '<!-- djazair.dev listing-check -->'
ICONS = {'pass': '✅', 'fail': '❌', 'review': '👀', 'error': '⚠️'}

# The issue form's field labels, as GitHub writes them into the issue body (.github/ISSUE_TEMPLATE/hub-listing.yml).
FORM = {'repository': 'Repository', 'category': 'Category', 'tags': 'Tags',
        'relevance': 'How does the project relate to Algeria?', 'pledge': 'Maintainer pledge', 'topic': 'GitHub topic'}


def safe(text: str) -> str:
    """Text from a submission, made inert in a comment: no HTML, no @mentions, no table breaks."""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('@', '@\u200b')
            .replace('|', '\\|').replace('\r', ' ').replace('\n', ' '))


def report_markdown(report: checks.Report) -> str:
    out = [f'#### `{report.repository}` · {report.summary()}', '', '| | Check | Result |', '|:-:|---|---|']
    for r in report.results:
        text = safe(r.found) + (f' **Fix:** {safe(r.fix)}' if r.fix else '')
        out.append(f'| {ICONS[r.status]} | `{r.key}` | {text} |')
    if report.notes:
        out += [''] + [f'- {safe(n)}' for n in report.notes]
    return '\n'.join(out)


def comment(title: str, sections: list, footer: str) -> str:
    return '\n\n'.join([MARKER, f'### listing-check · {title}'] + sections + [footer]) + '\n'


@dataclass
class Outcome:
    body: str                                   # the comment, as Markdown
    ok: bool                                    # every automatic check passed
    reports: list = field(default_factory=list)


def _entries(result: registry.Registry) -> dict:
    return {p.repository.lower(): p for p in result.projects}


def check_pull_request(proposed: str, base: Optional[str], github: GitHub, today: Optional[date] = None) -> Outcome:
    """Check the ``projects.yml`` a pull request proposes, against the one on main."""
    today = today or datetime.now(timezone.utc).date()
    after = registry.check(proposed, today)
    footer = ('Submissions are reviewed within 7 days. After fixing something on GitHub, edit this pull request’s '
              'description to run the checks again. See [CONTRIBUTING.md](https://github.com/djazairdev/djazair.dev/blob/main/'
              'CONTRIBUTING.md#list-a-project-in-the-hub).')
    if not after.ok:
        lines = [f'- line {p.line}: {safe(p)}' if p.line else f'- {safe(p)}' for p in after.problems]
        return Outcome(comment('`projects.yml` needs a fix', ['The file doesn’t match the registry format:', '\n'.join(lines)],
                               footer), False)
    before = _entries(registry.check(base, today)) if base else {}
    now = _entries(after)
    changed = [p for key, p in now.items() if key not in before or vars(before[key]) | {'line': 0} != vars(p) | {'line': 0}]
    removed = [p for key, p in before.items() if key not in now]
    sections, reports = [], []
    for project in changed:
        entry = {'category': project.category, 'tags': project.tags, 'maintainer_pledge': project.maintainer_pledge}
        report = checks.run(project.repository, entry, github, today)
        reports.append(report)
        sections.append(report_markdown(report))
    if removed:
        sections.append('Removes ' + ', '.join(f'`{p.repository}`' for p in removed) + ' from the Hub.')
    if not changed and not removed:
        sections.append('No entry was added or changed.')
    ok = all(r.ok for r in reports)
    title = ('all automatic checks passed' if ok else 'some checks need a fix') if reports else 'nothing to check'
    return Outcome(comment(title, sections, footer), ok, reports)


def parse_issue(body: str) -> dict:
    """The issue form's answers: {field id: text}. Unanswered optional fields are empty."""
    answers, label, buf = {}, None, []
    by_label = {v: k for k, v in FORM.items()}
    for line in (body or '').replace('\r\n', '\n').split('\n'):
        m = re.match(r'^###\s+(.+?)\s*$', line)
        if m and m.group(1) in by_label:
            if label:
                answers[by_label[label]] = '\n'.join(buf).strip()
            label, buf = m.group(1), []
        elif label:
            buf.append(line)
    if label:
        answers[by_label[label]] = '\n'.join(buf).strip()
    return {k: ('' if v == '_No response_' else v) for k, v in answers.items()}


def normalise_repository(text: str) -> str:
    """'https://github.com/Owner/Name.git/' -> 'Owner/Name'."""
    text = text.strip().strip('`').strip()
    text = re.sub(r'^(https?://)?(www\.)?github\.com/', '', text, flags=re.I)
    return re.sub(r'(\.git)?/*$', '', text)


def _ticked(text: str) -> bool:
    return bool(re.search(r'^\s*[-*]\s*\[[xX]\]', text or '', re.M))


def check_issue(body: str, github: GitHub, today: Optional[date] = None) -> Outcome:
    """Check a listing request made with the issue form."""
    today = today or datetime.now(timezone.utc).date()
    answers = parse_issue(body)
    tags = [t.strip() for t in re.split(r'[,\n]', answers.get('tags', '')) if t.strip()]
    entry = {'repository': normalise_repository(answers.get('repository', '')), 'category': answers.get('category', '').strip(),
             'tags': tags, 'maintainer_pledge': _ticked(answers.get('pledge', '')), 'added': today.isoformat()}
    footer = ('A djazair.dev maintainer checks relevance and adds the entry to `projects.yml` within 7 days. After fixing '
              'something on GitHub, edit this issue to run the checks again. See [CONTRIBUTING.md](https://github.com/'
              'djazairdev/djazair.dev/blob/main/CONTRIBUTING.md#list-a-project-in-the-hub).')
    checker = Checker(json.loads(registry.SCHEMA.read_text('utf-8')))
    problems = [e for e in checker.errors({'projects': [entry]}) if e.path[2:3] != ('maintainer_pledge',)]
    if problems:
        names = {'repository': 'Repository', 'category': 'Category', 'tags': 'Tags'}
        lines = [f'- **{names.get(e.path[2], e.path[2]) if len(e.path) > 2 else "Form"}**: {safe(e.message)}' for e in problems]
        return Outcome(comment('the form needs a fix', ['Some answers can’t be read:', '\n'.join(lines)], footer), False)
    report = checks.run(entry['repository'], entry, github, today)
    yaml = '\n'.join(['```yaml', f'  - repository: {entry["repository"]}', f'    category: {entry["category"]}',
                      f'    tags: [{", ".join(tags)}]', '    maintainer_pledge: true', f'    added: {entry["added"]}', '```'])
    sections = [report_markdown(report)]
    if report.ok:
        sections.append('The entry for `projects.yml`, once a reviewer has checked relevance:\n\n' + yaml)
    title = 'all automatic checks passed' if report.ok else 'some checks need a fix'
    return Outcome(comment(title, sections, footer), report.ok, [report])
