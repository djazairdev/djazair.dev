"""Page-specific human reviews, without publishing an entire unreviewed language.

A review covers exactly the page's visible strings, metadata and shared shell labels.
Changing any covered translation requires a fresh human approval before production builds.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .config import CONTENT_DIR, LANGS

REVIEW_FILE = CONTENT_DIR / 'page-reviews.json'
SCOPES = {'minhajna': ('minhajna.', 'pages.minhajna.', 'a11y.skip', 'a11y.language')}


def digest(catalog, page: str, lang: str) -> str:
    """Fingerprint reviewed copy; missing translations cannot be approved by fallback."""
    if page not in SCOPES or lang not in LANGS:
        raise ValueError('Unknown page or language in page review')
    keys = [key for key in catalog.flat['en'] if any(key.startswith(prefix) for prefix in SCOPES[page])]
    values = {key: catalog.flat[lang].get(key) for key in sorted(keys)}
    if not values or any(value in (None, '', []) for value in values.values()):
        raise ValueError(f'{page}/{lang} has untranslated review strings')
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def reviewed_pages(catalog, published: tuple, path: Path = REVIEW_FILE) -> dict:
    """Accept named human approvals only while the approved text still matches."""
    records = json.loads(path.read_text('utf-8'))
    if not isinstance(records, dict):
        raise ValueError('Page reviews must be an object')
    approved = {}
    for page, languages in records.items():
        if page not in SCOPES or not isinstance(languages, dict):
            raise ValueError('Unknown page or invalid language reviews')
        for lang, record in languages.items():
            if lang not in LANGS or not isinstance(record, dict):
                raise ValueError('Invalid page review language or record')
            if not isinstance(record.get('reviewer'), str) or not record['reviewer'].strip():
                raise ValueError('A page review needs its human reviewer')
            if not isinstance(record.get('date'), str):
                raise ValueError('A page review needs an ISO date')
            if date.fromisoformat(record['date']) > date.today():
                raise ValueError('A page review cannot be dated in the future')
            if lang in published:
                continue
            if record.get('strings_sha256') != digest(catalog, page, lang):
                raise ValueError(f'{page}/{lang} changed since human review; obtain a new approval')
            approved.setdefault(page, []).append(lang)
    return {page: tuple(languages) for page, languages in approved.items()}
