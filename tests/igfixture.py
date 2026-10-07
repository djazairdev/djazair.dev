"""A small, made-up Innovation Graph release for the pipeline tests, served by a fake GitHub
so no test touches the network. Values follow simple formulas, so results can be checked by hand."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.config import API_URL, RAW_URL, SOURCE_REPO  # noqa: E402
from pipeline.release import blob_sha  # noqa: E402

# economy: (developer accounts in 2020 Q1, growth per quarter)
ECONOMIES = {
    'DZ': (100_000, 0.05), 'EG': (240_000, 0.05), 'LY': (8_000, 0.04), 'MA': (150_000, 0.04), 'MR': (2_000, 0.06),
    'SD': (15_000, 0.05), 'TN': (90_000, 0.03), 'NG': (170_000, 0.07), 'KE': (90_000, 0.06), 'ZA': (200_000, 0.04),
    'GH': (40_000, 0.05), 'SN': (18_000, 0.08), 'US': (9_000_000, 0.02), 'EU': (7_000_000, 0.02),
}
RATIOS = {'git_pushes': 0.8, 'repositories': 1.5, 'organizations': 0.04}
TOPICS = {'DZ': ['python', 'javascript', 'react'], 'EG': ['python', 'javascript', 'react', 'flutter', 'laravel'],
          'MA': ['python', 'java'], 'TN': ['python'], 'NG': ['python', 'react', 'nodejs', 'flutter'], 'KE': ['python', 'django'],
          'ZA': ['python'], 'US': ['python', 'javascript'], 'EU': ['python', 'javascript']}
LANGUAGES = [('HTML', 'markup', 0.12), ('JavaScript', 'programming', 0.09), ('Python', 'programming', 0.06)]
PARTNERS = {'DZ': [('US', 90), ('EU', 80), ('FR', 40)], 'MA': [('FR', 70), ('US', 60), ('DZ', 30)], 'FR': [('DZ', 50)]}


def quarters(last=(2021, 2)) -> list:
    out, y, q = [], 2020, 1
    while (y, q) <= last:
        out.append((y, q))
        y, q = (y, q + 1) if q < 4 else (y + 1, 1)
    return out


def accounts(code: str, i: int) -> int:
    base, growth = ECONOMIES[code]
    return round(base * (1 + growth) ** i)


def release_files(last=(2021, 2)) -> dict:
    """name -> CSV bytes for the eight files, 2020 Q1 to ``last``."""
    qs = quarters(last)
    files = {}
    for metric, factor in [('developers', 1)] + list(RATIOS.items()):
        rows = [f'{metric},iso2_code,year,quarter']
        rows += [f'{round(accounts(c, i) * factor)},{c},{y},{q}' for i, (y, q) in enumerate(qs) for c in ECONOMIES]
        files[metric] = rows
    files['languages'] = ['num_pushers,language,language_type,iso2_code,year,quarter'] + [
        f'{round(accounts(c, i) * share)},{lang},{kind},{c},{y},{q}'
        for i, (y, q) in enumerate(qs) for c in ECONOMIES for lang, kind, share in LANGUAGES]
    files['topics'] = ['num_pushers,topic,iso2_code,year,quarter'] + [
        f'{100 + 10 * k},{topic},{c},{y},{q}' for (y, q) in qs for c, ts in TOPICS.items() for k, topic in enumerate(ts)]
    files['licenses'] = ['num_pushers,spdx_license,iso2_code,year,quarter'] + [
        f'{round(accounts(c, i) * 0.05)},MIT,{c},{y},{q}' for i, (y, q) in enumerate(qs) for c in ECONOMIES]
    files['economy_collaborators'] = ['weight,source,destination,year,quarter'] + [
        f'{w},{c},{d},{y},{q}' for (y, q) in qs for c, ps in PARTNERS.items() for d, w in ps]
    order = ('developers', 'git_pushes', 'repositories', 'organizations', 'languages', 'topics', 'licenses',
             'economy_collaborators')
    return {name: ('\n'.join(files[name]) + '\n').encode() for name in order}


class FakeGitHub:
    """Answers the URLs ``pipeline.release`` fetches. ``serve`` overrides what a raw download returns."""

    def __init__(self, files: dict, commit: str = 'c0ffee' + '0' * 34, date: str = '2021-09-01T12:00:00Z',
                 message: str = 'release q2 2021 data', serve: dict = None):
        self.files, self.commit, self.date, self.message = files, commit, date, message
        self.serve = serve or {}
        self.calls = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        if url == f'{API_URL}/repos/{SOURCE_REPO}/commits?path=data&per_page=1':
            return json.dumps([{'sha': self.commit, 'commit': {'committer': {'date': self.date},
                                                               'message': self.message + '\n\nDetails.'}}]).encode()
        if url == f'{API_URL}/repos/{SOURCE_REPO}/contents/data?ref={self.commit}':
            return json.dumps([{'name': f'{n}.csv', 'sha': blob_sha(b)} for n, b in self.files.items()]).encode()
        prefix = f'{RAW_URL}/{SOURCE_REPO}/{self.commit}/data/'
        if url.startswith(prefix) and url.endswith('.csv'):
            name = url[len(prefix):-4]
            return self.serve.get(name, self.files[name])
        raise AssertionError(f'unexpected URL: {url}')
