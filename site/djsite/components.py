"""Shared page components. Each returns ``Markup``; text arguments must already be escaped."""
from __future__ import annotations

from typing import Iterable, Optional

from .icons import icon
from .markup import Markup, esc, join


def eyebrow(text, tag: str = 'p') -> Markup:
    """Small label with the mint square: 'ALGERIA DEVELOPER INDEX · Q1 2026'."""
    return Markup(f'<{tag} class="eyebrow">{text}</{tag}>')


def btn(label, href: str, kind: str = 'primary', size: str = 'm', arrow: bool = True, attrs: str = '') -> Markup:
    """Link styled as a button. ``kind``: primary | secondary. ``size``: m (48 px) | s (40 px)."""
    arr = f'<span class="arr">{icon("arrow", 18, 2)}</span>' if arrow else ''
    sz = ' btn-s' if size == 's' else ''
    return Markup(f'<a class="btn btn-{kind}{sz}" href="{esc(href)}"{attrs}>{label}{arr}</a>')


def page_head(*, eyebrow_text, title, lede=None, meta: Optional[Iterable] = None, actions=None) -> Markup:
    """The top of an inner page: eyebrow, h1, lede, optional meta row and actions."""
    meta_html = ''
    if meta:
        meta_html = ('<dl class="page-meta">'
                     + ''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in meta) + '</dl>')
    lede_html = f'<p class="lede">{lede}</p>' if lede else ''
    actions_html = f'<div class="page-actions">{join(actions)}</div>' if actions else ''
    return Markup(f'''<section class="page-head">
<div class="container page-head-row">
<div class="page-head-text">{eyebrow(eyebrow_text)}
<h1>{title}</h1>
{lede_html}{meta_html}</div>
{actions_html}
</div>
</section>''')
