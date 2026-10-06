"""Detect, download and archive GitHub Innovation Graph releases (ticket #9; PRD §9.1, §9.5).

A release is the latest commit in github/innovationgraph that touches ``data/``. Its eight
files are archived in ``data/raw/<commit>/`` with ``SHA256SUMS`` and ``release.json``
(commit, date, data quarter, file sizes and checksums). Each download must match the git
hash GitHub lists for the file. An archived release is never overwritten, so running twice
on the same release changes nothing, and every read verifies the checksum first.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Iterator

from .config import API_URL, FILES, RAW_DIR, RAW_URL, SOURCE_REPO

Fetch = Callable[[str], bytes]
USER_AGENT = 'djazair.dev pipeline (+https://github.com/djazairdev/djazair.dev)'


class ArchiveError(Exception):
    """A download or an archive doesn't match its checksum, or a file is missing."""


def fetch(url: str, tries: int = 3) -> bytes:
    """GET ``url``. GitHub API calls use $GITHUB_TOKEN when it is set (higher rate limit)."""
    headers = {'User-Agent': USER_AGENT}
    if url.startswith(API_URL):
        headers['Accept'] = 'application/vnd.github+json'
        if os.environ.get('GITHUB_TOKEN'):
            headers['Authorization'] = f'Bearer {os.environ["GITHUB_TOKEN"]}'
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as err:
            if err.code < 500 or attempt == tries - 1:
                raise
        except OSError:
            if attempt == tries - 1:
                raise
        time.sleep(3 * 2 ** attempt)
    raise AssertionError('unreachable')


def latest(get: Fetch = fetch) -> dict:
    """The newest commit touching data/ in the source repository."""
    commits = json.loads(get(f'{API_URL}/repos/{SOURCE_REPO}/commits?path=data&per_page=1'))
    c = commits[0]
    return {'commit': c['sha'], 'date': c['commit']['committer']['date'],
            'message': c['commit']['message'].split('\n', 1)[0]}


def listing(commit: str, get: Fetch = fetch) -> dict:
    """Git blob hash of every CSV file in data/ at ``commit``."""
    items = json.loads(get(f'{API_URL}/repos/{SOURCE_REPO}/contents/data?ref={commit}'))
    return {i['name'][:-4]: i['sha'] for i in items if i['name'].endswith('.csv')}


def blob_sha(data: bytes) -> str:
    """The hash git gives a file's content (``git hash-object``)."""
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def data_quarter(developers_csv: bytes) -> str:
    rows = csv.DictReader(io.StringIO(developers_csv.decode('utf-8')))
    year, quarter = max((int(r['year']), int(r['quarter'])) for r in rows)
    return f'{year}-Q{quarter}'


def is_archived(commit: str, raw_dir: Path = RAW_DIR) -> bool:
    return (raw_dir / commit / 'release.json').is_file()


def archive(release: dict, raw_dir: Path = RAW_DIR, get: Fetch = fetch) -> tuple:
    """Archive ``release`` (from ``latest()``) unless it already is.
    Returns (folder, True if it was archived now)."""
    commit = release['commit']
    dest = raw_dir / commit
    if is_archived(commit, raw_dir):
        verify(dest)
        return dest, False
    if dest.exists():
        raise ArchiveError(f'{dest} exists but has no release.json; inspect it before archiving again')
    expected = listing(commit, get)
    missing = [name for name in FILES if name not in expected]
    if missing:
        raise ArchiveError(f'release {commit[:12]} has no {", ".join(f + ".csv" for f in missing)}')

    partial = raw_dir / f'.{commit}.partial'
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    try:
        files = {}
        for name in FILES:
            data = get(f'{RAW_URL}/{SOURCE_REPO}/{commit}/data/{name}.csv')
            if blob_sha(data) != expected[name]:
                raise ArchiveError(f'{name}.csv from {commit[:12]} does not match the hash GitHub lists for it')
            (partial / f'{name}.csv').write_bytes(data)
            files[name] = {'file': f'{name}.csv', 'bytes': len(data), 'sha256': sha256(data)}
        (partial / 'SHA256SUMS').write_text(''.join(f'{f["sha256"]}  {f["file"]}\n' for f in files.values()), 'utf-8')
        meta = {**release, 'quarter': data_quarter((partial / 'developers.csv').read_bytes()),
                'source': f'https://github.com/{SOURCE_REPO}/tree/{commit}/data', 'files': files}
        (partial / 'release.json').write_text(json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False) + '\n', 'utf-8')
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    partial.rename(dest)            # the archive appears complete or not at all
    return dest, True


def _sums(folder: Path) -> dict:
    sums = {}
    for line in (folder / 'SHA256SUMS').read_text('utf-8').splitlines():
        digest, name = line.split('  ', 1)
        sums[name] = digest
    return sums


def verify(folder: Path) -> dict:
    """Check every archived file against SHA256SUMS; return release.json."""
    if not (folder / 'release.json').is_file():
        raise ArchiveError(f'{folder} is not an archived release')
    sums = _sums(folder)
    for name in FILES:
        path = folder / f'{name}.csv'
        if f'{name}.csv' not in sums or not path.is_file():
            raise ArchiveError(f'{folder.name[:12]}: {name}.csv is missing')
        if sha256(path.read_bytes()) != sums[f'{name}.csv']:
            raise ArchiveError(f'{folder.name[:12]}: {name}.csv does not match SHA256SUMS')
    return json.loads((folder / 'release.json').read_text('utf-8'))


class Archive:
    """An archived release. Every read verifies the file's checksum."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.meta = verify(self.folder)

    @property
    def commit(self) -> str:
        return self.meta['commit']

    @property
    def quarter(self) -> str:
        return self.meta['quarter']

    def read(self, name: str) -> bytes:
        data = (self.folder / f'{name}.csv').read_bytes()
        if sha256(data) != _sums(self.folder)[f'{name}.csv']:
            raise ArchiveError(f'{self.commit[:12]}: {name}.csv does not match SHA256SUMS')
        return data

    def rows(self, name: str) -> Iterator[dict]:
        yield from csv.DictReader(io.StringIO(self.read(name).decode('utf-8')))


def archives(raw_dir: Path = RAW_DIR) -> list:
    """Every archived release, oldest first."""
    found = [Archive(p) for p in raw_dir.iterdir() if p.is_dir() and not p.name.startswith('.') and is_archived(p.name, raw_dir)]
    return sorted(found, key=lambda a: a.meta['date'])
