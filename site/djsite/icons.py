"""Inline stroke icons (24 × 24 grid, round caps) and the brand mark."""
from __future__ import annotations

import re
from functools import lru_cache

from .config import STATIC_DIR
from .markup import Markup

_PATHS = {
    'arrow': '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    'arrow-ur': '<path d="M7 17 17 7"/><path d="M8 7h9v9"/>',
    'code': '<path d="m8 8-4 4 4 4"/><path d="m16 8 4 4-4 4"/><path d="m14 5-4 14"/>',
    'menu': '<path d="M4 8h16"/><path d="M4 16h16"/>',
    'close': '<path d="m6 6 12 12"/><path d="M18 6 6 18"/>',
    'download': '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
    'share': '<path d="M12 15V4"/><path d="m7 8 5-5 5 5"/><path d="M5 13v6a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-6"/>',
    'embed': '<path d="M9 7 4 12l5 5"/><path d="m15 7 5 5-5 5"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    'chev': '<path d="m6 9 6 6 6-6"/>',
    'check': '<path d="m5 12 4.5 4.5L19 7"/>',
    'x': '<path d="m7 7 10 10"/><path d="M17 7 7 17"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'reply': '<path d="M10 9 5 13l5 4"/><path d="M5 13h9a5 5 0 0 1 5 5v1"/>',
    'globe': '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/>',
    'branch': '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 8v8"/><path d="M18 10c0 4-6 3-11 6"/>',
    'table': '<rect x="4" y="5" width="16" height="14" rx="1.5"/><path d="M4 10h16"/><path d="M10 10v9"/>',
    'plus': '<path d="M12 5v14"/><path d="M5 12h14"/>',
    'search': '<circle cx="11" cy="11" r="6"/><path d="m20 20-4.5-4.5"/>',
    'book': '<path d="M5 5a2 2 0 0 1 2-2h12v16H7a2 2 0 0 0-2 2z"/><path d="M5 19V5"/>',
    'filter': '<path d="M4 6h16"/><path d="M7 12h10"/><path d="M10 18h4"/>',
    'sort': '<path d="m8 9 4-4 4 4"/><path d="m8 15 4 4 4-4"/>',
    'link': '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
}


def icon(name: str, size: int = 18, stroke: float = 1.6, cls: str = 'icon') -> Markup:
    return Markup(
        f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f'{_PATHS[name]}</svg>')


@lru_cache(maxsize=None)
def _mark_inner() -> str:
    svg = (STATIC_DIR / 'favicon.svg').read_text('utf-8')
    inner = svg.split('>', 1)[1].rsplit('</svg>', 1)[0]
    return re.sub(r'<title>.*?</title>', '', inner)


def mark(size: int = 28, cls: str = 'mark') -> Markup:
    """The djazair.dev emblem (decorative: the wordmark beside it carries the name)."""
    return Markup(f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 120 120" aria-hidden="true" '
                  f'focusable="false">{_mark_inner()}</svg>')


def wordmark(cls: str = 'wordmark') -> Markup:
    return Markup(f'<span class="{cls}" lang="en" dir="ltr">djazair<span>.dev</span></span>')
