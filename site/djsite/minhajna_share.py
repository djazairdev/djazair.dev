"""Minhajna's social card, rendered from approved page copy and original artwork.

The imported logo remains CC BY-SA 4.0. No third-party image, font or script is fetched.
"""
from __future__ import annotations

from .config import I18N_DIR, STATIC_DIR
from .i18n import Catalog
from .markup import esc

STYLE = """
.mh-share { position: absolute; inset: 0; padding: 64px 72px; display: flex;
  flex-direction: column; justify-content: space-between; gap: 24px; }
.mh-share-brand { display: flex; align-items: center; justify-content: flex-start; gap: 24px; align-self: flex-start; }
.mh-share-brand svg { display: block; width: 96px; height: 96px; flex: none; }
.mh-share-brand svg + svg { width: 147px; height: 72px; }
.mh-share h1 { max-width: 1040px; font-size: 60px; line-height: 1.15; }
[lang=ar] .mh-share h1 { font-size: 64px; line-height: 1.4; }
.mh-share-copy { display: flex; flex-direction: column; gap: 18px; }
.mh-share-copy p { font-size: 28px; }
.mh-share-footer { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 24px; }
.mh-share-free { color: var(--bg); background: var(--ink); padding: 12px 24px; border-radius: 28px; font-size: 24px; font-weight: 700; }
.mh-share-url { font-size: 25px; color: var(--ink2); }
"""


def body(lang: str) -> str:
    """Only existing page strings; card copy changes invalidate its Arabic review."""
    catalog = Catalog(I18N_DIR)
    text = lambda key: esc(catalog.lookup(lang, key)[0])
    icon = (STATIC_DIR / 'minhajna/minhajna-icon.svg').read_text('utf-8')
    wordmark = (STATIC_DIR / 'minhajna/minhajna-wordmark-chalk.svg').read_text('utf-8')
    return f'''<main class="mh-share">
<div class="mh-share-brand" dir="rtl">{icon}{wordmark}</div>
<div class="mh-share-copy"><h1>{text('pages.minhajna.title')}</h1><p>{text('minhajna.eyebrow')}</p></div>
<div class="mh-share-footer"><span class="mh-share-free">{text('minhajna.download_note')}</span>
<span class="mh-share-url" dir="ltr">djazair.dev/{lang}/minhajna/</span></div>
</main>'''
