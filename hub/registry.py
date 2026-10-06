"""The Hub registry, ``projects.yml`` (ticket #15; PRD HUB-01).

Each entry has a repository, a category, tags saying how the project relates to Algeria, the
maintainer pledge and the date it was added. Language, licence and activity are read from
GitHub, so they aren't stored. ``check`` reads the file and validates it against
``hub/projects.schema.json``, then checks what a schema can't: a repository listed twice
(GitHub names ignore case) and a date in the future.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from . import miniyaml
from .schemacheck import Checker, path_text

REPO_DIR = Path(__file__).resolve().parent.parent
REGISTRY = REPO_DIR / 'projects.yml'
SCHEMA = Path(__file__).resolve().parent / 'projects.schema.json'


@dataclass(frozen=True)
class Problem:
    line: Optional[int]
    where: str             # projects[2] (owner/name).category
    message: str

    def __str__(self) -> str:
        return f'{self.where}: {self.message}' if self.where else self.message


@dataclass
class Project:
    repository: str
    category: str
    tags: list
    maintainer_pledge: bool
    added: str
    line: int = 0

    @property
    def owner(self) -> str:
        return self.repository.split('/')[0]

    @property
    def name(self) -> str:
        return self.repository.split('/')[1]


@dataclass
class Registry:
    projects: list = field(default_factory=list)
    problems: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def tags() -> list:
    """The allowed tags, in the schema's order."""
    return json.loads(SCHEMA.read_text('utf-8'))['$defs']['tag']['enum']


def _line(where: dict, path: tuple) -> Optional[int]:
    while path:
        if path in where:
            return where[path]
        path = path[:-1]
    return None


def check(text: str, today: Optional[date] = None) -> Registry:
    """Read and validate the registry's text."""
    today = today or date.today()
    try:
        data, where = miniyaml.load(text)
    except miniyaml.YAMLError as err:
        return Registry(problems=[Problem(err.line, '', err.message)])
    if data is None:
        return Registry(problems=[Problem(None, '', 'the file is empty: it needs a "projects:" list')])

    def label(path: tuple) -> str:
        text = path_text(path)
        if len(path) >= 2 and path[0] == 'projects' and isinstance(path[1], int):
            entry = data.get('projects')[path[1]] if isinstance(data, dict) and isinstance(data.get('projects'), list) else None
            repo = entry.get('repository') if isinstance(entry, dict) else None
            if isinstance(repo, str):
                head = f'projects[{path[1]}] ({repo})'
                text = head + text[len(f'projects[{path[1]}]'):]
        return text

    checker = Checker(json.loads(SCHEMA.read_text('utf-8')))
    problems = [Problem(_line(where, e.path), label(e.path), e.message) for e in checker.errors(data)]
    projects = []
    if isinstance(data, dict) and isinstance(data.get('projects'), list):
        seen = {}
        for i, entry in enumerate(data['projects']):
            if not isinstance(entry, dict):
                continue
            repo, added = entry.get('repository'), entry.get('added')
            if isinstance(repo, str):
                if repo.lower() in seen:
                    problems.append(Problem(_line(where, ('projects', i, 'repository')), label(('projects', i, 'repository')),
                                            f'{repo} is already listed as projects[{seen[repo.lower()]}].'))
                else:
                    seen[repo.lower()] = i
            if isinstance(added, str):
                try:
                    if date.fromisoformat(added) > today + timedelta(days=1):
                        problems.append(Problem(_line(where, ('projects', i, 'added')), label(('projects', i, 'added')),
                                                f'"{added}" is in the future. Write the date you add the entry.'))
                except ValueError:
                    pass                                         # the schema already reports it
        if not problems:
            projects = [Project(e['repository'], e['category'], list(e['tags']), e['maintainer_pledge'], e['added'],
                                _line(where, ('projects', i)) or 0) for i, e in enumerate(data['projects'])]
    problems.sort(key=lambda p: (p.line or 0, p.where))
    return Registry(projects, problems)


def load(path: Path = REGISTRY, today: Optional[date] = None) -> Registry:
    return check(Path(path).read_text('utf-8'), today)
