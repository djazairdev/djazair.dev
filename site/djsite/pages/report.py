"""Quarterly reports (ticket #34; PRD §13, IDX-17): the Reports page and one page per report.

A report's words live in ``content/reports/<yyyy-qN>/<lang>.md`` (``reports.py``). This module
draws them like the Methodology page, with a table of contents beside numbered sections, and
draws each ``:::`` block with the site's components:

- ``numbers``: the headline figures, each with its source and quarter (PRD §13, item 1);
- ``figure <key>``: one of the report's five charts, numbered in order, with its downloads and
  data table. The same five charts make the press kit;
- ``changes``, ``peers`` and ``languages``: tables of the quarter against the previous one and
  a year earlier, against the peer medians, and of the languages' ranks;
- ``hub``: the Hub's numbers on the date in ``report.json``;
- ``presskit``, ``method`` and ``cite``: the press kit (one zip with the charts in both
  languages and themes, their data and the methodology summary), the summary and a citation.

Every figure comes from the report's own quarter in ``data/derived/``, so a report keeps its
numbers when newer data arrives. ``report.json`` lists the claims its words make; the tests
check them against that quarter's data.
"""
from __future__ import annotations

import html
import io
import re
import zipfile
from dataclasses import dataclass

from .. import charts, editorial, reports
from .. import components as C
from ..charts import HBar, HBarChart, Line, LineChart, Note, UnitMap, loc, tick_compact, tick_dec, tick_pct
from ..config import LANGS, SITE_URL
from ..context import Ctx, Page
from ..data import Derived
from ..figures import downloads, figure
from ..fmt import date_label, fdec, fint, fpct, fsize, num, ordinal, quarter_label, rank_text
from ..icons import icon
from ..markdown import _PLACEHOLDER, Renderer, sections
from ..markup import Markup, esc, join, striptags
from ..palette import THEMES
from ..scorecard import CORE_PEERS, year_earlier
from . import languages as langs_page
from .methodology import CONTACT, toc

PER = 1000                     # accounts per square on the unit map, as on Home
TOP = 10                       # languages in the chart and the table
FIGURES = ('units', 'growth', 'pushes', 'accounts', 'languages')   # the press kit, in this order
SERIES = {'na': 'median_north_africa', 'af': 'median_africa'}
RANKED = {'accounts': 'accounts', 'yoy': 'yoy', 'pushes': 'pushes_per_account', 'repos': 'repos_per_account',
          'orgs': 'orgs_per_account', 'permillion': 'accounts_per_million'}
GROUPS = {'na': 'north_africa', 'af': 'africa'}


def find(ctx) -> reports.Report:
    """The report a route renders: its key is 'report-<yyyy-qN>'."""
    return next(r for r in reports.all_reports() if r.key == ctx.route.key)


def report_data(ctx, report: reports.Report) -> Derived:
    """The report's own quarter of derived data, read once per build."""
    folder = ctx.site.data.folder.parent / report.slug
    cache = ctx.site.cache.setdefault('reports', {})
    if folder not in cache:
        cache[folder] = ctx.site.data if folder == ctx.site.data.folder else Derived(folder)
    return cache[folder]


def _q(q: str, lang: str) -> str:
    return quarter_label(q, lang)


def slug(language: str) -> str:
    """A language's name in placeholders: 'C++' → 'cpp', 'Jupyter Notebook' → 'jupyter_notebook'."""
    s = language.lower().replace('+', 'p').replace('#', 'sharp')
    return re.sub(r'\W+', '_', s).strip('_')


# ---------------------------------------------------------------- {{values}}
def values(ctx, report: reports.Report, data: Derived) -> dict:
    """The {{name}} figures a report's text uses, in the page's language."""
    lang = ctx.lang
    q, qs = data.quarter, data.quarters
    prev, before = qs[-2], year_earlier(q)
    ov = data.overview()
    at = lambda ind, series='DZ': dict(zip(qs, data.series(ind, series)))
    whole = lambda v: num(fint(v, lang))
    pct = lambda v: num(fpct(v, 1, lang, sign=False))
    dec = lambda digits: (lambda v: num(fdec(v, digits, lang)))
    acc = at('accounts')
    n, _, _ = editorial.streak([v for quarter, v in zip(qs, data.series('yoy', 'DZ')) if quarter <= q])
    out = {
        'quarter': _q(q, lang), 'previous_quarter': _q(prev, lang), 'year_earlier_quarter': _q(before, lang),
        'first_quarter': _q(qs[0], lang), 'release_date': date_label(data.release_date, lang),
        'population_year': num(str(data.peers()['DZ']['population_year'])),
        'accounts': whole(acc[q]), 'accounts_previous': whole(acc[prev]), 'accounts_year_earlier': whole(acc[before]),
        'added_quarter': whole(acc[q] - acc[prev]), 'added_year': whole(acc[q] - acc[before]),
        'change_quarter': num(fpct(acc[q] / acc[prev] - 1, 1, lang, sign=False)),
        'accounts_na': whole(ov['accounts']['north_africa_median']),
        'permillion': whole(ov['accounts_per_million']['value']),
        'streak': editorial.count_phrase(ctx, n),
        'n_na': num(str(ov['yoy']['north_africa_ranked'])), 'n_af': num(str(ov['yoy']['africa_ranked'])),
        'contact': Markup(f'<a href="mailto:{CONTACT}">{CONTACT}</a>'),
    }
    # Each indicator now, last quarter and a year earlier, for Algeria and the two medians.
    for name, ind, fmt in (('yoy', 'yoy', pct), ('pushes', 'pushes_per_account', dec(2)),
                           ('repos', 'repos_per_account', dec(2)), ('orgs', 'orgs_per_account', dec(4))):
        for suffix, series in (('', 'DZ'), ('_na', SERIES['na']), ('_af', SERIES['af'])):
            s = at(ind, series)
            out[f'{name}{suffix}'] = fmt(s[q])
            out[f'{name}{suffix}_previous'] = fmt(s[prev])
            out[f'{name}{suffix}_year_earlier'] = fmt(s[before])
    for key, ind in RANKED.items():
        for short, group in GROUPS.items():
            row = ov[ind]
            out[f'rank.{key}.{short}'] = num(rank_text(row[f'{group}_rank'], row[f'{group}_ranked'], lang))
    out.update(language_values(ctx, data))
    return out


def language_values(ctx, data: Derived) -> dict:
    """``lang.<slug>.<field>`` for each of Algeria's languages in the quarter: name, pushers,
    change, and its rank now, a year earlier and in the first quarter (``ord``: '4th')."""
    lang = ctx.lang
    first = {r['language']: r['rank'] for r in data.rows('languages_algeria') if r['quarter'] == data.quarters[0]}
    ord_ = lambda r: '—' if r is None else ordinal(r) if lang == 'en' else str(r)
    out = {}
    for r in langs_page.rows(data):
        s = f'lang.{slug(r["language"])}'
        ranks = {'': r['rank'], '_year_earlier': r['rank_year_earlier'], '_first': first.get(r['language'])}
        out[f'{s}.name'] = Markup(f'<bdi lang="en">{esc(r["language"])}</bdi>')
        out[f'{s}.pushers'] = num(fint(r['pushers'], lang))
        out[f'{s}.change'] = num(fpct(r['change'], 0, lang)) if r['change'] is not None else '—'
        for suffix, rank in ranks.items():
            out[f'{s}.rank{suffix}'] = num('—' if rank is None else str(rank))
            out[f'{s}.ord{suffix}'] = num(ord_(rank))
    return out


def plain(value) -> str:
    """A value as plain text, for files."""
    return html.unescape(re.sub(r'<[^>]*>', '', str(esc(value))))


# ---------------------------------------------------------------- charts
@dataclass
class Figures:
    """The report's five charts, built once per page."""
    specs: dict

    def __getitem__(self, key):
        return self.specs[key]


def build_charts(ctx, data: Derived) -> Figures:
    credit = {lang: ctx.site.catalog.lookup(lang, 'chart.credit')[0] for lang in LANGS}
    q, qs = data.quarter, data.quarters
    before = year_earlier(q)
    ql = lambda quarter: (lambda lang: quarter_label(quarter, lang))
    span = {'from': ql(qs[0]), 'to': ql(q)}

    a = data.overview()['accounts']
    units = UnitMap(id='report-units', quarter=q, title={}, summary={}, total=int(a['value']), start=int(a['year_earlier']),
                    per=PER, credit=credit)
    squares, added = units.squares
    per = lambda lang: fint(PER, lang)
    units.title = ctx.both('report.fig.units', per=per, quarter=ql(q))
    units.summary = ctx.both('home.map_desc', total=lambda lang: fint(squares, lang), per=per,
                             added=lambda lang: fint(added, lang), quarter=ql(before))
    units.start_label = {lang: quarter_label(before, lang) for lang in LANGS}
    units.added_label = ctx.both('home.map_new')
    units.total_label = {lang: quarter_label(q, lang) for lang in LANGS}
    units.square_label = ctx.both('home.map_quantity')

    def medians_chart(id_, ind, start, fmt, ticks, key):
        series = {k: data.series(ind, k) for k in ('DZ', SERIES['na'], SERIES['af'])}
        last = lambda k: (lambda lang: fmt(series[k][-1], lang))
        return LineChart(
            id=id_, quarter=q, credit=credit, x=qs[start:], fmt=fmt, tick_fmt=ticks,
            title=ctx.both(f'report.fig.{key}', **{'from': qs[start][:4], 'to': q[:4]}),
            summary=ctx.both(f'report.fig.{key}_summary', **{'from': ql(qs[start]), 'to': ql(q)}, quarter=ql(q),
                             dz=last('DZ'), na=last(SERIES['na']), af=last(SERIES['af'])),
            unit=ctx.both(f'report.fig.{key}_unit'),
            lines=[Line(SERIES['af'], ctx.both('home.africa_median'), series[SERIES['af']][start:], 'median'),
                   Line(SERIES['na'], ctx.both('home.north_median'), series[SERIES['na']][start:], 'ref'),
                   Line('DZ', ctx.both('home.algeria'), series['DZ'][start:], 'dz')])

    growth = medians_chart('report-growth', 'yoy', 4, lambda v, lang: fpct(v, 1, lang), tick_pct, 'growth')
    dz = data.series('yoy', 'DZ')
    n, direction, start = editorial.streak(dz)
    if direction > 0 and n > 1 and start >= 4:              # point at the low the streak started from
        pct = lambda v: (lambda lang: fpct(v, 1, lang, sign=False))
        growth.notes = [Note(qs[start], 'DZ', ctx.both('home.trend_note', count=lambda lang: editorial.count_phrase(ctx, n, True, lang),
                                                       low=pct(dz[start]), high=pct(dz[-1])), dy=110)]
    pushes = medians_chart('report-pushes', 'pushes_per_account', 0, lambda v, lang: fdec(v, 2, lang), tick_dec, 'pushes')

    peers = [Line(c, ctx.both(f'economy.{c}'), data.series('accounts', c), 'peer') for c in CORE_PEERS]
    accounts = LineChart(
        id='report-accounts', quarter=q, credit=credit, x=qs, fmt=lambda v, lang: fint(v, lang), tick_fmt=tick_compact,
        title=ctx.both('report.fig.accounts', **{'from': qs[0][:4], 'to': q[:4]}),
        summary=ctx.both('report.fig.accounts_summary', **span, value=lambda lang: fint(a['value'], lang), quarter=ql(q)),
        unit=ctx.both('report.fig.accounts_unit'), peers_label=ctx.both('trends.six_peers'),
        lines=peers + [Line(SERIES['na'], ctx.both('trends.na_median'), data.series('accounts', SERIES['na']), 'median'),
                       Line('DZ', ctx.both('economy.DZ'), data.series('accounts', 'DZ'), 'dz')])

    quarter = {lang: quarter_label(q, lang) for lang in LANGS}
    both = lambda key, **kw: ctx.both(f'languages.{key}', **kw)
    bars = [HBar(r['language'], r['language'], r['pushers'], r['pushers_year_earlier'], r['rank'])
            for r in langs_page.rows(data)[:TOP]]
    languages = HBarChart(id='report-languages', quarter=q, credit=credit, title=both('fig_title', quarter=quarter),
                          summary=both('fig_summary', quarter=quarter), unit=ctx.both('chart.developers'), bars=bars,
                          fmt=lambda v, lang: fint(v, lang), change_fmt=lambda v, lang: fpct(v, 1, lang),
                          category_label=both('category'), now_label=quarter,
                          before_label={lang: quarter_label(before, lang) for lang in LANGS},
                          added_label=both('added'), change_label=both('change'))
    return Figures({'units': units, 'growth': growth, 'pushes': pushes, 'accounts': accounts, 'languages': languages})


def chart_source(ctx, key: str, data: Derived) -> Markup:
    q, date = _q(data.quarter, ctx.lang), date_label(data.release_date, ctx.lang)
    if key == 'growth':
        return ctx.t('home.trend_source')
    if key == 'languages':
        return ctx.t('languages.source', quarter=q)
    return ctx.t(f'report.src_{key}' if key == 'pushes' else 'report.src', quarter=q, date=date)


# ---------------------------------------------------------------- blocks
def _chip(ctx, figure_text: str, words, kind: str = 'flat') -> Markup:
    """A chip of a figure and words, as on the scorecard: the figure isolated in Arabic."""
    fig = esc(figure_text) if ctx.en else num(figure_text)
    return C.chip(Markup(f'{fig} {words}'), kind)


def key_figures(ctx, data: Derived):
    def draw(lines, arg, md) -> Markup:
        lang, q = ctx.lang, data.quarter
        ov = data.overview()
        a, y, p, pm = ov['accounts'], ov['yoy'], ov['pushes_per_account'], ov['accounts_per_million']
        medians = lambda row, fmt: ctx.t('report.kf.medians', na=num(fmt(row['north_africa_median'])), af=num(fmt(row['africa_median'])))
        source = ctx.t('report.kf.source', quarter=_q(q, lang))
        year = data.peers()['DZ']['population_year']
        figures = {
            'accounts': (ctx.t('ind.accounts.title'), fint(a['value'], lang),
                         _chip(ctx, f'▲ {fpct(y["value"], 1, lang, sign=False)}', ctx.t('ind.in_year'), 'up'),
                         ctx.t('report.kf.added', n=num(fint(a['value'] - a['year_earlier'], lang, sign=True)),
                               quarter=_q(year_earlier(q), lang)), source),
            'growth': (ctx.t('report.kf.growth'), fpct(y['value'], 1, lang, sign=False),
                       C.chip(ctx.t('report.kf.rank_na', rank=num(rank_text(y['north_africa_rank'], y['north_africa_ranked'], lang)))),
                       medians(y, lambda v: fpct(v, 1, lang, sign=False)), source),
            'pushes': (ctx.t('ind.pushes.title'), fdec(p['value'], 2, lang),
                       _chip(ctx, f'{"▲" if p["change"] >= 0 else "▼"} {fpct(abs(p["change"]), 0, lang, sign=False)}',
                             ctx.t('ind.in_year')),
                       medians(p, lambda v: fdec(v, 2, lang)), source),
            'permillion': (ctx.t('ind.permillion.title'), fint(pm['value'], lang),
                           C.chip(ctx.t('ind.eq_na')) if abs(pm['value'] / pm['north_africa_median'] - 1) < 0.005
                           else _chip(ctx, fpct(pm['value'] / pm['north_africa_median'] - 1, 0, lang), ctx.t('ind.vs_na')),
                           ctx.t('report.kf.cp_median', median=num(fint(pm['core_peers_median'], lang))),
                           ctx.t('report.kf.source_pop', quarter=_q(q, lang), year=year)),
        }
        cards = []
        for line in lines:
            key = line.strip().lstrip('- ').strip()
            if not key:
                continue
            label, value, chip, context, src = figures[key]
            cards.append(f'<div class="kf-card"><dt class="kf-l">{label}</dt><dd class="kf-v num" dir="ltr">{esc(value)}</dd>'
                         f'<dd class="kf-c">{chip}</dd><dd class="kf-x">{context}</dd><dd class="kf-s">{src}</dd></div>')
        return Markup(f'<dl class="kf">{"".join(cards)}</dl>')
    return draw


def figure_block(ctx, data: Derived, figs: Figures, seen: list):
    def draw(lines, arg, md) -> Markup:
        if arg not in FIGURES:
            raise KeyError(f'no report figure {arg!r}: use one of {", ".join(FIGURES)}')
        seen.append(arg)
        return figure(ctx, figs[arg], len(seen), source=chart_source(ctx, arg, data), cls='rp-fig')
    return draw


def changes_table(ctx, data: Derived):
    """Algeria's six indicators now, a quarter earlier and a year earlier, with the change."""
    def draw(lines, arg, md) -> Markup:
        lang, q, qs = ctx.lang, data.quarter, data.quarters
        prev, before = qs[-2], year_earlier(q)
        rows = []
        for key, ind, fmt, title in (('accounts', 'accounts', lambda v: fint(v, lang), 'ind.accounts.title'),
                                     ('yoy', 'yoy', lambda v: fpct(v, 1, lang, sign=False), 'report.kf.growth'),
                                     ('pushes', 'pushes_per_account', lambda v: fdec(v, 2, lang), 'ind.pushes.title'),
                                     ('repos', 'repos_per_account', lambda v: fdec(v, 2, lang), 'ind.repos.title'),
                                     ('orgs', 'orgs_per_account', lambda v: fdec(v, 4, lang), 'ind.orgs.title'),
                                     ('permillion', 'accounts_per_million', lambda v: fint(v, lang), 'ind.permillion.title')):
            s = dict(zip(qs, data.series(ind, 'DZ')))
            if key == 'yoy':          # a change in a rate is in percentage points
                change = ctx.t('report.points', n=num(fdec((s[q] - s[before]) * 100, 1, lang, sign=True)))
            else:
                change = num(fpct(s[q] / s[before] - 1, 1, lang))
            rows.append((key, [ctx.t(title), num(fmt(s[q])), num(fmt(s[prev])), num(fmt(s[before])), change]))
        head = [(ctx.t('report.col_indicator'), 'start'), (esc(_q(q, lang)), 'end'), (esc(_q(prev, lang)), 'end'),
                (esc(_q(before, lang)), 'end'), (ctx.t('report.col_change'), 'end')]
        caption = ctx.t('report.changes_caption', quarter=_q(q, lang))
        return C.data_table(caption, head, rows, cls='rp-table') + C.source_line(
            ctx.t('report.src', quarter=_q(q, lang), date=date_label(data.release_date, lang)))
    return draw


def peers_table(ctx, data: Derived):
    """Algeria against the North African and African medians, with its ranks in both groups."""
    def draw(lines, arg, md) -> Markup:
        lang, q = ctx.lang, data.quarter
        ov = data.overview()
        rows = []
        for key, title, fmt in (('accounts', 'ind.accounts.title', lambda v: fint(v, lang)),
                                ('yoy', 'report.kf.growth', lambda v: fpct(v, 1, lang, sign=False)),
                                ('pushes_per_account', 'ind.pushes.title', lambda v: fdec(v, 2, lang)),
                                ('repos_per_account', 'ind.repos.title', lambda v: fdec(v, 2, lang)),
                                ('orgs_per_account', 'ind.orgs.title', lambda v: fdec(v, 4, lang)),
                                ('accounts_per_million', 'ind.permillion.title', lambda v: fint(v, lang))):
            r = ov[key]
            cells = [ctx.t(title), num(fmt(r['value']))]
            cells += [num(fmt(r[f'{g}_median'])) for g in ('north_africa', 'africa')]
            cells += [num(rank_text(r[f'{g}_rank'], r[f'{g}_ranked'], lang)) for g in ('north_africa', 'africa')]
            rows.append((key, cells))
        head = [(ctx.t('report.col_indicator'), 'start'), (ctx.t('economy.DZ'), 'end'),
                (ctx.t('overview.med_na', n=ov['yoy']['north_africa_ranked']), 'end'),
                (ctx.t('overview.med_af', n=ov['yoy']['africa_ranked']), 'end'),
                (ctx.t('report.col_rank_na'), 'end'), (ctx.t('report.col_rank_af'), 'end')]
        caption = ctx.t('report.peers_caption', quarter=_q(q, lang))
        year = data.peers()['DZ']['population_year']
        return C.data_table(caption, head, rows, cls='rp-table rp-peers') + C.source_line(
            ctx.t('overview.peers_source', quarter=_q(q, lang), year=year))
    return draw


def languages_table(ctx, data: Derived):
    """The top ten languages and any that left them in the year, with their ranks over time."""
    def draw(lines, arg, md) -> Markup:
        lang, q, first_q = ctx.lang, data.quarter, data.quarters[0]
        first = {r['language']: r['rank'] for r in data.rows('languages_algeria') if r['quarter'] == first_q}
        all_rows = langs_page.rows(data)
        shown = all_rows[:TOP] + [r for r in all_rows[TOP:] if r['rank_year_earlier'] and r['rank_year_earlier'] <= TOP]
        rank = lambda r: (num(str(r)), r) if r else ('—', '')
        rows = []
        for r in shown:
            name = Markup(f'<span class="lang-n" lang="en" dir="ltr">{esc(r["language"])}</span>')
            change = (num(fpct(r['change'], 0, lang)), r['change']) if r['change'] is not None else ('—', '')
            rows.append((r['language'], [name, (num(fint(r['pushers'], lang)), r['pushers']), change, rank(r['rank']),
                                         rank(r['rank_year_earlier']), rank(first.get(r['language']))]))
        head = [(ctx.t('languages.category'), 'start'), (ctx.t('chart.developers'), 'end'), (ctx.t('languages.change'), 'end'),
                (ctx.t('report.col_rank_q', quarter=_q(q, lang)), 'end'),
                (ctx.t('report.col_rank_q', quarter=_q(year_earlier(q), lang)), 'end'),
                (ctx.t('report.col_rank_q', quarter=_q(first_q, lang)), 'end')]
        caption = ctx.t('report.languages_caption', quarter=_q(q, lang))
        return C.data_table(caption, head, rows, cls='rp-table rp-langs') + C.source_line(
            ctx.t('report.languages_note', n=TOP))
    return draw


def hub_block(ctx, report: reports.Report):
    def draw(lines, arg, md) -> Markup:
        hub, lang = report.hub, ctx.lang
        if not hub:
            raise ValueError(f'content/reports/{report.slug}/report.json has no "hub" numbers for the ::: hub block')
        items = [(ctx.t('report.hub_projects'), num(fint(hub['projects'], lang))),
                 (ctx.t('report.hub_issues'), num(fint(hub['issues'], lang)))]
        cards = ''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in items)
        when = ctx.t('report.hub_date', date=date_label(hub['date'], lang))
        return Markup(f'<div class="rp-hub"><dl>{cards}</dl><p>{when}</p></div>')
    return draw


def method_block(ctx):
    def draw(lines, arg, md) -> Markup:
        items = [l.strip()[2:] for l in lines if l.strip().startswith('- ')]
        return Markup(f'<div class="rp-method"><h3>{ctx.t("report.method_title")}</h3>'
                      f'<ul>{"".join(f"<li>{md.inline(x)}</li>" for x in items)}</ul></div>')
    return draw


def cite_block(ctx, report: reports.Report, front: dict):
    def draw(lines, arg, md) -> Markup:
        year = (report.published or ctx.site.data.release_date)[:4]
        text = ctx.t('report.cite_text', year=year, title=front['title'], n=report.number,
                     url=f'{SITE_URL}{ctx.url(report.key)}')
        return Markup(f'<figure class="cite"><figcaption><span class="cite-t">{ctx.t("report.cite_title")}</span>'
                      f'<button type="button" class="act" data-copy data-copied="{ctx.ta("code.copied")}" hidden>'
                      f'{ctx.t("code.copy")}</button></figcaption>'
                      f'<p class="cite-text">{text}</p><p class="cite-l">{ctx.t("methodology.cite_licence")}</p></figure>')
    return draw


# ---------------------------------------------------------------- press kit
def zip_path(report: reports.Report) -> str:
    return f'/reports/{report.slug}/djazair.dev-report-{report.slug}-press-kit.zip'


def method_text(ctx, report: reports.Report, data: Derived, lang: str) -> str:
    """The ``::: method`` block of ``<lang>.md`` as plain text, with its figures filled in."""
    other = Ctx(ctx.site, lang, ctx.route)
    vals = values(other, report, data)
    front, body = report.source(lang)
    m = re.search(r'^::: method\n(.*?)^:::$', body, re.S | re.M)
    if not m:
        return ''
    fill = lambda s: _PLACEHOLDER.sub(lambda v: plain(vals[v.group(1)]), s)
    text = re.sub(r'\*\*|\[([^\]]+)\]\([^)]*\)', lambda x: x.group(1) or '', fill(m.group(1)))
    title = other.s('report.method_title')
    return f'{front["title"]}\n{title}\n\n{text.strip()}\n'


def press_kit(ctx, report: reports.Report, data: Derived, figs: Figures) -> bytes:
    """The charts of the report in both languages and both themes, their CSV and JSON, the
    methodology summary in both languages and a README. Names, order and timestamps are
    fixed, so the same report always gives the same file."""
    stamp = tuple(int(x) for x in data.release_date.split('-')) + (0, 0, 0)
    root = f'djazair.dev-report-{report.slug}'
    files = []
    readme = []
    for lang in LANGS:
        other = Ctx(ctx.site, lang, ctx.route)
        front, _ = report.source(lang)
        lines = [front['title'], other.s('report.readme_kit').replace('{n}', str(report.number)),
                 f'{SITE_URL}{other.url(report.key)}', '']
        if report.draft:
            lines += [other.s('report.readme_draft'), '']
        lines.append(other.s('report.readme_charts'))
        for i, key in enumerate(FIGURES, 1):
            lines.append(f'  {i}. {figs[key].id}: {loc(figs[key].title, lang)}')
        lines += ['', other.s('report.readme_files'), '', other.s('report.readme_licence'),
                  f'{other.s("report.cite_title")}: ' + plain(other.t('report.cite_text', year=(report.published or data.release_date)[:4],
                                                                          title=front['title'], n=report.number,
                                                                          url=f'{SITE_URL}{other.url(report.key)}')),
                  f'{other.s("report.readme_contact")}: {CONTACT}', '']
        readme.append('\n'.join(lines))
        files.append((f'methodology-summary-{lang}.txt', method_text(ctx, report, data, lang).encode('utf-8')))
    files.insert(0, ('README.txt', ('\n' + '-' * 60 + '\n\n').join(readme).encode('utf-8')))
    for key in FIGURES:
        chart = figs[key]
        files += [(f'data/{chart.id}.csv', chart.csv()), (f'data/{chart.id}.json', chart.json())]
        for lang in LANGS:
            for theme, pal in THEMES.items():
                files.append((f'{lang}/{chart.id}-{theme}.svg', charts.download_svg(chart, lang, pal)))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for name, data_ in files:
            info = zipfile.ZipInfo(f'{root}/{name}', date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data_, compresslevel=9)
    return buf.getvalue()


def presskit_block(ctx, report: reports.Report, data: Derived, figs: Figures):
    def draw(lines, arg, md) -> Markup:
        kit = press_kit(ctx, report, data, figs)
        url = ctx.site.add_file(zip_path(report), kit)
        items = []
        for i, key in enumerate(FIGURES, 1):
            chart = figs[key]
            items.append(f'<li><span class="kit-n num">{ctx.t("fig.label")} {i:02d}</span>'
                         f'<a class="kit-t" href="#{chart.id}-label">{esc(loc(chart.title, ctx.lang))}</a>'
                         f'{C.download_menu(ctx, downloads(ctx, chart))}</li>')
        size = num(f'ZIP · {fsize(len(kit), ctx.lang)}', 'dl-size')
        button = C.btn(Markup(f'{ctx.t("report.kit_download")} {size}'), url, arrow=False, attrs=' download')
        return Markup(f'<div class="kit"><div class="kit-head">{button}<p>{ctx.t("report.kit_text")}</p></div>'
                      f'<ol class="kit-list">{"".join(items)}</ol></div>')
    return draw


# ---------------------------------------------------------------- the report page
def renderer(ctx, report: reports.Report, data: Derived, front: dict, figs: Figures, seen: list) -> Renderer:
    return Renderer(values=values(ctx, report, data), link=lambda key, hash_: ctx.url("data" if key == "methodology" else key, hash=hash_), directives={
        'numbers': key_figures(ctx, data), 'figure': figure_block(ctx, data, figs, seen), 'changes': changes_table(ctx, data),
        'peers': peers_table(ctx, data), 'languages': languages_table(ctx, data), 'hub': hub_block(ctx, report),
        'presskit': presskit_block(ctx, report, data, figs), 'method': method_block(ctx), 'cite': cite_block(ctx, report, front)})


def status(ctx, report: reports.Report) -> Markup:
    if report.draft:
        return ctx.t('report.status_draft')
    return Markup(esc(date_label(report.published, ctx.lang, short=ctx.en)))


def notes(ctx, report: reports.Report, data: Derived) -> Markup:
    """The draft notice, and a note when GitHub has re-released the quarter since it was written."""
    items = []
    if report.draft:
        items.append((ctx.t('report.draft_title'), ctx.t('report.draft_text')))
    if data.release != report.release:
        items.append((ctx.t('report.revised_title'), ctx.t('report.revised_text', date=date_label(data.release_date, ctx.lang))))
    return join(f'<aside class="callout rp-note" role="note"><span class="callout-i">{icon("info", 20)}</span><div>'
                f'<p class="rp-note-t">{title}</p><p>{text}</p></div></aside>' for title, text in items)


def render(ctx: Ctx) -> Page:
    report = find(ctx)
    data = report_data(ctx, report)
    front, body = report.source(ctx.lang)
    figs = build_charts(ctx, data)
    seen: list = []
    md = renderer(ctx, report, data, front, figs, seen)
    secs = sections(body)
    out = join(f'<section class="doc-sec" id="{s.id}" aria-labelledby="{s.id}-h"><h2 id="{s.id}-h">'
               f'<span class="sec-n" aria-hidden="true">{i:02d}</span>{md.inline(s.title)}</h2>{md.render(s.body)}</section>'
               for i, s in enumerate(secs, 1))
    standfirst = md.inline(front['standfirst'])
    meta = [(ctx.t('report.meta_data'), _q(data.quarter, ctx.lang)),
            (ctx.t('overview.meta_released'), date_label(data.release_date, ctx.lang, short=ctx.en)),
            (ctx.t('report.meta_status' if report.draft else 'report.meta_published'), status(ctx, report)),
            (ctx.t('overview.meta_licence'), 'CC BY 4.0')]
    actions = [C.btn(ctx.t('report.kit'), '#press', arrow=False), C.btn(ctx.t('overview.methodology'), ctx.url('data'), 'secondary')]
    head = C.page_head(eyebrow_text=ctx.t('report.eyebrow', n=f'{report.number:02d}'), title=esc(front['title']),
                       lede=standfirst, meta=meta, actions=actions)
    page = Markup(f'{head}<div class="container doc rp">{toc(ctx, secs)}<div class="doc-main">{notes(ctx, report, data)}{out}</div></div>')
    return Page(title=front['title'], description=plain(standfirst), body=page, indexed=not report.draft)


# ---------------------------------------------------------------- the Reports page
def contents(ctx, report: reports.Report) -> Markup:
    """The report's sections as numbered links."""
    _, body = report.source(ctx.lang)
    url = ctx.url(report.key)
    return Markup('<ol class="rp-toc">' + ''.join(
        f'<li><a href="{url}#{s.id}"><span class="toc-n num">{i:02d}</span><span>{esc(s.title)}</span></a></li>'
        for i, s in enumerate(sections(body), 1)) + '</ol>')


def summary(ctx, report: reports.Report) -> Markup:
    """The standfirst, with its figures."""
    data = report_data(ctx, report)
    front, _ = report.source(ctx.lang)
    return Renderer(values=values(ctx, report, data)).inline(front['standfirst'])


def card(ctx, report: reports.Report) -> Markup:
    front, _ = report.source(ctx.lang)
    data = report_data(ctx, report)
    url = ctx.url(report.key)
    chip = f' {C.chip(ctx.t("report.status_draft"))}' if report.draft else ''
    when = (ctx.t('report.card_published', date=date_label(report.published, ctx.lang)) if not report.draft
            else ctx.t('report.card_data', quarter=_q(data.quarter, ctx.lang)))
    acts = C.btn(ctx.t('report.read'), url) + C.btn(ctx.t('report.kit'), f'{url}#press', 'secondary', arrow=False)
    return Markup(f'<article class="card rp-card"><div class="rp-card-main">'
                  f'<p class="rp-card-k"><span class="rp-no num">{ctx.t("report.no", n=f"{report.number:02d}")}</span>'
                  f'<span>{when}</span>{chip}</p>'
                  f'<h3><a href="{url}">{esc(front["title"])}</a></h3><p class="rp-card-s">{summary(ctx, report)}</p>'
                  f'<div class="section-actions">{acts}</div></div>{contents(ctx, report)}</article>')


def render_index(ctx: Ctx) -> Page:
    found = [r for r in reports.all_reports() if ctx.has(r.key)]
    meta = [(ctx.t('reports.meta_schedule'), ctx.t('reports.schedule')), (ctx.t('reports.meta_languages'), ctx.t('reports.languages')),
            (ctx.t('overview.meta_licence'), 'CC BY 4.0')]
    head = C.page_head(eyebrow_text=ctx.t('reports.eyebrow'), title=ctx.t('reports.title'), lede=ctx.t('reports.lede'), meta=meta)
    cards = join(card(ctx, r) for r in found) if found else Markup(f'<p class="lede">{ctx.t("reports.none")}</p>')
    rules = join(f'<div class="limit"><h3>{ctx.t(f"reports.rule.{k}")}</h3><p>{ctx.t(f"reports.rule.{k}_text")}</p></div>'
                 for k in ('accounts', 'bad_news', 'medians', 'checked', 'corrections'))
    more = C.btn(ctx.t('reports.corrections'), ctx.url('data', hash='corrections'), 'secondary', size='s')
    body = (head + C.section('list', ctx.t('reports.list_eyebrow'), ctx.t('reports.list_title'), Markup(f'<div class="rp-list">{cards}</div>'),
                             lede=ctx.t('reports.next'), size='s')
            + C.section('rules', ctx.t('reports.rules_eyebrow'), ctx.t('reports.rules_title'),
                        Markup(f'<div class="limits rp-rules">{rules}</div><div class="limits-more">{more}</div>'), size='s'))
    return Page(title=ctx.s('pages.reports.title'), description=ctx.s('pages.reports.description'), body=Markup(body))
