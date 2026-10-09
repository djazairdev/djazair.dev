"""Verified editorial links; distinct from the Hub's opted-in project registry."""
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from .config import CONTENT_DIR

PATH = CONTENT_DIR / 'community-projects.json'


def load(path: Path = PATH) -> dict:
    data = json.loads(Path(path).read_text('utf-8'))
    date.fromisoformat(data['checked'])
    seen = set()
    for project in data['projects']:
        repo = project['repository']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or repo.lower() in seen:
            raise ValueError(f'Invalid or duplicate discovery repository: {repo}')
        seen.add(repo.lower())
        for key in ('name', 'en', 'ar', 'language', 'licence'):
            if not project.get(key):
                raise ValueError(f'{repo}: missing {key}')
        datetime.fromisoformat(project['last_commit'].replace('Z', '+00:00'))
        url = urlsplit(project['contribute'])
        if url.scheme != 'https' or url.netloc != 'github.com' or not (
                url.path == '/' + repo or url.path.startswith('/' + repo + '/')):
            raise ValueError(f'{repo}: contribution link must open this GitHub repository')
    return data


def links(data: dict) -> list:
    return [(p['repository'], 'https://github.com/' + p['repository'], p['contribute'])
            for p in data['projects']]
