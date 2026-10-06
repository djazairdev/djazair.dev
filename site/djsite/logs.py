"""The changelog and the corrections log (tickets #23 and #24). The Methodology page shows the
latest entries; the Data page shows both in full, at #changelog and #corrections.

The changelog joins ``content/changelog.json`` (changes to the site) with one entry per
published data quarter, read from ``data/derived/*/manifest.json``, so a new release is
logged without anyone writing it. Corrections live in ``content/corrections.json``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from . import data as data_mod
from .config import CONTENT_DIR
from .fmt import date_label, quarter_label
from .icons import icon
from .markdown import Renderer
from .markup import Markup, esc

REPO = 'https://github.com/djazairdev/djazair.dev'


@dataclass
class Entry:
    date: Optional[str]            # YYYY-MM-DD; None until the change is live ("at launch"). Corrections: when fixed
    html: Markup
    kind: str                      # site, data or correction
    link: Optional[str] = None     # the issue that reported a correction
    found: Optional[str] = None    # when a correction's error was found


def _load(name: str) -> list:
    return json.loads((CONTENT_DIR / name).read_text('utf-8'))['entries']


def _md(ctx) -> Renderer:
    return Renderer(link=lambda key, hash_: ctx.url(key, hash=hash_))


def changelog(ctx, root=data_mod.DERIVED_DIR) -> list:
    """Site changes and data releases, newest first (changes not yet live come first)."""
    md = _md(ctx)
    out = [Entry(e['date'], md.inline(e[ctx.lang]), 'site') for e in _load('changelog.json')]
    for m in data_mod.manifests(root):
        text = (f'<strong>{ctx.t("logs.data_title", quarter=quarter_label(m["quarter"], ctx.lang))}</strong> '
                f'{ctx.t("logs.data_text", release=m["release"][:12])}')
        rev = m.get('revisions') or {}
        if rev.get('compared_with'):
            text += ' ' + str(ctx.t('logs.revised', n=rev['changed']) if rev['changed'] else ctx.t('logs.not_revised'))
        out.append(Entry(m['release_date'][:10], Markup(text), 'data'))
    return sorted(out, key=lambda e: e.date or '9999-12-31', reverse=True)


def corrections(ctx) -> list:
    md = _md(ctx)
    found = [Entry(e['fixed'], md.inline(e[ctx.lang]), 'correction', e.get('issue'), e['found']) for e in _load('corrections.json')]
    return sorted(found, key=lambda e: e.date, reverse=True)


def entry_list(ctx, entries: list, empty, limit: Optional[int] = None) -> Markup:
    """Entries as a dated list, or the empty-state line."""
    if not entries:
        return Markup(f'<p class="log-empty">{icon("check", 16)}<span>{empty}</span></p>')
    rows = []
    for e in entries[:limit] if limit else entries:
        when = (f'<time datetime="{e.date}">{esc(date_label(e.date, ctx.lang, short=ctx.en))}</time>' if e.date
                else f'<span class="log-soon">{ctx.t("logs.at_launch")}</span>')
        issue = f' <a href="{esc(e.link)}">{ctx.t("logs.issue")}</a>' if e.link else ''
        found = (f'<span class="log-f">{ctx.t("logs.found", found=date_label(e.found, ctx.lang, short=ctx.en), fixed=date_label(e.date, ctx.lang, short=ctx.en))}</span>'
                 if e.found else '')
        rows.append(f'<li class="log-{e.kind}"><span class="log-d">{when}</span><span class="log-t">{e.html}{issue}{found}</span></li>')
    return Markup(f'<ol class="log">{"".join(rows)}</ol>')


def report_url() -> str:
    return f'{REPO}/issues/new?template=correction.yml'
