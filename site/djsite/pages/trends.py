"""Trends (ticket #20; Trends boards in docs/design): quarterly series since 2020 for four
indicators, actual or indexed to the first quarter, with one core peer brought forward
(IDX-07, AC-IDX-7, IDX-15).

Every view is drawn at build time: four indicators by two scales, each with a wide and a phone
drawing, its downloads and its data table. Radio buttons pick the view and CSS shows it, so
the page works without JavaScript; ``trends.js`` adds the crosshair readout (pointer, drag and
keyboard) and lets a pressed peer chip clear when pressed again.
"""
from __future__ import annotations

import json

from .. import charts
from .. import components as C
from ..charts import Bar, BarChart, Line, LineChart, loc, tick_compact, tick_dec, tick_int
from ..config import LANGS
from ..context import Ctx, Page
from ..figures import downloads, figure, line_key
from ..fmt import fdec, fint, fpct, quarter_label
from ..markup import Markup, esc, join
from ..scorecard import CORE_PEERS, NORTH_AFRICA

INDS = (('accounts', 'accounts'), ('pushes', 'pushes_per_account'), ('repos', 'repos_per_account'),
        ('orgs', 'orgs_per_account'))
SCALES = ('actual', 'indexed')
DECIMALS = {'accounts': 0, 'pushes': 2, 'repos': 2, 'orgs': 4}
SERIES = ('DZ', 'median_north_africa') + CORE_PEERS        # tables and the readout, in this order


def qlabel(q: str, lang: str) -> str:
    """Quarters on this page read as on its axes in English ('2020 Q1'), as words in Arabic."""
    return quarter_label(q, lang, 'axis' if lang == 'en' else 'text')


def view_id(key: str, scale: str) -> str:
    return f'{key}-{scale}'


def cls(key: str, scale: str = '') -> str:
    """Classes that show an element only in its view (scale '' for every scale)."""
    return f'v i-{key}' + (f' s-{scale}' if scale else '')


def values(data, ind: str, series: str, scale: str) -> list:
    vals = data.series(ind, series)
    if scale == 'indexed':
        base = vals[0]
        return [None if v is None or not base else v / base * 100 for v in vals]
    return vals


def formatter(key: str, scale: str):
    if scale == 'indexed' or key == 'accounts':
        return lambda v, lang: fint(v, lang)
    return lambda v, lang, d=DECIMALS[key]: fdec(v, d, lang)


def view_chart(ctx, key: str, ind: str, scale: str) -> LineChart:
    data = ctx.site.data
    qs = data.quarters
    first, last = qs[0], qs[-1]
    fmt = formatter(key, scale)
    lines = [Line(c, ctx.both(f'economy.{c}'), values(data, ind, c, scale), 'peer') for c in CORE_PEERS]
    lines.append(Line('median_north_africa', ctx.both('trends.na_median'), values(data, ind, 'median_north_africa', scale), 'median'))
    dz = values(data, ind, 'DZ', scale)
    lines.append(Line('DZ', ctx.both('economy.DZ'), dz, 'dz'))
    name = ctx.both(f'trends.ind.{key}')
    lower = {lang: (text[0].lower() + text[1:] if lang == 'en' else text) for lang, text in name.items()}
    q = lambda quarter: (lambda lang: qlabel(quarter, lang))
    common = dict(indicator=lower, last=q(last), value=lambda lang: fmt(charts.last(dz)[1], lang), **{'from': q(first), 'to': q(last)})
    if scale == 'indexed':
        title = ctx.both('trends.fig_indexed', indicator=name, quarter=q(first))
        summary = ctx.both('trends.summary_indexed', quarter=q(first), **common)
        unit = ctx.both('trends.unit.indexed', quarter=q(first))
    else:
        title = ctx.both('trends.fig_actual', indicator=name, **{'from': first[:4], 'to': last[:4]})
        summary = ctx.both('trends.summary', **common)
        unit = ctx.both(f'trends.unit.{key}')
    ticks = tick_int if scale == 'indexed' else (tick_compact if key == 'accounts' else tick_dec)
    return LineChart(id=f'trends-{view_id(key, scale)}', quarter=last, title=title, summary=summary, unit=unit, x=qs,
                     lines=lines, fmt=fmt, tick_fmt=ticks, baseline=100 if scale == 'indexed' else None,
                     peers_label=ctx.both('trends.six_peers'))


def views(ctx) -> list:
    return [(key, scale, view_chart(ctx, key, ind, scale)) for key, ind in INDS for scale in SCALES]


# ---------------------------------------------------------------- controls
def radio(name: str, value: str, checked: bool, extra_cls: str = '') -> str:
    return (f'<input class="sr-only{extra_cls}" type="radio" name="{name}" value="{esc(value)}" id="{name}-{esc(value)}"'
            f'{" checked" if checked else ""}>')


def tabs(ctx) -> Markup:
    ov = ctx.site.data.overview()
    lang = ctx.lang
    out = []
    for key, ind in INDS:
        row = ov[ind]
        value = formatter(key, 'actual')(row['value'], lang)
        change = row['change']
        pct = fpct(abs(change), 1 if key == 'accounts' else 0, lang, sign=False)
        said = ctx.t('trends.change_up' if change >= 0 else 'trends.change_down', pct=pct)
        up = ' up' if key == 'accounts' and change >= 0 else ''
        out.append(f'<label class="mt">{radio("tr-ind", key, key == "accounts")}<span class="mt-k">{ctx.t(f"trends.ind.{key}")}</span>'
                   f'<span class="mt-v"><span class="num" dir="ltr">{esc(value)}</span>'
                   f'<span class="mt-d num{up}" dir="ltr" aria-hidden="true">{"▲" if change >= 0 else "▼"} {esc(pct)}</span>'
                   f'<span class="sr-only">{said}</span></span></label>')
    return Markup(f'<div class="mts" role="radiogroup" aria-label="{ctx.ta("trends.indicator")}">{join(out)}</div>')


def scale_control(ctx) -> Markup:
    first = ctx.site.data.quarters[0]
    options = [('actual', ctx.t('trends.actual'), ''),
               ('indexed', ctx.t('trends.indexed', quarter=quarter_label(first, ctx.lang, 'axis')), ' class="mono" dir="ltr"')]
    labels = join(f'<label{attrs}>{radio("tr-scale", value, value == "actual")}<span>{text}</span></label>'
                  for value, text, attrs in options)
    return Markup(f'<div class="tr-ctl"><span class="ctl-label" id="tr-scale-label">{ctx.t("trends.scale")}</span>'
                  f'<div class="seg" role="radiogroup" aria-labelledby="tr-scale-label">{labels}</div></div>')


def peer_control(ctx) -> Markup:
    chips = join(f'<label class="pk">{radio("tr-hl", c, False, " tr-hl")}<span class="sw" aria-hidden="true"></span>'
                 f'{ctx.t(f"economy.{c}")}</label>' for c in CORE_PEERS)
    return Markup(f'<div class="tr-ctl tr-peers"><span class="ctl-label" id="tr-peers-label">{ctx.t("trends.compare")}</span>'
                  f'<div class="pks" role="radiogroup" aria-labelledby="tr-peers-label">'
                  f'<input type="radio" name="tr-hl" value="none" id="tr-hl-none" checked hidden>{chips}</div></div>')


# ---------------------------------------------------------------- readout
def readout_rows(ctx, key: str, scale: str, chart: LineChart, i: int) -> str:
    """The values in quarter ``i``: Algeria, the median, and the peer when one is brought forward."""
    by_key = {ln.key: ln for ln in chart.lines}
    rows = []
    for series in SERIES:
        v = by_key[series].values[i]
        text = '—' if v is None else chart.fmt(v, ctx.lang)
        kind = 'dz' if series == 'DZ' else 'md' if series.startswith('median') else f'p ro-p-{series}'
        rows.append(f'<span class="ro ro-{kind}" data-s="{series}"><span class="ro-n"><span class="sw sw-ro" aria-hidden="true"></span>'
                    f'{esc(loc(by_key[series].name, ctx.lang))}</span><span class="ro-v num" dir="ltr">{esc(text)}</span></span>')
    return ''.join(rows)


def payload(ctx, items) -> str:
    """What trends.js needs to place the crosshair and fill the readout, for this language."""
    data = ctx.site.data
    out = {'q': [quarter_label(q, ctx.lang, 'axis') for q in data.quarters], 'series': list(SERIES),
           'names': {}, 'views': {}}
    for key, scale, chart in items:
        by_key = {ln.key: ln for ln in chart.lines}
        out['names'] = {s: loc(by_key[s].name, ctx.lang) for s in SERIES}
        view = {'t': {s: ['—' if v is None else chart.fmt(v, ctx.lang) for v in by_key[s].values] for s in SERIES}}
        for size in ('wide', 'narrow'):
            L = charts.line_layout(chart, ctx.lang, size)
            view[size[0]] = {'g': [L['W'], L['H'], L['top'], round(L['ph'], 2), round(L['left'], 2),
                                   round(L['pw'] / (len(chart.x) - 1), 4)],
                             'y': {s: [None if v is None else round(L['Y'](v), 1) for v in by_key[s].values] for s in SERIES}}
        out['views'][view_id(key, scale)] = view
    return json.dumps(out, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def overlay() -> str:
    return ('<span class="xh ov" aria-hidden="true"></span><span class="tdot tdot-dz ov" aria-hidden="true"></span>'
            '<span class="tdot tdot-hl ov" aria-hidden="true"></span>')


# ---------------------------------------------------------------- figure 1
def figure_one(ctx, items) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    last = len(data.quarters) - 1
    titles = join(f'<span class="{cls(k, s)}">{esc(loc(ch.title, lang))}</span>' for k, s, ch in items)
    head = Markup(f'<div class="fig-head">{C.fig_label(ctx, 1, titles, "tr-fig-label")}{scale_control(ctx)}</div>')
    wide, narrow, readouts, menus = [], [], [], []
    for key, scale, chart in items:
        desc = f'{loc(chart.summary, lang)} {ctx.s("chart.desc_table")}'
        uid = f'tr-{view_id(key, scale)}'
        wide.append(charts.svg(chart, lang, 'wide', f'{uid}-w', desc, cls=cls(key, scale)))
        narrow.append(charts.svg(chart, lang, 'narrow', f'{uid}-n', desc, cls=cls(key, scale)))
        readouts.append(f'<span class="ro-rows {cls(key, scale)}">{readout_rows(ctx, key, scale, chart, last)}</span>')
        menus.append(f'<div class="{cls(key, scale)}">{C.download_menu(ctx, downloads(ctx, chart))}</div>')
    tip = ('<div class="tip ov" aria-hidden="true"><span class="tip-q num"></span>'
           + readout_rows(ctx, *items[0][:2], items[0][2], last) + '</div>')
    q = data.quarters
    members = _names(ctx, NORTH_AFRICA)
    source = ctx.t('trends.source', members=members, **{'from': qlabel(q[0], lang), 'to': qlabel(q[-1], lang)})
    first_chart = items[0][2]
    body = Markup(
        f'{tabs(ctx)}{head}{peer_control(ctx)}'
        f'<div class="cw cw-w wide" data-label="{ctx.ta("trends.readout")}">{join(wide)}{overlay()}{tip}</div>'
        f'<div class="tr-n narrow"><div class="cw cw-n">{join(narrow)}{overlay()}</div>'
        f'<div class="readout"><span class="ro-head"><span class="ro-q num" dir="ltr">{esc(quarter_label(q[-1], lang, "axis"))}</span>'
        f'<span class="ro-hint" hidden>{ctx.t("trends.drag")}</span></span>{join(readouts)}</div>'
        f'{line_key(ctx, first_chart)}</div>'
        f'<p class="sr-only" role="status" aria-live="polite" id="tr-live"></p>'
        + C.source_line(source, Markup(join(menus))))
    return C.frame(body, cls='fig tr-fig', labelledby='tr-fig-label')


def _names(ctx, codes) -> str:
    names = [ctx.s(f'economy.{c}') for c in sorted(codes, key=lambda c: ctx.site.catalog.lookup('en', f'economy.{c}')[0])]
    if ctx.en:
        return ', '.join(names[:-1]) + ' and ' + names[-1]
    return names[0] + ''.join(f' و{n}' for n in names[1:])


# ---------------------------------------------------------------- figure 2 and notes
def growth_chart(ctx) -> tuple:
    """Developer accounts, growth from each year's Q(n) to the next: (chart, lede)."""
    data = ctx.site.data
    qs, last = data.quarters, data.quarter
    n = last[-1]
    yoy = dict(zip(qs, data.series('yoy', 'DZ')))
    points = [(q[:4], yoy[q]) for q in qs if q.endswith(f'Q{n}') and yoy.get(q) is not None]
    years = [y for y, _ in points]
    vals = dict(points)
    y0, yn = years[0], years[-1]
    low_y = min(years, key=lambda y: vals[y])
    high_y = max(years, key=lambda y: vals[y])
    pct = lambda v: (lambda lang: fpct(v, 1, lang, sign=False))
    words = dict(first=pct(vals[y0]), last=pct(vals[yn]), low=pct(vals[low_y]), high=pct(vals[high_y]),
                 y0=y0, yn=yn, ylow=low_y, yhigh=high_y)
    dip = high_y == yn and low_y not in (y0, yn)
    lede = ctx.t('trends.fig2_lede_dip' if dip else 'trends.fig2_lede',
                 **{k: (v(ctx.lang) if callable(v) else v) for k, v in words.items()})
    chart = BarChart(id='trends-q-growth', quarter=last, title=ctx.both('trends.fig2_title', n=n),
                     summary=ctx.both('trends.fig2_summary', n=n, y0=y0, yn=yn, last=pct(vals[yn])),
                     bars=[Bar(y, y, v) for y, v in points], fmt=lambda v, lang: fpct(v, 1, lang, sign=False), highlight=yn)
    return chart, lede


def read_well(ctx) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    qs = data.quarters
    what = join(f'<div class="{cls(key)}">{C.measures(ctx, ctx.tl(f"ind.{key}.does"), ctx.tl(f"ind.{key}.doesnt"))}</div>'
                for key, _ in INDS)
    index = {c: values(data, 'accounts', c, 'indexed')[-1] for c in ('DZ',) + CORE_PEERS}
    top = max(CORE_PEERS, key=lambda c: index[c] or 0)
    why_index = ctx.t('trends.why_index_text', year=qs[0][:4], first=qlabel(qs[0], lang), last=qlabel(qs[-1], lang),
                      dz=fint(index['DZ'], lang), times=fdec(index['DZ'] / 100, 1, lang), peer=ctx.s(f'economy.{top}'),
                      peer_value=fint(index[top], lang))
    accounts = data.peers()
    big = max(NORTH_AFRICA, key=lambda c: accounts[c]['accounts'] or 0)
    why_median = ctx.t('trends.why_median_text', country=ctx.s(f'economy.{big}'), value=fint(accounts[big]['accounts'], lang))
    return Markup(f'<article class="card read-well"><h2>{ctx.t("trends.read_title")}</h2>'
                  + C.details(ctx.t('trends.what'), what, open_=True)
                  + C.details(ctx.t('trends.why_index', quarter=qlabel(qs[0], lang)), Markup(f'<p class="rw-p">{why_index}</p>'))
                  + C.details(ctx.t('trends.why_median'), Markup(f'<p class="rw-p">{why_median}</p>'))
                  + f'<div class="rw-more">{C.btn(ctx.t("trends.methodology"), ctx.url("methodology"), "secondary", size="s")}</div>'
                  + '</article>')


def tables(ctx, items) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    qs = data.quarters
    out = []
    for key, scale, chart in items:
        by_key = {ln.key: ln for ln in chart.lines}
        head = f'<th scope="col">{ctx.t("trends.quarter")}</th>' + ''.join(
            f'<th scope="col" class="end">{esc(loc(by_key[s].name, lang))}</th>' for s in SERIES)
        rows = []
        for i in range(len(qs) - 1, -1, -1):
            cells = ''.join(f'<td class="end">{esc("—" if by_key[s].values[i] is None else chart.fmt(by_key[s].values[i], lang))}</td>'
                            for s in SERIES)
            rows.append(f'<tr><th scope="row">{esc(quarter_label(qs[i], lang, "axis"))}</th>{cells}</tr>')
        caption = ctx.t('trends.table_caption', title=loc(chart.title, lang))
        out.append(f'<div class="table-wrap fig-dt dz-col {cls(key, scale)}" tabindex="0" role="region" aria-label="{esc(caption)}">'
                   f'<table class="dt"><caption class="sr-only">{caption}</caption><thead><tr>{head}</tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div>')
    meta = ctx.t('trends.table_meta', quarters=len(qs), series=len(SERIES))
    summary = Markup(f'{ctx.t("trends.table")}<span class="tbl-meta">{meta}</span>')
    body = Markup(f'{join(out)}<p class="fig-note">{ctx.t("trends.table_note")}</p>')
    return C.details(summary, body, cls='tr-table', icon_name='table', id_='trends-table')


def render(ctx: Ctx) -> Page:
    data = ctx.site.data
    lang = ctx.lang
    qs = data.quarters
    items = views(ctx)
    meta = [(ctx.t('trends.meta_data'), f'{quarter_label(qs[0], lang, "axis")} – {quarter_label(qs[-1], lang, "axis")}'),
            (ctx.t('trends.meta_quarters'), str(len(qs))), (ctx.t('trends.meta_licence'), 'CC0')]
    head = C.page_head(eyebrow_text=ctx.t('trends.eyebrow'), title=ctx.t('trends.title', year=qs[0][:4]),
                       lede=ctx.t('trends.lede', year=qs[0][:4]), meta=meta,
                       actions=[C.btn(ctx.t('trends.download'), f'/data/{data.folder.name}/trends.csv', 'secondary',
                                      arrow=False, attrs=' download')])
    chart2, lede2 = growth_chart(ctx)
    fig2 = figure(ctx, chart2, 2, source=ctx.t('trends.fig2_source', n=data.quarter[-1]), lede=lede2)
    body = Markup(f'{head}<section class="trends-body" aria-label="{ctx.ta("trends.chart_label")}"><div class="container">'
                  f'<div class="trc" id="trends">{figure_one(ctx, items)}'
                  f'<div class="tr-cols">{fig2}{read_well(ctx)}</div>{tables(ctx, items)}</div></div></section>'
                  f'<script type="application/json" id="trends-data">{payload(ctx, items)}</script>')
    script = ctx.site.assets.scripts.get('trends')
    return Page(title=ctx.s('pages.trends.title'), description=ctx.s('pages.trends.description'), body=body,
                scripts=(script,) if script else ())
