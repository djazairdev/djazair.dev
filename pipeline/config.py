"""Sources, paths and peer groups (PRD §9.1 and §9.3)."""
from __future__ import annotations

from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_DIR / 'data' / 'raw'
DERIVED_DIR = REPO_DIR / 'data' / 'derived'
CACHE_DIR = REPO_DIR / 'data' / 'cache'

SOURCE_REPO = 'github/innovationgraph'
SOURCE_URL = f'https://github.com/{SOURCE_REPO}'
API_URL = 'https://api.github.com'
RAW_URL = 'https://raw.githubusercontent.com'

# The eight files of a release, in data/ of the source repository.
FILES = ('developers', 'git_pushes', 'repositories', 'organizations', 'languages', 'topics', 'licenses',
         'economy_collaborators')

FIRST_QUARTER = (2020, 1)

# Peer groups (§9.3). The Africa ranking group is every African economy with at least
# AFRICA_MIN_ACCOUNTS developer accounts a year before the quarter.
NORTH_AFRICA = ('DZ', 'EG', 'LY', 'MA', 'MR', 'SD', 'TN')
CORE_PEERS = ('MA', 'TN', 'EG', 'NG', 'KE', 'ZA')
AFRICA = ('DZ', 'AO', 'BJ', 'BW', 'BF', 'BI', 'CV', 'CM', 'CF', 'TD', 'KM', 'CG', 'CD', 'CI', 'DJ', 'EG', 'GQ', 'ER',
          'SZ', 'ET', 'GA', 'GM', 'GH', 'GN', 'GW', 'KE', 'LS', 'LR', 'LY', 'MG', 'MW', 'ML', 'MR', 'MU', 'MA', 'MZ',
          'NA', 'NE', 'NG', 'RW', 'ST', 'SN', 'SC', 'SL', 'SO', 'ZA', 'SS', 'SD', 'TZ', 'TG', 'TN', 'UG', 'ZM', 'ZW')
AFRICA_MIN_ACCOUNTS = 20_000
HOME = 'DZ'

# The Innovation Graph also lists the European Union as one economy. In economy_collaborators
# its weight is the sum of the members listed in the same quarter and direction, so rankings of
# partners leave it out.
EU = 'EU'
EU_MEMBERS = ('AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU',
              'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE')

LICENCE = 'CC0-1.0'
LICENCE_URL = 'https://creativecommons.org/publicdomain/zero/1.0/'
ATTRIBUTION = 'Data: GitHub Innovation Graph (CC0)'
