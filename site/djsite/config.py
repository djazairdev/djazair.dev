"""Site-wide settings and paths."""
from __future__ import annotations

from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent          # site/
REPO_DIR = SITE_DIR.parent                                   # repository root
STATIC_DIR = SITE_DIR / 'static'
I18N_DIR = SITE_DIR / 'i18n'
DEFAULT_OUT = SITE_DIR / 'dist'
DATA_DIR = REPO_DIR / 'data'
CONTENT_DIR = REPO_DIR / 'content'

SITE_URL = 'https://djazair.dev'
REPO = 'djazairdev/djazair.dev'
REPO_URL = f'https://github.com/{REPO}'
ORG_URL = f'https://github.com/{REPO.split("/")[0]}'
ISSUES_URL = f'{REPO_URL}/issues'

# Hub ideas (ticket #39, PRD HUB-07) live in the "Ideas" category of GitHub Discussions, with the
# form in .github/DISCUSSION_TEMPLATE/ideas.yml. Anyone with a GitHub account votes by upvoting,
# and every quarter the organisation adopts the idea with the most votes (docs/hub-ideas.md).
# Discussions is off until a maintainer turns it on; set HUB_IDEAS to True then, and the Hub
# shows its Ideas section, with the round's top ideas from the Hub sync (hub/ideas.py).
HUB_IDEAS = False
IDEAS_URL = f'{REPO_URL}/discussions/categories/ideas'
NEW_IDEA_URL = f'{REPO_URL}/discussions/new?category=ideas'
IDEAS_BY_VOTES_URL = f'{IDEAS_URL}?discussions_q=is%3Aopen+category%3AIdeas+sort%3Atop'
IDEAS_RESULTS_URL = f'{REPO_URL}/blob/hub-data/ideas.json'      # each round's count, saved by the Hub sync
IDEAS_MIN_VOTES = 10                # the votes an idea needs before it can be adopted
IDEAS_SHOWN = 5                     # the ideas the Hub lists, most votes first

LANGS = ('en', 'ar')
DIRS = {'en': 'ltr', 'ar': 'rtl'}
OTHER = {'en': 'ar', 'ar': 'en'}
OG_LOCALES = {'en': 'en_GB', 'ar': 'ar_DZ'}    # Open Graph: British spelling; Algerian Arabic

THEME_COLOR = '#0E1A15'

# Cloudflare Web Analytics (ticket #32): no cookies, totals only. The build adds the beacon when
# this environment variable holds the site's token (docs/deploy.md#analytics).
ANALYTICS_ENV = 'CLOUDFLARE_WEB_ANALYTICS_TOKEN'
BEACON_URL = 'https://static.cloudflareinsights.com/beacon.min.js'
