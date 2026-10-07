"""Methodology (ticket #23; Methodology boards in docs/design; PRD IDX-12, IDX-14, §9).

The words live in ``content/methodology/<lang>.md``; this module draws them: a numbered
section per ``##`` heading, a table of contents (sticky beside the text on wide screens, a
disclosure on phones), and a component for each ``:::`` block. Figures in the text are
``{{name}}`` values computed here from the derived data, and the worked example recomputes
Algeria's ratios from the counts in the published peers table, so the page stays true when
the data changes.
"""
from __future__ import annotations

import datetime as dt
import re

from .. import components as C
from .. import logs
from ..config import CONTENT_DIR
from ..context import Ctx, Page
from ..fmt import date_label, fdec, fint, fpct, num, quarter_label
from ..icons import icon
from ..markdown import Renderer, items, paragraphs, sections
from ..markup import Markup, esc, join
from ..scorecard import AFRICA_MIN_ACCOUNTS, CORE_PEERS
from . import overview

REPO = 'https://github.com/djazairdev/djazair.dev'
CONTACT = 'contact@djazair.dev'
GROUP_ORDER = ('north_africa', 'core_peers', 'africa')


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def days_text(n: int, lang: str) -> str:
    """'83 days' / '83 يومًا' (Arabic counted nouns change with the number)."""
    if lang == 'en':
        return f'{n} day' if n == 1 else f'{n} days'
    if n == 1:
        return 'يوم واحد'
    if n == 2:
        return 'يومان'
    if 3 <= n % 100 <= 10:
        return f'{n} أيام'
    if 11 <= n % 100 <= 99:
        return f'{n} يومًا'
    return f'{n} يوم'


def values(ctx) -> dict:
    """The {{name}} values the content uses, from the data."""
    data = ctx.site.data
    lang = ctx.lang
    ind = {(r['economy'], r['quarter']): r for r in data.rows('indicators')}
    q = data.quarter
    year, n = q.split('-Q')
    before = f'{int(year) - 1}-Q{n}'

    def pushes_growth(code: str):
        now, then = ind.get((code, q)), ind.get((code, before))
        if not (now and then and now['pushes_per_account'] and then['pushes_per_account']):
            return '—'
        return num(fpct(now['pushes_per_account'] * now['accounts'] / (then['pushes_per_account'] * then['accounts']) - 1, 0, lang))

    rev = data.manifest.get('revisions') or {}
    revisions = ''
    if rev.get('compared_with'):
        revisions = ctx.t('methodology.revisions_some', n=rev['changed']) if rev['changed'] else ctx.t('methodology.revisions_none')
    africa = next(r for r in data.rows('groups') if r['group'] == 'africa' and r['quarter'] == q)
    return {
        'quarter': _q(ctx, q),
        'first_quarter': _q(ctx, data.quarters[0]),
        'economies': num(fint(len({e for e, _ in ind}), lang)),
        'population_year': data.peers()['DZ']['population_year'],
        'africa_min': num(fint(AFRICA_MIN_ACCOUNTS, lang)),
        'africa_n': africa['members'],
        'dz_topics': num(fint(data.overview()['topics']['value'], lang)),
        'pushes_us': pushes_growth('US'),
        'pushes_dz': pushes_growth('DZ'),
        'revisions': revisions,
        'analytics': ctx.t('about.analytics_on' if ctx.site.analytics else 'about.analytics_off'),
        'hub_counts': ctx.t('about.hub_counts') if getattr(ctx.site.hub, 'metrics', None) else Markup(''),
        'accounts': num(fint(data.overview()['accounts']['value'], lang)),
        'yoy': num(fpct(data.overview()['yoy']['value'], 1, lang, sign=False)),
        'contact': Markup(f'<a href="mailto:{CONTACT}">{CONTACT}</a>'),
    }


# ---------------------------------------------------------------- blocks
def callout(lines, arg, md) -> Markup:
    (title, _, body), = items(lines)
    return Markup(f'<aside class="callout"><span class="callout-i">{icon("table", 20)}</span><div>'
                  f'<h3>{md.inline(title)}</h3><p>{md.inline(" ".join(paragraphs(body)))}</p></div></aside>')


def cards(lines, arg, md) -> Markup:
    out = join(f'<div class="doc-card"><h3>{md.inline(title)}</h3><p>{md.inline(" ".join(paragraphs(body)))}</p></div>'
               for title, _, body in items(lines))
    return Markup(f'<div class="doc-cards">{out}</div>')


def releases(ctx):
    """The last five Innovation Graph releases: the dates listed in the content, plus the
    release the data comes from if the list doesn't have it yet."""
    def draw(lines, arg, md) -> Markup:
        data = ctx.site.data
        listed = {l.strip().lstrip('- ').strip() for l in lines if l.strip()}
        listed.add(data.release_date[:10])
        dates = sorted(dt.date.fromisoformat(d) for d in listed)[-5:]
        lis = []
        for i, d in enumerate(dates):
            gap = f'<span class="rel-gap" dir="auto">{esc(days_text((d - dates[i - 1]).days, ctx.lang))}</span>' if i else ''
            last = i == len(dates) - 1
            q = f'<span class="rel-q" dir="auto">{ctx.t("methodology.releases_data", quarter=_q(ctx, data.quarter))}</span>' if last else ''
            lis.append(f'<li{' class="is-last"' if last else ""}>{gap}<span class="rel-dot" aria-hidden="true"></span>'
                       f'<time datetime="{d.isoformat()}" dir="auto">{esc(date_label(d, ctx.lang, short=ctx.en))}</time>{q}</li>')
        return Markup(f'<figure class="rel"><figcaption><span class="rel-t">{ctx.t("methodology.releases_title")}</span>'
                      f'<span class="rel-s">{ctx.t("methodology.releases_sub")}</span></figcaption>'
                      f'<ol class="rel-line">{"".join(lis)}</ol></figure>')
    return draw


def formulas(lines, arg, md) -> Markup:
    rows = []
    for title, ident, body in items(lines):
        body = [l.strip() for l in body if l.strip()]
        formula = re.fullmatch(r'`([^`]+)`', body[0]) if body else None
        if not formula:
            raise ValueError(f'formula {title!r}: the first line must be the formula in backticks')
        note = ' '.join(body[1:])
        rows.append(f'<div class="fm" id="{esc(ident)}"><div class="fm-a"><h3>{md.inline(title)}</h3>'
                    f'<code class="fm-f" dir="ltr">{esc(formula.group(1))}</code></div><p class="fm-n">{md.inline(note)}</p></div>')
    return Markup(f'<div class="formulas">{"".join(rows)}</div>')


def example(ctx):
    """Algeria's ratios recomputed from the counts in the published peers table."""
    def draw(lines, arg, md) -> Markup:
        data = ctx.site.data
        lang = ctx.lang
        dz = data.peers()['DZ']
        acc = data.overview()['accounts']
        f = lambda v: fint(v, lang)
        sums = {
            'yoy': (f'{f(acc["value"])} / {f(acc["year_earlier"])} − 1', fpct(acc['value'] / acc['year_earlier'] - 1, 1, lang)),
            'pushes_per_account': (f'{f(dz["git_pushes"])} / {f(dz["accounts"])}', fdec(dz['git_pushes'] / dz['accounts'], 2, lang)),
            'repos_per_account': (f'{f(dz["repositories"])} / {f(dz["accounts"])}', fdec(dz['repositories'] / dz['accounts'], 2, lang)),
            'orgs_per_account': (f'{f(dz["organizations"])} / {f(dz["accounts"])}', fdec(dz['organizations'] / dz['accounts'], 4, lang)),
            'accounts_per_million': (f'{f(dz["accounts"])} / {f(dz["population"])} × 10⁶',
                                     fint(dz['accounts'] / dz['population'] * 1e6, lang)),
        }
        rows = []
        for line in lines:
            if not line.strip():
                continue
            key, _, label = line.strip().lstrip('- ').partition(':')
            calc, result = sums[key.strip()]
            rows.append(f'<li><span class="ex-l">{md.inline(label.strip())}</span>'
                        f'<span class="ex-c" dir="ltr">{esc(calc)}</span><span class="ex-r" dir="ltr">{esc(result)}</span></li>')
        csv = f'/data/{data.folder.name}/peers.csv'
        return Markup(f'<figure class="example"><figcaption><span class="ex-t">'
                      f'{ctx.t("methodology.example_title", quarter=_q(ctx, data.quarter))}</span>'
                      f'<a class="ex-a" href="{csv}" download>{ctx.t("methodology.example_link")}</a></figcaption>'
                      f'<ul>{"".join(rows)}</ul></figure>')
    return draw


def groups(ctx):
    def draw(lines, arg, md) -> Markup:
        data = ctx.site.data
        rows = {r['group']: r for r in data.rows('groups') if r['quarter'] == data.quarter}
        cards_html = []
        for title, key, body in items(lines):
            g = rows[key]
            members = g['economies'].split()
            paras = paragraphs(body)
            if key == 'africa':
                squares = ''.join('<i></i>' for _ in members)
                inner = f'<div class="pg-sq" aria-hidden="true">{squares}</div><p class="pg-d">{md.inline(paras[0])}</p>'
            else:
                order = ([c for c in CORE_PEERS if c in members] if key == 'core_peers'
                         else sorted(members, key=lambda c: (c != 'DZ', ctx.s(f'economy.{c}'))))
                chips = ''.join(f'<li{' class="is-dz"' if c == "DZ" else ""}>{ctx.t(f"economy.{c}")}</li>' for c in order)
                inner = f'<ul class="pg-chips">{chips}</ul>'
            cards_html.append(f'<div class="pg-card"><div class="pg-h"><h3>{md.inline(title)}</h3>'
                              f'<span class="pg-n">{num(str(g["members"]))}</span></div>{inner}'
                              f'<p class="pg-f">{md.inline(paras[-1])}</p></div>')
        return Markup(f'<div class="pg">{"".join(cards_html)}</div>')
    return draw


def limits(lines, arg, md) -> Markup:
    out = []
    for title, _, body in items(lines):
        lis = ''.join(f'<li>{md.inline(l.strip()[2:])}</li>' for l in body if l.strip().startswith('- '))
        out.append(f'<div class="lim-card"><h3>{md.inline(title)}</h3><ul>{lis}</ul></div>')
    return Markup(f'<div class="lims">{"".join(out)}</div>')


def steps(ctx):
    def draw(lines, arg, md) -> Markup:
        out = []
        for line in lines:
            m = re.match(r'^\s*(\d+)\.\s+`([^`]+)`\s+((?:\[[^\]]+\]\s*)+)(.*)$', line)
            if not m:
                if line.strip():
                    raise ValueError(f'step not understood: {line!r}')
                continue
            n, name, tags, text = m.groups()
            tag_list = re.findall(r'\[([^\]]+)\]', tags)
            human = len(tag_list) > 1
            pills = ''.join(f'<span class="st-tag{" st-human" if human and i == len(tag_list) - 1 else ""}">{esc(t)}</span>'
                            for i, t in enumerate(tag_list))
            out.append(f'<li class="{"is-human" if human else ""}"><span class="st-n" aria-hidden="true">{n}</span>'
                       f'<div><p class="st-h"><code dir="ltr">{esc(name)}</code>{pills}</p><p class="st-p">{md.inline(text)}</p></div></li>')
        return Markup(f'<ol class="steps">{"".join(out)}</ol>')
    return draw


def log_cards(ctx):
    def draw(lines, arg, md) -> Markup:
        data = ctx.site.data
        change = logs.entry_list(ctx, logs.changelog(ctx), '', limit=3)
        fixes = logs.entry_list(ctx, logs.corrections(ctx), ctx.t('logs.none'), limit=3)
        card = lambda title, body, more: (f'<div class="log-card"><div class="log-h"><h3>{title}</h3>{more}</div>{body}</div>')
        more_c = f'<a class="log-more" href="{ctx.url("data", hash="changelog")}">{ctx.t("methodology.log_all")}</a>'
        more_f = f'<a class="log-more" href="{ctx.url("data", hash="corrections")}">{ctx.t("methodology.log_all")}</a>'
        actions = (C.btn(ctx.t('methodology.report'), logs.report_url())
                   + C.btn(ctx.t('methodology.download'), overview.zip_url(data), 'secondary', arrow=False, attrs=' download'))
        return Markup(f'<div class="logs">{card(ctx.t("logs.changelog"), change, more_c)}'
                      f'{card(ctx.t("logs.corrections"), fixes, more_f)}</div><div class="doc-actions">{actions}</div>')
    return draw


def cite(ctx):
    def draw(lines, arg, md) -> Markup:
        data = ctx.site.data
        text = ctx.t('methodology.cite_text', year=data.release_date[:4], quarter=_q(ctx, data.quarter),
                     url=f'https://djazair.dev{ctx.url("overview")}')
        return Markup(f'<figure class="cite"><figcaption><span class="cite-t">{ctx.t("methodology.cite_title")}</span>'
                      f'<button type="button" class="act" data-copy data-copied="{ctx.ta("code.copied")}" hidden>'
                      f'{ctx.t("code.copy")}</button></figcaption>'
                      f'<p class="cite-text">{text}</p><p class="cite-l">{ctx.t("methodology.cite_licence")}</p></figure>')
    return draw


# ---------------------------------------------------------------- page
def toc(ctx, secs) -> Markup:
    links = ''.join(f'<li><a href="#{s.id}"><span class="toc-n">{i:02d}</span>{esc(s.title)}</a></li>'
                    for i, s in enumerate(secs, 1))
    return Markup(f'<nav class="toc" aria-label="{ctx.ta("methodology.toc_label")}"><p class="toc-h">{ctx.t("methodology.toc")}</p>'
                  f'<ol>{links}</ol></nav>'
                  f'<details class="disclosure toc-m"><summary><span class="disc-s">{icon("book", 16)}{ctx.t("methodology.toc")}</span>'
                  f'<span class="chev">{icon("chev", 18)}</span></summary><nav class="disc-body" aria-label="{ctx.ta("methodology.toc_label")}">'
                  f'<ol>{links}</ol></nav></details>')


def head(ctx) -> Markup:
    data = ctx.site.data
    meta = [(ctx.t('methodology.meta_version'), ctx.t('methodology.version')),
            (ctx.t('methodology.meta_data'), quarter_label(data.quarter, ctx.lang, 'axis')),
            (ctx.t('methodology.meta_licence'), 'CC BY 4.0')]
    actions = [C.btn(ctx.t('methodology.download'), overview.zip_url(data), arrow=False, attrs=' download'),
               C.btn(ctx.t('methodology.code'), REPO, 'secondary')]
    return C.page_head(eyebrow_text=ctx.t('methodology.eyebrow'), title=ctx.t('methodology.title'),
                       lede=ctx.t('methodology.lede'), meta=meta, actions=actions)


def renderer(ctx) -> Renderer:
    return Renderer(values=values(ctx), link=lambda key, hash_: ctx.url(key, hash=hash_), directives={
        'callout': callout, 'cards': cards, 'releases': releases(ctx), 'formulas': formulas, 'example': example(ctx),
        'groups': groups(ctx), 'limits': limits, 'steps': steps(ctx), 'logs': log_cards(ctx), 'cite': cite(ctx)})


def document(ctx, name: str) -> tuple:
    """(sections, rendered sections) of ``content/<name>/<lang>.md``."""
    text = (CONTENT_DIR / name / f'{ctx.lang}.md').read_text('utf-8')
    secs = sections(text)
    md = renderer(ctx)
    out = join(f'<section class="doc-sec" id="{s.id}" aria-labelledby="{s.id}-h"><h2 id="{s.id}-h">'
               f'<span class="sec-n" aria-hidden="true">{i:02d}</span>{md.inline(s.title)}</h2>{md.render(s.body)}</section>'
               for i, s in enumerate(secs, 1))
    return secs, out


def render(ctx: Ctx) -> Page:
    secs, body = document(ctx, 'methodology')
    page = Markup(f'{head(ctx)}<div class="container doc">{toc(ctx, secs)}<div class="doc-main">{body}</div></div>')
    return Page(title=ctx.s('pages.methodology.title'), description=ctx.s('pages.methodology.description'), body=page)
