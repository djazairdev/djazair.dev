"""Meetups (ticket #43, PRD D11): small, free meetups in cafés in Algerian cities. They are
organised on founders.coffee, which has its own accounts, RSVPs and hosts, so this page says
what a meetup is and how to host one, and links there to find or host one. It copies no
meetups and no names, so it never goes out of date.

Where it links comes from ``content/meetups/meetups.json``; ``site/tools/links.py`` opens
those links every week. docs/meetups.md explains the move from founders.coffee.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from .. import components as C
from ..config import CONTENT_DIR, LANGS
from ..context import Ctx, Page
from ..fmt import date_label
from ..icons import icon
from ..markup import Markup, esc, join

PATH = CONTENT_DIR / 'meetups' / 'meetups.json'
LINKS = ('find', 'host', 'terms', 'privacy')


class MeetupsError(Exception):
    """content/meetups/meetups.json has a mistake; the message says which."""


def load(path: Path = PATH) -> dict:
    data = json.loads(Path(path).read_text('utf-8'))
    where = Path(path).name
    for key in ('platform', 'url', 'title', 'links', 'checked'):
        if not data.get(key):
            raise MeetupsError(f'{where} has no {key}')
    parts = urlsplit(data['url'])
    if parts.scheme != 'https' or not parts.netloc or parts.path not in ('', '/'):
        raise MeetupsError(f'{where}: url must be an https address with no path')
    for key in LINKS:
        link = data['links'].get(key, '')
        if not link.startswith('/{lang}/'):
            raise MeetupsError(f'{where}: links.{key} must be a path that starts with /{{lang}}/')
    date_label(data['checked'], 'en')            # a real date, or this raises
    return data


def link(data: dict, key: str, lang: str) -> str:
    return data['url'].rstrip('/') + data['links'][key].replace('{lang}', lang)


def links(data: dict) -> list:
    """Every (name, language, url) the page links to."""
    return [(key, lang, link(data, key, lang)) for key in LINKS for lang in LANGS]


# ---------------------------------------------------------------- page
def head(ctx, data) -> Markup:
    actions = [C.btn(ctx.t('meetups.find'), link(data, 'find', ctx.lang), out=True),
               C.btn(ctx.t('meetups.host'), link(data, 'host', ctx.lang), 'secondary', out=True)]
    return Markup(f'''<section class="page-head hub-hero mt-hero">
<div class="container"><div class="page-head-text">{C.eyebrow(ctx.t('meetups.eyebrow'))}
<h1>{ctx.t('meetups.title')}</h1>
<p class="lede">{ctx.t('meetups.lede', platform=Markup(f'<bdi>{esc(data["platform"])}</bdi>'))}</p>
<div class="page-actions">{join(actions)}</div></div></div>
</section>''')


def cards(ctx, prefix: str, numbered: bool) -> Markup:
    """Three cards: ``meetups.<prefix>1_t`` and ``<prefix>1`` …, numbered when they are steps."""
    items = []
    for i in (1, 2, 3):
        n = f'<span class="step-n num">0{i}</span>' if numbered else ''
        items.append(f'<li class="step card">{n}<h3>{ctx.t(f"meetups.{prefix}{i}_t")}</h3><p>{ctx.t(f"meetups.{prefix}{i}")}</p></li>')
    return Markup(f'<ol class="steps-row">{join(items)}</ol>' if numbered else f'<ul class="steps-row" role="list">{join(items)}</ul>')


def what(ctx) -> Markup:
    return C.section('what', ctx.t('meetups.what_eyebrow'), ctx.t('meetups.what_title'), cards(ctx, 'what', False))


def host(ctx, data) -> Markup:
    action = Markup(f'<div class="mt-actions">{C.btn(ctx.t("meetups.host_cta"), link(data, "host", ctx.lang), out=True)}</div>')
    return C.section('host', ctx.t('meetups.host_eyebrow'), ctx.t('meetups.host_title'), cards(ctx, 'step', True) + action,
                     lede=ctx.t('meetups.host_lede'))


def bring(ctx) -> Markup:
    """What djazair.dev brings to a table: a first issue, and the quarter's numbers."""
    items = join(f'<li><a class="card mt-card" href="{href}"><h3>{ctx.t(f"meetups.bring_{key}_t")}'
                 f'<span class="arr">{icon("arrow", 18, 2)}</span></h3><p>{ctx.t(f"meetups.bring_{key}")}</p></a></li>'
                 for key, href in (('hub', ctx.url('hub')), ('report', ctx.url('reports'))))
    return C.section('bring', ctx.t('meetups.bring_eyebrow'), ctx.t('meetups.bring_title'),
                     Markup(f'<ul class="mt-bring" role="list">{items}</ul>'))


def note(ctx, data) -> Markup:
    """founders.coffee is another site, with its own accounts, terms and privacy policy."""
    terms = Markup(f'<a href="{esc(link(data, "terms", ctx.lang))}">{ctx.t("meetups.terms")}</a>')
    privacy = Markup(f'<a href="{esc(link(data, "privacy", ctx.lang))}">{ctx.t("meetups.privacy")}</a>')
    platform = Markup(f'<bdi>{esc(data["platform"])}</bdi>')
    return Markup(f'''<section class="section section-s" id="note" aria-label="{ctx.ta('meetups.note_t', platform=data['platform'])}">
<div class="container"><aside class="callout mt-note" role="note"><span class="callout-i">{icon('info', 20)}</span><div>
<h3>{ctx.t('meetups.note_t', platform=platform)}</h3><p>{ctx.t('meetups.note', platform=platform, terms=terms, privacy=privacy)}</p>
</div></aside></div>
</section>''')


def render(ctx: Ctx) -> Page:
    data = load()
    body = head(ctx, data) + what(ctx) + host(ctx, data) + bring(ctx) + note(ctx, data)
    return Page(title=ctx.s('pages.meetups.title'), description=ctx.s('pages.meetups.description'), body=body)
