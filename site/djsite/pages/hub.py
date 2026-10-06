"""The Project Hub (ticket #27; PRD §7.2, HUB-04): beginner issues from the listed projects,
the projects themselves, how a first contribution works, and how to get listed.

Everything comes from the snapshot the Hub sync writes every 6 hours (``data/derived/hub/``,
tickets #25 and #26), read once per build (``Site.hub``): only the projects that pass their
health checks, and their issues. Cards show what an issue needs, never who opened it
(AC-HUB-5).

Without JavaScript the whole feed shows. ``hub.js`` reveals the search, the label tabs and
the language, project and age filters, filters the list in place, keeps the filters in the
address so a view can be shared, and announces the count.
"""
from __future__ import annotations

from collections import Counter
from datetime import timezone
from urllib.parse import quote

from .. import components as C
from ..config import REPO_URL
from ..context import Ctx, Page
from ..fmt import date_label, fint, num, plural
from ..icons import icon, mark
from ..markup import Markup, esc, join

BEGINNER = ('good first issue', 'help wanted')
CHECKS = ('licence', 'activity', 'docs', 'issues', 'pledge', 'topic', 'relevance')
WANTED = ('divisions', 'payments', 'languages')
AGES = (('', None), ('7', 7), ('30', 30))
HEALTH_REPORT = f'{REPO_URL}/blob/hub-data/HEALTH.md'
OPEN_PR = f'{REPO_URL}/edit/main/projects.yml'
ISSUE_FORM = f'{REPO_URL}/issues/new?template=hub-listing.yml'
REFRESH_HOURS = 6


def counted(ctx, key: str, n: int, plain: bool = False) -> Markup:
    """``key.<plural category>`` with the count: '6 open issues' / '6 مهام مفتوحة'. ``plain``:
    the figure in the text's face, as hub.js writes it."""
    figure = fint(n, ctx.lang)
    return ctx.t(f'{key}.{plural(n, ctx.lang)}', n=figure if plain else num(figure))


def count_forms(ctx, key: str) -> str:
    """The forms of a counted string as data attributes, for hub.js."""
    return ''.join(f' data-{cat}="{ctx.ta(f"{key}.{cat}", n="{n}")}"' for cat in ('zero', 'one', 'two', 'few', 'many', 'other'))


def kinds(issue: dict) -> list:
    """Which beginner labels the issue carries: gfi, hw or both."""
    names = {label.lower() for label in issue.get('labels', [])}
    return [k for k, label in zip(('gfi', 'hw'), BEGINNER) if label in names]


def ordered_labels(issue: dict) -> list:
    """The beginner labels first, then the project's own, at most four."""
    labels = issue.get('labels', [])
    first = sorted((l for l in labels if l.lower() in BEGINNER), key=lambda l: BEGINNER.index(l.lower()))
    return (first + [l for l in labels if l.lower() not in BEGINNER])[:4]


def _lang_key(issue: dict) -> str:
    return issue.get('language') or '-'


# ---------------------------------------------------------------- hero
def head(ctx, hub) -> Markup:
    lang = ctx.lang
    meta = [(ctx.t('hub.meta_projects'), fint(len(hub.projects), lang)), (ctx.t('hub.meta_issues'), fint(len(hub.issues), lang)),
            (ctx.t('hub.meta_refreshed'), ctx.t('hub.every', n=num(REFRESH_HOURS)))]
    meta_html = ''.join(f'<div><dt>{k}</dt><dd>{num(v) if not isinstance(v, Markup) else v}</dd></div>' for k, v in meta)
    actions = join([C.btn(ctx.t('hub.list'), '#list'), C.btn(ctx.t('hub.contribute'), '#contribute', 'secondary', arrow=False)])
    return Markup(f'''<section class="page-head hub-hero">
<div class="container"><div class="page-head-text">{C.eyebrow(ctx.t('hub.eyebrow'))}
<h1>{ctx.t('hub.title')}</h1>
<p class="lede">{ctx.t('hub.lede')}</p>
<dl class="page-meta">{meta_html}</dl>
<div class="page-actions">{actions}</div></div></div>
</section>''')


# ---------------------------------------------------------------- feed
def card(ctx, issue: dict) -> Markup:
    data = {'lang': _lang_key(issue), 'repo': issue['repo'], 'days': issue['days'], 'kind': ' '.join(kinds(issue))}
    return C.issue_card(ctx, dict(issue, labels=ordered_labels(issue), data=data))


def _option(name: str, value: str, label, n: int, lang: str, checked: bool = False, dot: str = '', mono: bool = False) -> str:
    dot_html = f'<span class="dot dot-{dot}" aria-hidden="true"></span>' if dot else ''
    cls = ' hf-mono' if mono else ''
    return (f'<label class="hf-opt{cls}"><input class="sr-only" type="radio" name="{name}" value="{esc(value)}"'
            f'{" checked" if checked else ""}><span class="hf-name">{dot_html}<span{" dir=ltr" if mono else ""}>{label}</span></span>'
            f'<span class="hf-n num">{fint(n, lang)}</span></label>')


def filters(ctx, issues: list) -> Markup:
    lang = ctx.lang
    by_lang = Counter(_lang_key(i) for i in issues)
    by_repo = Counter(i['repo'] for i in issues)
    langs = sorted(by_lang.items(), key=lambda kv: (kv[0] == '-', -kv[1], kv[0].lower()))
    lang_opts = [_option('lang', '', ctx.t('hub.all_languages'), len(issues), lang, checked=True)]
    for key, n in langs:
        label = ctx.t('hub.other_language') if key == '-' else esc(key)
        lang_opts.append(_option('lang', key, label, n, lang, dot=C.LANG_DOT.get(key, 'neutral') if key != '-' else ''))
    repo_opts = [_option('repo', '', ctx.t('hub.all_projects'), len(issues), lang, checked=True)]
    repo_opts += [_option('repo', repo, esc(repo), n, lang, mono=True)
                  for repo, n in sorted(by_repo.items(), key=lambda kv: (-kv[1], kv[0].lower()))]
    age_opts = [_option('age', value, ctx.t(f'hub.age_{value or "any"}'),
                        sum(1 for i in issues if days is None or i['days'] <= days), lang, checked=not value)
                for value, days in AGES]
    groups = ''.join(f'<fieldset class="hf-group"><legend class="hf-legend">{ctx.t(title)}</legend>{"".join(opts)}</fieldset>'
                     for title, opts in (('hub.language', lang_opts), ('hub.project', repo_opts), ('hub.opened', age_opts)))
    return Markup(f'''<div class="hub-tools" hidden>
<div class="hub-search">{icon("search", 17)}<label class="sr-only" for="hub-q">{ctx.t('hub.search')}</label>
<input type="search" id="hub-q" name="q" placeholder="{ctx.ta('hub.search')}" autocomplete="off" spellcheck="false"></div>
<details class="hf" open><summary class="hf-sum">{icon("filter", 17)}<span class="hf-t">{ctx.t('hub.filters')}</span>
<span class="hf-state num" data-none="{ctx.ta('hub.filters_none')}" data-some="{ctx.ta('hub.filters_some', n='{n}')}">{ctx.t('hub.filters_none')}</span>{icon("chev", 18)}</summary>
<div class="hf-body">{groups}</div></details>
</div>''')


def feed(ctx, hub) -> Markup:
    issues = hub.issues
    note = ctx.t('hub.note', gfi=Markup('<code dir="ltr">good first issue</code>'), hw=Markup('<code dir="ltr">help wanted</code>'),
                 hours=num(REFRESH_HOURS))
    if hub.synced:
        when = hub.synced.astimezone(timezone.utc)
        comma = ', ' if ctx.en else '، '
        stamp = Markup(f'<time datetime="{when:%Y-%m-%dT%H:%MZ}">{esc(date_label(when.date(), ctx.lang, short=ctx.en))}{comma}'
                       f'<span dir="ltr">{when:%H:%M} UTC</span></time>')
        note = Markup(f'{note} {ctx.t("hub.synced", when=stamp)}')
    if not issues:
        empty = Markup(f'<div class="empty-state hub-empty"><span class="empty-icon">{icon("plus", 20)}</span>'
                       f'<div class="empty-text"><h3>{ctx.t("hub.empty_title")}</h3><p>{ctx.t("hub.empty")}</p>'
                       f'<div class="page-actions">{C.btn(ctx.t("hub.list"), "#list", size="s")}</div></div></div>')
        return Markup(f'<section class="hub-feed" id="issues" aria-labelledby="issues-h"><div class="container">'
                      f'<h2 class="sr-only" id="issues-h">{ctx.t("hub.feed_title")}</h2>{empty}'
                      f'<p class="hub-note">{note}</p></div></section>')
    tabs = ''.join(f'<label class="{"mono" if value else ""}"><input class="sr-only" type="radio" name="kind" value="{value}"'
                   f'{" checked" if not value else ""}><span{" dir=ltr" if value else ""}>{text}</span></label>'
                   for value, text in (('', ctx.t('hub.kind_all')), ('gfi', 'good first issue'), ('hw', 'help wanted')))
    cards = join(card(ctx, i) for i in issues)
    return Markup(f'''<section class="hub-feed" id="issues" aria-labelledby="issues-h"><div class="container">
<h2 class="sr-only" id="issues-h">{ctx.t('hub.feed_title')}</h2>
<div class="hub-grid">
{filters(ctx, issues)}
<div class="hub-main">
<div class="hub-panel">
<div class="hp-head">
<p class="hp-count" role="status">{C.issue_icon()}<span class="hp-n"{count_forms(ctx, 'hub.count')}>{counted(ctx, 'hub.count', len(issues), plain=True)}</span></p>
<button type="button" class="hp-clear" hidden>{ctx.t('hub.clear')}</button>
<fieldset class="seg hp-kind" hidden><legend class="sr-only">{ctx.t('hub.kind_legend')}</legend>{tabs}</fieldset>
</div>
<div class="hp-list">{cards}</div>
<div class="hp-empty" hidden><span class="empty-icon">{icon("search", 18)}</span><h3>{ctx.t('hub.no_match_title')}</h3><p>{ctx.t('hub.no_match')}</p></div>
</div>
<p class="hub-note">{note}</p>
</div>
</div>
</div></section>''')


# ---------------------------------------------------------------- how a first contribution works
def steps(ctx) -> Markup:
    cards = join(f'<li class="step card"><span class="step-n num">0{i}</span><h3>{ctx.t(f"hub.step{i}_t")}</h3>'
                 f'<p>{ctx.t(f"hub.step{i}")}</p></li>' for i in (1, 2, 3))
    return C.section('contribute', ctx.t('hub.steps_eyebrow'), ctx.t('hub.steps_title'), Markup(f'<ol class="steps-row">{cards}</ol>'))


# ---------------------------------------------------------------- projects
def _mark(project: dict) -> Markup:
    name = project.get('name') or project['repository']
    if name.split('/')[0].lower() == 'djazairdev':
        return Markup(f'<span class="pj-mark pj-logo" aria-hidden="true">{mark(40)}</span>')
    letter = name.split('/')[-1][:1].upper() or '·'
    return Markup(f'<span class="pj-mark num" aria-hidden="true">{esc(letter)}</span>')


def project_card(ctx, p: dict) -> Markup:
    lang = ctx.lang
    name = p.get('name') or p['repository']
    sub = ctx.t('hub.listed', category=ctx.t(f'hub.category.{p["category"]}'),
                date=Markup(f'<time datetime="{esc(p["added"])}">{esc(date_label(p["added"], lang, short=ctx.en))}</time>'))
    desc = f'<p class="pj-desc" dir="auto">{esc(p["description"])}</p>' if p.get('description') else ''
    tags = ''.join(f'<li class="lbl" dir="ltr">{esc(t.replace("-", " "))}</li>' for t in p.get('tags', []))
    if p.get('status') == 'flagged':
        reason = p['flags'][0]['reason'] if p.get('flags') else 'inactive'
        health = (f'<li class="badge badge-warn">{icon("info", 14, 2)}<span>{ctx.t("hub.flagged", reason=ctx.t(f"hub.reason.{reason}"))}'
                  f'</span></li>')
    else:
        health = f'<li class="badge">{icon("check", 14, 2.4)}<span>{ctx.t("hub.healthy")}</span></li>'
    pledge = f'<li class="badge">{icon("reply", 14, 2)}<span>{ctx.t("hub.pledge")}</span></li>' if p.get('pledge') else ''
    facts = []
    if p.get('language'):
        facts.append(f'<span class="ic-lang"><span class="dot dot-{C.LANG_DOT.get(p["language"], "neutral")}" aria-hidden="true">'
                     f'</span>{esc(p["language"])}</span>')
    if p.get('licence'):
        facts.append(f'<span class="pj-lic num" dir="ltr">{esc(p["licence"])}</span>')
    n = p.get('issues', 0)
    facts.append(f'<a class="pj-issues" href="?repo={quote(name, safe="/")}#issues" data-repo="{esc(name)}">'
                 f'{counted(ctx, "hub.open_issues", n)}</a>')
    return Markup(f'''<li class="pj card">
<div class="pj-head">{_mark(p)}<div class="pj-id"><h3 class="pj-name num" dir="ltr"><a href="{esc(p.get('url') or 'https://github.com/' + name)}">{esc(name).replace('/', '/<wbr>')}</a></h3>
<p class="pj-sub">{sub}</p></div></div>
{desc}{f'<ul class="pj-tags" aria-label="{ctx.ta("hub.tags")}">{tags}</ul>' if tags else ''}
<div class="pj-foot"><ul class="pj-badges">{health}{pledge}</ul><p class="pj-facts">{"".join(facts)}</p></div>
</li>''')


def wanted_card(ctx, key: str) -> Markup:
    return Markup(f'''<li class="pj pj-wanted">
<div class="pj-head"><span class="pj-mark pj-plus" aria-hidden="true">{icon("plus", 18)}</span>
<p class="pj-kind">{ctx.t('hub.wanted')} · {ctx.t(f'hub.want.{key}.category')}</p></div>
<h3 class="pj-title">{ctx.t(f'hub.want.{key}.title')}</h3>
<p class="pj-desc">{ctx.t(f'hub.want.{key}.text')}</p>
<a class="pj-start" href="#list">{ctx.t('hub.start')}<span class="arr">{icon("arrow", 16, 2)}</span></a>
</li>''')


def projects(ctx, hub) -> Markup:
    cards = join([project_card(ctx, p) for p in hub.projects] + [wanted_card(ctx, k) for k in WANTED])
    report = Markup(f'<a href="{HEALTH_REPORT}">{ctx.t("hub.health_report")}</a>')
    note = Markup(f'<p class="hub-note">{ctx.t("hub.projects_note", report=report)}</p>')
    return C.section('projects', ctx.t('hub.projects_eyebrow'), ctx.t('hub.projects_title'),
                     Markup(f'<ul class="pj-grid">{cards}</ul>{note}'), lede=ctx.t('hub.projects_lede'))


# ---------------------------------------------------------------- get listed
def listing(ctx) -> Markup:
    labels = {'gfi': Markup('<bdi>good first issue</bdi>'), 'hw': Markup('<bdi>help wanted</bdi>'),
              'topic': Markup('<bdi>djazairdev</bdi>')}
    checks = C.check_panel(ctx, [(k, ctx.t(f'hub.check.{k}', **labels), True) for k in CHECKS], ctx.t('hub.check_note'))
    code = C.code_block(ctx, 'projects.yml', ['# One entry per project', '- repository: owner/name', '  category: library',
                                              '  tags: [arabic, payments]', '  maintainer_pledge: true', '  added: 2026-10-06'])
    actions = join([C.btn(ctx.t('hub.open_pr'), OPEN_PR), C.btn(ctx.t('hub.issue_form'), ISSUE_FORM, 'secondary', arrow=False)])
    inner = Markup(f'<div class="list-grid">{checks}<div class="list-side">{code}<div class="page-actions">{actions}</div>'
                   f'<p class="hub-note">{ctx.t("hub.list_note")}</p></div></div>')
    return C.section('list', ctx.t('hub.list_eyebrow'), ctx.t('hub.list_title'), inner, lede=ctx.t('hub.list_lede'))


def render(ctx: Ctx) -> Page:
    hub = ctx.site.hub
    body = head(ctx, hub) + feed(ctx, hub) + steps(ctx) + projects(ctx, hub) + listing(ctx)
    script = ctx.site.assets.scripts.get('hub')
    return Page(title=ctx.s('pages.hub.title'), description=ctx.s('pages.hub.description'), body=body,
                scripts=(script,) if script and hub.issues else ())
