"""GitHub's GDC26 rankings (ticket #38; PRD IDX-11 and Appendix A.6).

For the Global Digital Collaboration Conference in Geneva (1–3 September 2026), GitHub added
two one-off files to github/innovationgraph, in ``supplementary_data/
git_pushes_weighted_by_profile_economy/``: git pushes from Q3 2025 to Q2 2026, weighted to
correct for VPN use, for the 30 economies with the most, and per 1,000 working-age people for
the ten highest in each region. GitHub notes they can't be reproduced from the quarterly
files: the weights come from the locations on developers' profiles.

``archive`` keeps the files in ``data/raw/gdc26/`` with ``SHA256SUMS`` and ``source.json``,
each checked against the git hash GitHub lists, like a release. ``estimate`` is what
djazair.dev can compute from the quarterly files instead: unweighted pushes over the same four
quarters, with a quarter not released yet taken as equal to the latest one, per 1,000
working-age people of the World Bank year GitHub used.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import API_URL, RAW_DIR, RAW_URL, SOURCE_REPO
from .release import ArchiveError, Fetch, blob_sha, fetch, sha256

COMMIT = 'a5aedb7585dc5908a46ab90d33113044046cd7b5'   # "add supplementary data", 31 August 2026
DATE = '2026-08-31'                                   # the commit's date: when GitHub published the files
FOLDER = 'supplementary_data/git_pushes_weighted_by_profile_economy'
FILES = ('README.md', 'git_pushes_weighted_by_profile_economy.csv', 'git_pushes_weighted_by_profile_economy_per_capita.csv')
WORLD, PER_CAPITA = FILES[1], FILES[2]
DIR = RAW_DIR / 'gdc26'

QUARTERS = ((2025, 3), (2025, 4), (2026, 1), (2026, 2))      # the four quarters GitHub summed
POPULATION_YEAR = 2025                                        # the World Bank year of GitHub's working-age population
REGION = 'Africa'


def archive(dest: Path = DIR, get: Fetch = fetch, commit: str = COMMIT) -> tuple:
    """Archive the files unless they already are. Returns (folder, True if archived now)."""
    if (dest / 'source.json').is_file():
        verify(dest)
        return dest, False
    if dest.exists():
        raise ArchiveError(f'{dest} exists but has no source.json; inspect it before archiving again')
    listing = {i['name']: i['sha'] for i in json.loads(get(f'{API_URL}/repos/{SOURCE_REPO}/contents/{FOLDER}?ref={commit}'))}
    missing = [name for name in FILES if name not in listing]
    if missing:
        raise ArchiveError(f'{FOLDER} at {commit[:12]} has no {", ".join(missing)}')
    partial = dest.parent / f'.{dest.name}.partial'
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    try:
        files = {}
        for name in FILES:
            data = get(f'{RAW_URL}/{SOURCE_REPO}/{commit}/{FOLDER}/{name}')
            if blob_sha(data) != listing[name]:
                raise ArchiveError(f'{name} from {commit[:12]} does not match the hash GitHub lists for it')
            (partial / name).write_bytes(data)
            files[name] = {'bytes': len(data), 'sha256': sha256(data)}
        (partial / 'SHA256SUMS').write_text(''.join(f'{f["sha256"]}  {name}\n' for name, f in files.items()), 'utf-8')
        meta = {'commit': commit, 'source': f'https://github.com/{SOURCE_REPO}/tree/{commit}/{FOLDER}', 'licence': 'CC0-1.0',
                'files': files}
        (partial / 'source.json').write_text(json.dumps(meta, indent=2, sort_keys=True) + '\n', 'utf-8')
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    partial.rename(dest)
    return dest, True


def verify(folder: Path = DIR) -> dict:
    """Check every archived file against SHA256SUMS; return source.json."""
    if not (folder / 'source.json').is_file():
        raise ArchiveError(f'{folder} is not an archive of the GDC26 files: run `python3 -m pipeline gdc26`')
    sums = dict(reversed(line.split('  ', 1)) for line in (folder / 'SHA256SUMS').read_text('utf-8').splitlines())
    for name in FILES:
        path = folder / name
        if name not in sums or not path.is_file():
            raise ArchiveError(f'gdc26: {name} is missing')
        if sha256(path.read_bytes()) != sums[name]:
            raise ArchiveError(f'gdc26: {name} does not match SHA256SUMS')
    return json.loads((folder / 'source.json').read_text('utf-8'))


@dataclass(frozen=True)
class Entry:
    rank: int
    economy: str
    region: str               # ICANN region, as GitHub gives it
    pushes: int
    working_age: Optional[int] = None
    per_1k: Optional[float] = None


class GDC26:
    """The archived lists: ``africa``, GitHub's ten highest in Africa per 1,000 working-age
    people; ``world``, the 30 economies with the most pushes."""

    def __init__(self, folder: Path = DIR):
        self.folder = Path(folder)
        self.meta = verify(self.folder)
        rows = lambda name: list(csv.DictReader(io.StringIO((self.folder / name).read_text('utf-8'))))
        self.africa = sorted((Entry(int(r['rank_d5_by_icann_region']), r['classified_iso2_code'], r['icann_region_name'],
                                    int(r['git_pushes']), int(r['working_age_population']),
                                    float(r['git_pushes_per_1k_working_age_population']))
                              for r in rows(PER_CAPITA) if r['icann_region_name'] == REGION), key=lambda e: e.rank)
        self.world = sorted((Entry(int(r['rank_pushes']), r['classified_iso2_code'], r['icann_region_name'], int(r['pushes']))
                             for r in rows(WORLD)), key=lambda e: e.rank)

    @property
    def commit(self) -> str:
        return self.meta['commit']

    @property
    def source(self) -> str:
        return self.meta['source']


@dataclass(frozen=True)
class Estimate:
    economy: str
    quarters: tuple            # pushes in each of QUARTERS
    assumed: int               # how many of them repeat the latest released quarter
    working_age: Optional[int]
    year: int = POPULATION_YEAR

    @property
    def pushes(self) -> int:
        return sum(self.quarters)

    @property
    def per_1k(self) -> Optional[float]:
        return self.pushes / self.working_age * 1000 if self.working_age else None


def estimate(code: str, pushes: dict, released: list, working_age: dict) -> Optional[Estimate]:
    """djazair.dev's estimate for ``code``: ``pushes`` {(code, (year, quarter)): pushes} from the
    quarterly files, ``released`` their quarters, ``working_age`` {code: {year: people}}. None
    when the data doesn't reach the first of the four quarters."""
    latest = max(q for q in released if q <= QUARTERS[-1]) if released else None
    if latest is None or latest < QUARTERS[0] or (code, latest) not in pushes:
        return None
    values, assumed = [], 0
    for q in QUARTERS:
        if q in released:
            if (code, q) not in pushes:
                return None
            values.append(pushes[(code, q)])
        else:
            values.append(pushes[(code, latest)])
            assumed += 1
    people = working_age.get(code, {}).get(str(POPULATION_YEAR))
    return Estimate(code, tuple(values), assumed, people)
