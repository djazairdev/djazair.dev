"""The Hub's localisation page (ticket #40; PRD HUB-08): teams that translate open-source
software into Arabic and Tamazight on Pontoon, Weblate and Crowdin, how to join one, and why
the Index doesn't see this work (PRD §9.4).

The teams come from ``content/localisation.json`` (its ``about`` explains the fields).
``site/tools/links.py`` opens every link, and the Link check workflow runs it every week.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from .. import components as C
from ..config import CONTENT_DIR, REPO_URL
from ..context import Ctx, Page
from ..fmt import date_label, fint
from ..icons import icon
from ..markdown import Renderer
from ..markup import Markup, esc, join

PATH = CONTENT_DIR / 'localisation.json'
PLATFORMS = {'pontoon': 'Pontoon', 'weblate': 'Weblate', 'crowdin': 'Crowdin'}
LANGUAGES = ('ar', 'kab', 'zgh')                 # Arabic; Kabyle; Tamazight in Tifinagh (the Moroccan standard)
GROUPS = (('arabic', ('ar',)), ('tamazight', ('kab', 'zgh')))
EDIT_URL = f'{REPO_URL}/edit/main/content/localisation.json'
ISSUE_URL = f'{REPO_URL}/issues/new?title=Translation%20team%3A%20'


class LocalisationError(Exception):
    """content/localisation.json has a mistake; the message says which and where."""


def load(path: Path = PATH) -> dict:
    """The list, checked: every team has a name, a known platform, text in both languages and
    at least one https link per language it lists."""
    data = json.loads(Path(path).read_text('utf-8'))
    names = set()
    for i, team in enumerate(data.get('teams', [])):
        where = f'{Path(path).name}: teams[{i}] ({team.get("name", "?")})'
        missing = [k for k in ('name', 'platform', 'en', 'ar', 'links') if not team.get(k)]
        if missing:
            raise LocalisationError(f'{where} has no {", ".join(missing)}')
        if team['name'] in names:
            raise LocalisationError(f'{where} is listed twice')
        names.add(team['name'])
        if team['platform'] not in PLATFORMS:
            raise LocalisationError(f'{where}: platform must be one of {", ".join(PLATFORMS)}')
        for code, url in team['links'].items():
            if code not in LANGUAGES:
                raise LocalisationError(f'{where}: links.{code} isn’t a language this page lists ({", ".join(LANGUAGES)})')
            if urlsplit(url).scheme != 'https' or not urlsplit(url).netloc:
                raise LocalisationError(f'{where}: links.{code} must be an https address')
    if not names:
        raise LocalisationError(f'{Path(path).name} lists no teams')
    date_label(data['checked'], 'en')            # a real date, or this raises
    return data


def links(data: dict) -> list:
    """Every (team name, language, url), in the order of the file."""
    return [(t['name'], code, url) for t in data['teams'] for code, url in t['links'].items()]


# ---------------------------------------------------------------- page
def head(ctx, data) -> Markup:
    checked = data['checked']
    meta = [(ctx.t('localisation.meta_projects'), fint(len(data['teams']), ctx.lang)),
            (ctx.t('localisation.meta_links'), fint(len(links(data)), ctx.lang)),
            (ctx.t('localisation.meta_checked'),
             Markup(f'<time datetime="{esc(checked)}">{esc(date_label(checked, ctx.lang, short=ctx.en))}</time>'))]
    actions = [C.btn(ctx.t('localisation.go_arabic'), '#arabic'),
               C.btn(ctx.t('localisation.go_tamazight'), '#tamazight', 'secondary', arrow=False)]
    meta_html = ''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in meta)
    return Markup(f'''<section class="page-head hub-hero lz-hero">
<div class="container"><div class="page-head-text">{C.eyebrow(ctx.t('localisation.eyebrow'))}
<h1>{ctx.t('localisation.title')}</h1>
<p class="lede">{ctx.t('localisation.lede')}</p>
<dl class="page-meta">{meta_html}</dl>
<div class="page-actions">{join(actions)}</div></div></div>
</section>''')


def card(ctx, team: dict, codes: tuple, md: Renderer) -> Markup:
    """One project: what is translated there, and a link to each of its teams in ``codes``."""
    items = join(f'<li><a class="pj-start lz-link" href="{esc(url)}" hreflang="{code}">{ctx.t(f"localisation.team.{code}")}'
                 f'<span class="arr">{icon("arrow-ur", 16, 2)}</span></a></li>'
                 for code, url in team['links'].items() if code in codes)
    letter = esc(team['name'][:1].upper())
    return Markup(f'''<li class="pj card lz">
<div class="pj-head"><span class="pj-mark num" aria-hidden="true">{letter}</span><div class="pj-id">
<h3 class="pj-name lz-name" dir="ltr">{esc(team['name'])}</h3>
<p class="pj-sub">{ctx.t('localisation.on', platform=Markup(f'<bdi>{PLATFORMS[team["platform"]]}</bdi>'))}</p></div></div>
<p class="pj-desc">{md.inline(team[ctx.lang])}</p>
<ul class="lz-links" role="list">{items}</ul>
</li>''')


def group(ctx, data, key: str, codes: tuple, md: Renderer) -> Markup:
    cards = join(card(ctx, t, codes, md) for t in data['teams'] if any(c in t['links'] for c in codes))
    return C.section(key, ctx.t(f'localisation.{key}_eyebrow'), ctx.t(f'localisation.{key}_title'),
                     Markup(f'<ul class="pj-grid lz-grid" role="list">{cards}</ul>'), lede=ctx.t(f'localisation.{key}_lede'))


def steps(ctx) -> Markup:
    cards = join(f'<li class="step card"><span class="step-n num">0{i}</span><h3>{ctx.t(f"localisation.step{i}_t")}</h3>'
                 f'<p>{ctx.t(f"localisation.step{i}")}</p></li>' for i in (1, 2, 3))
    return C.section('start', ctx.t('localisation.steps_eyebrow'), ctx.t('localisation.steps_title'),
                     Markup(f'<ol class="steps-row">{cards}</ol>'))


def suggest(ctx, data) -> Markup:
    """The note PRD HUB-08 asks for, and how to add a team."""
    limits = Markup(f'<a href="{ctx.url("methodology", hash="limitations")}">{ctx.t("localisation.limits")}</a>')
    note = (f'<aside class="callout lz-note" role="note"><span class="callout-i">{icon("info", 20)}</span><div>'
            f'<h3>{ctx.t("localisation.index_t")}</h3><p>{ctx.t("localisation.index", limits=limits)}</p></div></aside>')
    actions = join([C.btn(ctx.t('localisation.edit'), EDIT_URL),
                    C.btn(ctx.t('localisation.issue'), ISSUE_URL, 'secondary', arrow=False)])
    checked = Markup(f'<time datetime="{esc(data["checked"])}">{esc(date_label(data["checked"], ctx.lang))}</time>')
    rules = ctx.t('localisation.rules', file=Markup('<code dir="ltr">content/localisation.json</code>'))
    side = (f'<div class="list-side"><p class="lz-rules">{rules}</p>'
            f'<div class="page-actions">{actions}</div><p class="hub-note">{ctx.t("localisation.checked", date=checked)}</p></div>')
    return C.section('suggest', ctx.t('localisation.suggest_eyebrow'), ctx.t('localisation.suggest_title'),
                     Markup(f'<div class="list-grid">{side}{note}</div>'))


def render(ctx: Ctx) -> Page:
    data = load()
    md = Renderer(link=lambda key, hash_: ctx.url(key, hash=hash_))
    body = head(ctx, data) + join(group(ctx, data, key, codes, md) for key, codes in GROUPS) + steps(ctx) + suggest(ctx, data)
    return Page(title=ctx.s('pages.localisation.title'), description=ctx.s('pages.localisation.description'), body=body)
