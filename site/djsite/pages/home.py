"""Home (ticket #18; Home boards in docs/design): the hero with the unit map, the scorecard of
six indicators, the growth trend, the latest quarterly report (#34), the Hub teaser and the
open-by-default links.

Every number comes from the derived data. Sentences that state a fact are computed from it
(``editorial``); the trend headline comes from ``content/editorial/<quarter>.json`` when one
exists for the quarter and its claims still hold, with a neutral computed headline otherwise.
"""
from __future__ import annotations

from .. import charts
from .. import components as C
from .. import editorial
from ..charts import Line, LineChart, Note, UnitMap, loc, tick_pct
from ..config import LANGS, REPO_URL
from ..context import Ctx, Page
from ..figures import figure, table, unit_key
from ..fmt import date_label, fint, fpct, num, quarter_label, rank_text
from ..icons import icon
from ..markup import Markup, esc, join
from ..scorecard import indicators, year_earlier
from . import report

PER = 1000                     # accounts per square on the unit map
GROUP = {'en': ',', 'ar': '.'}  # digit-group separators, as fmt writes them


# ---------------------------------------------------------------- the account ticker
def _groups(value: int) -> list:
    return f'{value:,}'.split(',')


def animated(data) -> bool:
    """The count animates from a year earlier only when both numbers have as many digit
    groups (a counter can't add a group mid-count)."""
    a = data.overview()['accounts']
    return len(_groups(int(a['value']))) == len(_groups(int(a['year_earlier'])))


def ticker_css(data) -> str:
    """The ticker's stylesheet, which depends on the data: it counts from the year-earlier
    value to now with CSS counters, three digits per counter (no JavaScript). Each group is
    floor(n / 1000^k) - 1000 × floor(n / 1000^(k+1)); an <integer> property rounds to the
    nearest integer, so floor(n / d) is written round((n - (d - 1) / 2) / d)."""
    if not animated(data):
        return ''
    a = data.overview()['accounts']
    now, before = int(a['value']), int(a['year_earlier'])
    groups = len(_groups(now))

    def floor_div(k: int) -> str:                       # floor(n / 1000^k)
        d = 1000 ** k
        return 'var(--tick)' if k == 0 else f'calc((var(--tick) - {(d - 1) / 2}) / {d})'   # 499.5, 499999.5

    rules = []
    for i in range(groups):
        k = groups - 1 - i                              # groups to the right of this one
        if i == 0:
            decl = f'--tka:{floor_div(k)};counter-reset:tg var(--tka);content:counter(tg)'
        else:
            decl = (f'--tka:{floor_div(k)};--tkb:{floor_div(k + 1)};--tkc:calc(var(--tka) - 1000 * var(--tkb));'
                    f'counter-reset:tg var(--tkc);content:counter(tg,tick-pad3)')
        rules.append(f'.tick-anim .tg{i}::after{{{decl}}}')
    props = ''.join(f"@property --{name}{{syntax:'<integer>';inherits:false;initial-value:0}}\n" for name in ('tka', 'tkb', 'tkc'))
    return (f'/* Home: the account ticker, generated from data/derived by site/djsite/pages/home.py */\n'
            f"@property --tick{{syntax:'<integer>';inherits:true;initial-value:{now}}}\n{props}"
            f'@counter-style tick-pad3{{system:extends decimal;pad:3 "0"}}\n'
            f'@keyframes tick{{from{{--tick:{before}}}to{{--tick:{now}}}}}\n'
            f'@media (prefers-reduced-motion:no-preference){{@supports (color:rgb(from white r g b)){{\n'
            f'.hero-n .tick-anim{{display:inline;--tick:{now};animation:tick 1.1s var(--ease-io) 1.15s both}}\n'
            f'.hero-n .tick-static{{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}}\n'
            + '\n'.join(rules) + '\n}}\n')


def ticker(ctx, value: int) -> Markup:
    """The account count. Everyone gets the plain number; where motion is welcome and the
    browser can animate it, the stylesheet swaps in a copy that counts up to it."""
    sep = f'<span class="ts">{GROUP[ctx.lang]}</span>'
    static = sep.join(_groups(value))
    anim = ''
    if animated(ctx.site.data):
        anim = '<span class="tick-anim" aria-hidden="true">' + sep.join(
            f'<span class="tg{i}"></span>' for i in range(len(_groups(value)))) + '</span>'
    return Markup(f'<span class="hero-n num" dir="ltr"><span class="tick-static">{static}</span>{anim}</span>')


# ---------------------------------------------------------------- hero
def units_chart(ctx) -> UnitMap:
    data = ctx.site.data
    a = data.overview()['accounts']
    q, before = data.quarter, year_earlier(data.quarter)
    chart = UnitMap(id='home-units', quarter=q, title={}, summary={}, total=int(a['value']), start=int(a['year_earlier']),
                    per=PER)
    squares, added = chart.squares
    per = lambda lang: fint(PER, lang)
    chart.title = ctx.both('home.fig_map', per=per)
    chart.summary = ctx.both('home.map_desc', total=lambda lang: fint(squares, lang), per=per,
                             added=lambda lang: fint(added, lang), quarter=lambda lang: quarter_label(before, lang))
    chart.start_label = {lang: quarter_label(before, lang) for lang in LANGS}
    chart.added_label = ctx.both('home.map_new')
    chart.total_label = {lang: quarter_label(q, lang) for lang in LANGS}
    chart.square_label = ctx.both('home.map_quantity')
    return chart


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def _stat(value: Markup, label, up: bool = False) -> str:
    return f'<div class="hs{" hs-up" if up else ""}"><dt>{label}</dt><dd>{value}</dd></div>'


def figures(ctx) -> list:
    """The hero's three figures, (value, label): growth in a year, the rank for it in North
    Africa and the accounts added. The release's share images show them too (site/tools/share.py)."""
    data = ctx.site.data
    lang = ctx.lang
    ov = data.overview()
    a, y = ov['accounts'], ov['yoy']
    return [(fpct(y['value'], 1, lang, sign=False), ctx.t('home.stat_growth')),
            (rank_text(y['north_africa_rank'], y['north_africa_ranked'], lang), ctx.t('home.stat_rank')),
            (fint(a['value'] - a['year_earlier'], lang, sign=True), ctx.t('home.stat_added', quarter=_q(ctx, year_earlier(data.quarter))))]


def hero(ctx) -> Markup:
    data = ctx.site.data
    lang, q = ctx.lang, data.quarter
    a = data.overview()['accounts']
    (growth, growth_label), (rank, rank_label), (added, added_label) = figures(ctx)
    growth = Markup(f'<span class="num" dir="ltr"><span aria-hidden="true">▲ </span>{esc(growth)}</span>')
    stats = _stat(growth, growth_label, up=True) + _stat(num(rank), rank_label) + _stat(num(added), added_label)

    n, direction, _ = editorial.streak(data.series('yoy', 'DZ'))
    lead = ''
    if direction:
        many, one = ('home.streak_many', 'home.streak_one') if direction > 0 else ('home.slowed_many', 'home.slowed_one')
        lead = ctx.t(many, count=editorial.count_phrase(ctx, n)) if n > 1 else ctx.t(one)
    lede = Markup(f'{lead} {ctx.t("home.map_note", per=fint(PER, lang))}'.strip())
    source = ctx.t('home.source', quarter=_q(ctx, q), date=date_label(data.release_date, lang))

    chart = units_chart(ctx)
    desc = f'{loc(chart.summary, lang)} {ctx.s("chart.desc_table")}'
    label_id = 'home-units-label'
    fig = C.frame(Markup(f'<div class="fig-head">{C.fig_label(ctx, 1, esc(loc(chart.title, lang)), label_id)}</div>'
                         f'<div class="fig-body">{charts.svg(chart, lang, "wide", "home-units-m", desc)}{unit_key(ctx, chart)}</div>'
                         f'{table(ctx, chart)}'), cls='fig hero-fig enter d2', labelledby=label_id)

    return Markup(f'''<section class="hero" aria-labelledby="hero-h">
<div class="hero-bg" aria-hidden="true"></div>
<div class="container hero-grid">
<div class="hero-text">
{C.eyebrow(ctx.t('home.eyebrow', quarter=_q(ctx, q)), cls='enter')}
<h1 id="hero-h" class="hero-h enter d1">{ticker(ctx, int(a['value']))} <span class="hero-tail">{ctx.t('home.h1_tail')}</span></h1>
<dl class="hero-stats enter d2">{stats}</dl>
<p class="lede hero-lede enter d3">{lede}</p>
<div class="hero-ctas enter d4">{C.btn(ctx.t('home.cta_index'), ctx.url('overview'))}{C.btn(ctx.t('home.cta_hub'), ctx.url('hub'), 'secondary', arrow=False)}</div>
<p class="hero-src enter d5">{source} <a class="lnk" href="{ctx.url('methodology')}">{ctx.t('home.how')}</a></p>
</div>
{fig}
</div>
</section>''')


# ---------------------------------------------------------------- scorecard
def scorecard(ctx) -> Markup:
    data = ctx.site.data
    tiles = join(C.tile(n=i, title=ind.title, value=ind.value, chip_html=ind.chip, viz=ind.viz, ranks=ind.ranks,
                        note=ind.note, lang=ctx.lang, href=ctx.url('overview', hash=f'ind-{ind.key}'))
                 for i, ind in enumerate(indicators(ctx), 1))
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/overview.csv') + C.action_link('JSON', f'/data/{folder}/overview.json')
    source = C.source_line(ctx.t('home.score_source', quarter=_q(ctx, data.quarter),
                                 year=data.peers()['DZ']['population_year']), acts)
    return C.section('scorecard', ctx.t('home.score_eyebrow'), ctx.t('home.score_title'),
                     Markup(f'<div class="tiles">{tiles}</div>{source}'),
                     lede=ctx.t('home.score_lede', n=data.overview()['yoy']['africa_ranked']),
                     head_extra=C.btn(ctx.t('home.score_more'), ctx.url('overview'), 'secondary', size='s'))


# ---------------------------------------------------------------- trend
def trend_chart(ctx) -> LineChart:
    data = ctx.site.data
    qs, last = data.quarters, data.quarter
    s = 4                                                   # growth needs a year of history
    series = {key: data.series('yoy', key) for key in ('DZ', 'median_north_africa', 'median_africa')}
    dz = series['DZ']
    at_last = lambda key: (lambda lang: fpct(series[key][-1], 1, lang))
    span = {'from': lambda lang: quarter_label(qs[s], lang), 'to': lambda lang: quarter_label(last, lang)}
    chart = LineChart(
        id='home-yoy', quarter=last,
        title=ctx.both('home.trend_fig', **{'from': qs[s][:4], 'to': last[:4]}),
        summary=ctx.both('home.trend_summary', **span, dz=at_last('DZ'), na=at_last('median_north_africa'),
                         af=at_last('median_africa'), quarter=lambda lang: quarter_label(last, lang)),
        unit=ctx.both('home.trend_unit'), x=qs[s:], fmt=lambda v, lang: fpct(v, 1, lang), tick_fmt=tick_pct,
        lines=[Line('median_africa', ctx.both('home.africa_median'), series['median_africa'][s:], 'median'),
               Line('median_north_africa', ctx.both('home.north_median'), series['median_north_africa'][s:], 'ref'),
               Line('DZ', ctx.both('home.algeria'), dz[s:], 'dz')])
    n, direction, start = editorial.streak(dz)
    if direction > 0 and n > 1 and start >= s:              # point at the low the streak started from
        pct = lambda v: (lambda lang: fpct(v, 1, lang, sign=False))
        chart.notes = [Note(qs[start], 'DZ', ctx.both('home.trend_note', count=lambda lang: editorial.count_phrase(ctx, n, True, lang),
                                                      low=pct(dz[start]), high=pct(dz[-1])), dy=110)]
    return chart


def trend(ctx) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    doc = editorial.current(data)
    title, lede = editorial.text(doc, lang, 'trend_title'), editorial.text(doc, lang, 'trend_lede')
    if title and lede:
        title, lede = esc(title), esc(lede)
    else:
        pct = lambda key: fpct(data.series('yoy', key)[-1], 1, lang, sign=False)
        title = ctx.t('home.trend_title')
        lede = ctx.t('home.trend_lede', dz=pct('DZ'), na=pct('median_north_africa'), af=pct('median_africa'),
                     quarter=_q(ctx, data.quarter))
    fig = figure(ctx, trend_chart(ctx), 2, source=ctx.t('home.trend_source'))
    return C.section('trend', ctx.t('home.trend_eyebrow'), title, fig, lede=lede)


# ---------------------------------------------------------------- Hub teaser
def hub_teaser(ctx) -> Markup:
    issues = ctx.site.hub.issues[:3]
    actions = Markup(f'<div class="section-actions">{C.btn(ctx.t("home.hub_browse"), ctx.url("hub"))}'
                     f'{C.btn(ctx.t("home.hub_list"), ctx.url("hub", hash="list"), "secondary", arrow=False)}</div>')
    if issues:
        inner = Markup(f'<div class="issues">{join(C.issue_card(ctx, i) for i in issues)}</div>')
    else:
        inner = Markup(f'<div class="empty-state"><span class="empty-icon">{icon("plus", 20)}</span>'
                       f'<div class="empty-text"><h3>{ctx.t("home.hub_empty_title")}</h3><p>{ctx.t("home.hub_empty")}</p></div></div>')
    return C.section('hub-teaser', ctx.t('home.hub_eyebrow'), ctx.t('home.hub_title'), inner,
                     lede=ctx.t('home.hub_lede'), head_extra=actions)


# ---------------------------------------------------------------- open by default
def open_row(ctx) -> Markup:
    items = [('table', 'home.open_data', 'home.open_data_sub', 'CC0', ctx.url('data')),
             ('book', 'home.open_method', 'home.open_method_sub', 'CC BY 4.0', ctx.url('methodology')),
             ('code', 'home.open_code', 'home.open_code_sub', 'MIT', REPO_URL)]
    cards = join(f'<a class="card open-card" href="{esc(href)}"><span class="open-icon">{icon(ic, 19)}</span>'
                 f'<span class="open-text"><span class="open-t">{ctx.t(t)}</span><span class="open-s">{ctx.t(sub)}</span></span>'
                 f'<span class="open-lic num" dir="ltr">{lic}</span></a>' for ic, t, sub, lic, href in items)
    return Markup(f'<section class="section section-s open-row" aria-label="{ctx.ta("home.open_label")}">'
                  f'<div class="container"><div class="open-grid">{cards}</div></div></section>')


def render(ctx: Ctx) -> Page:
    body = hero(ctx) + scorecard(ctx) + trend(ctx) + report.teaser(ctx) + hub_teaser(ctx) + open_row(ctx)
    return Page(title=ctx.s('pages.home.title'), description=ctx.s('pages.home.description'), body=Markup(body))
