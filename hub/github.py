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
        self.calls = 0                  # requests sent
        self.unchanged = 0              # of which GitHub answered 304 Not Modified
        self.rate: dict = {}            # the rate limit headers of the last answer

    def request(self, method: str, path: str, data=None) -> tuple:
        """(status, parsed JSON or None). Retries server errors; raises GitHubError on rate limits."""
        status, _head, parsed = self.exchange(method, path, data)
        return status, parsed

    def exchange(self, method: str, path: str, data=None, extra: Optional[dict] = None) -> tuple:
        """(status, response headers, parsed JSON or None), as ``request``; ``extra`` adds request
        headers. Counts the calls and keeps the rate limit GitHub last reported."""
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': USER_AGENT, 'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        headers.update(extra or {})
        body = json.dumps(data).encode() if data is not None else None
        if body is not None:
            headers['Content-Type'] = 'application/json'
        for attempt in range(self.tries):
            status, head, raw = self.transport(method, API + path, body, headers)
            self.calls += 1
            self.unchanged += status == 304
            if _header(head, 'X-RateLimit-Remaining'):
                self.rate = {k: _header(head, f'X-RateLimit-{k.title()}') for k in ('limit', 'remaining', 'reset', 'used')}
            if status >= 500 and attempt < self.tries - 1:
                time.sleep(2 * 2 ** attempt)
                continue
            if status in (403, 429) and (_header(head, 'X-RateLimit-Remaining') == '0' or status == 429):
                raise GitHubError('GitHub API rate limit reached; try again later')
            parsed = json.loads(raw) if raw and raw.strip()[:1] in (b'{', b'[') else None
            return status, head, parsed
        raise GitHubError(f'GitHub kept failing for {path}')

    def get_if_changed(self, path: str, etag: Optional[str]) -> tuple:
        """(status, JSON, ETag) for ``path``, asking with the ETag of the last answer. 304 means
        it hasn't changed (no JSON, and no cost against the rate limit); 404 and 409 (an empty
        repository) mean there is nothing there. Other errors raise."""
        status, head, data = self.exchange('GET', path, extra={'If-None-Match': etag} if etag else None)
        if status == 304:
            return 304, None, etag
        if status in (404, 409):
            return status, None, None
        if status >= 400:
            message = data.get('message', '') if isinstance(data, dict) else ''
            raise GitHubError(f'GitHub answered {status} for {path}{": " + message if message else ""}')
        return status, data, _header(head, 'ETag') or None

    def rate_limit(self) -> Optional[dict]:
        """The core REST quota: limit, remaining, reset (epoch seconds), used. Free to ask."""
        status, data = self.request('GET', '/rate_limit')
        if status >= 400 or not isinstance(data, dict):
            return None
        return (data.get('resources') or {}).get('core') or data.get('rate')

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


def _header(head: dict, name: str) -> str:
    """A response header, whatever its case."""
    name = name.lower()
    return next((str(v) for k, v in (head or {}).items() if k.lower() == name), '')


def _repo(repo: str) -> str:
    owner, name = repo.split('/', 1)
    return f'{quote(owner, safe="")}/{quote(name, safe="")}'
