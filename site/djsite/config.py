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
ISSUES_URL = f'{REPO_URL}/issues'

LANGS = ('en', 'ar')
DIRS = {'en': 'ltr', 'ar': 'rtl'}
OTHER = {'en': 'ar', 'ar': 'en'}
OG_LOCALES = {'en': 'en_GB', 'ar': 'ar_DZ'}    # Open Graph: British spelling; Algerian Arabic

THEME_COLOR = '#0E1A15'

# Cloudflare Web Analytics (ticket #32): no cookies, totals only. The build adds the beacon when
# this environment variable holds the site's token (docs/deploy.md#analytics).
ANALYTICS_ENV = 'CLOUDFLARE_WEB_ANALYTICS_TOKEN'
BEACON_URL = 'https://static.cloudflareinsights.com/beacon.min.js'
