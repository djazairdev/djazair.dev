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
