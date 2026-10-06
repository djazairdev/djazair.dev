"""A small GitHub REST client for the Hub (standard library only).

Reads use ``GITHUB_TOKEN`` (or ``GH_TOKEN``) when it is set, for the higher rate limit;
public data needs no token. Comments need a token that may write issues and pull requests.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable, Optional
from urllib.parse import quote

API = 'https://api.github.com'
USER_AGENT = 'djazair.dev hub (+https://github.com/djazairdev/djazair.dev)'


class GitHubError(Exception):
    """GitHub didn't answer as expected (rate limit, outage, no permission)."""


Transport = Callable[[str, str, Optional[bytes], dict], tuple]       # (method, url, body, headers) -> (status, headers, bytes)


def urllib_transport(method: str, url: str, body: Optional[bytes], headers: dict) -> tuple:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers or {}), err.read() or b''


class GitHub:
    def __init__(self, token: Optional[str] = None, transport: Transport = urllib_transport, tries: int = 3):
        self.token = token if token is not None else (os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or '')
        self.transport = transport
        self.tries = tries

    def request(self, method: str, path: str, data=None) -> tuple:
        """(status, parsed JSON or None). Retries server errors; raises GitHubError on rate limits."""
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': USER_AGENT, 'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        body = json.dumps(data).encode() if data is not None else None
        if body is not None:
            headers['Content-Type'] = 'application/json'
        for attempt in range(self.tries):
            status, head, raw = self.transport(method, API + path, body, headers)
            if status >= 500 and attempt < self.tries - 1:
                time.sleep(2 * 2 ** attempt)
                continue
            if status in (403, 429) and (str(head.get('X-RateLimit-Remaining', head.get('x-ratelimit-remaining', ''))) == '0'
                                         or status == 429):
                raise GitHubError('GitHub API rate limit reached; try again later')
            parsed = json.loads(raw) if raw and raw.strip()[:1] in (b'{', b'[') else None
            return status, parsed
        raise GitHubError(f'GitHub kept failing for {path}')

    def get(self, path: str):
        """The JSON at ``path``, or None if it doesn't exist (404). Other errors raise."""
        status, data = self.request('GET', path)
        if status == 404:
            return None
        if status >= 400:
            message = data.get('message', '') if isinstance(data, dict) else ''
            raise GitHubError(f'GitHub answered {status} for {path}{": " + message if message else ""}')
        return data

    # ---- what the checks read
    def repository(self, repo: str):
        return self.get(f'/repos/{_repo(repo)}')

    def last_commit(self, repo: str, branch: str):
        status, data = self.request('GET', f'/repos/{_repo(repo)}/commits?sha={quote(branch, safe="")}&per_page=1')
        if status == 409:                                       # an empty repository
            return None
        if status >= 400:
            raise GitHubError(f'GitHub answered {status} for the commits of {repo}')
        return data[0] if data else None

    def community(self, repo: str):
        return self.get(f'/repos/{_repo(repo)}/community/profile')

    def labelled_issues(self, repo: str, label: str) -> list:
        """Open issues (not pull requests) with ``label``."""
        out, page = [], 1
        while True:
            data = self.get(f'/repos/{_repo(repo)}/issues?state=open&labels={quote(label, safe="")}&per_page=100&page={page}') or []
            out += [i for i in data if 'pull_request' not in i]
            if len(data) < 100 or page >= 5:
                return out
            page += 1

    # ---- comments
    def upsert_comment(self, repo: str, number: int, marker: str, body: str) -> str:
        """Edit the comment that holds ``marker`` on issue or pull request ``number``, or add one.
        Returns 'updated' or 'created'."""
        page = 1
        while True:
            comments = self.get(f'/repos/{_repo(repo)}/issues/{number}/comments?per_page=100&page={page}') or []
            for c in comments:
                if marker in (c.get('body') or '') and (c.get('user') or {}).get('type') == 'Bot':
                    self._write('PATCH', f'/repos/{_repo(repo)}/issues/comments/{c["id"]}', body)
                    return 'updated'
            if len(comments) < 100:
                break
            page += 1
        self._write('POST', f'/repos/{_repo(repo)}/issues/{number}/comments', body)
        return 'created'

    def _write(self, method: str, path: str, body: str) -> None:
        status, data = self.request(method, path, {'body': body})
        if status >= 400:
            message = data.get('message', '') if isinstance(data, dict) else ''
            raise GitHubError(f'could not write the comment ({status}{": " + message if message else ""})')


def _repo(repo: str) -> str:
    owner, name = repo.split('/', 1)
    return f'{quote(owner, safe="")}/{quote(name, safe="")}'
