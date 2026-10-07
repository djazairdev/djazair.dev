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
from ..assets import minify_css
from ..charts import Line, LineChart, Note, UnitMap, loc, tick_pct
from ..config import LANGS, REPO_URL
from ..context import Ctx, Page
from ..figures import figure, table, unit_key
from ..fmt import MINUS, date_label, fint, fpct, has_arabic, num, ordinal, quarter_label, rank_text
from ..icons import icon
from ..markup import Markup, esc, join
from ..scorecard import indicators, year_earlier
from . import report

PER = 1000                     # accounts per square on the unit map
GROUP = {'en': ',', 'ar': '.'}  # digit-group separators, as fmt writes them
POINT = {'en': '.', 'ar': ','}  # decimal points, likewise
# The rank as rank_text writes it ('3rd of 7', '3 من 7'), printed with counters; 0 prints '0 of 7'
RANK ={'en': 'counter(tkr,tick-ord) " of " counter(tkn)', 'ar': 'counter(tkr) " من " counter(tkn)'}
# The hero replays the years, in seconds: it holds the first year while the page fades in,
# counts up to each next year, rests on the latest, rewinds, and starts again.
HOLD, FLIP, COUNT, REST, REWIND = 1.4, 1.2, 0.9, 4.0, 0.6


# ---------------------------------------------------------------- the years the hero replays
def history(data) -> list:
    """Algeria's accounts in the same quarter of each year, oldest first, up to the latest:
    [('2020-Q1', 91819), ..., ('2026-Q1', 586990)]."""
    values = zip(data.quarters, data.series('accounts', 'DZ'))
    return [(q, int(v)) for q, v in values if q[-2:] == data.quarter[-2:] and v is not None]


def timeline(years: int) -> tuple:
    """(the loop's length, when each later year starts, when the rewind starts), in seconds
    from the start of the loop."""
    flips = [HOLD + FLIP * k for k in range(years - 1)]
    rewind = HOLD + FLIP * (years - 1) + REST
    return rewind + REWIND, flips, rewind


def year_figures(data, years: list) -> list:
    """The hero's three figures for each year it replays, as numbers: (growth in a year in
    tenths of a per cent, rounded as fpct rounds it; the rank for it among the North African
    economies; how many of them were ranked; the accounts added since the year before). The
    first year has no year before it in the data, so it gets None."""
    north = [k for k, row in data.peers().items() if row['north_africa']]
    growth = {k: dict(zip(data.quarters, data.series('yoy', k))) for k in north}
    out = []
    for i, (q, accounts) in enumerate(years):
        g = growth['DZ'].get(q)
        if i == 0 or g is None:
            out.append(None)
            continue
        ranked = [v for v in (growth[k].get(q) for k in north) if v is not None]
        tenths = int(f'{abs(g) * 100:.1f}'.replace('.', ''))
        out.append((-tenths if g < 0 else tenths, 1 + sum(v > g for v in ranked), len(ranked), accounts - years[i - 1][1]))
    return out


def figure_text(row: tuple, lang: str) -> tuple:
    """A year's three figures as the hero writes them: ('▲ 44.6%', '6th of 7', '+40,925')."""
    growth, rank, ranked, added = row
    return (f'{"▼" if growth < 0 else "▲"} {fpct(abs(growth) / 1000, 1, lang, sign=False)}',
            rank_text(rank, ranked, lang), fint(added, lang, sign=True))


def _groups(value: int) -> list:
    return f'{value:,}'.split(',')


def _width(years: list) -> int:
    """The most digit groups the count has in a year."""
    return max(len(_groups(v)) for _, v in years)


def hero_css(lang: str, years: list, stats: list = ()) -> str:
    """Home's own stylesheet, generated from the data: with CSS only, the hero replays the
    years. The count goes up to each year's value as the year above it turns over, the map
    adds that year's squares, and the three figures under the number (``stats``, from
    ``year_figures``) count up or down to that year's in step.

    Each of these four numbers is a registered <integer> property, --tick, that keyframes take
    through the years. CSS can't print a property, but it can print counters: each group of
    three digits is worked out from --tick and printed with its separator and leading zeros,
    and counter styles print nothing for a group that is still 0, so a number can gain a digit
    group on the way. An <integer> property rounds to the nearest integer, so floor(n / d) is
    written round((n - (d - 1) / 2) / d). The signs, the growth's tenths and the rank's
    ordinal are counters too, and so is the year; each year's squares have keyframes of their
    own."""
    if len(years) < 2:
        return ''
    length, flips, rewind = timeline(len(years))

    def at(t: float) -> str:                            # a time in the loop, as a keyframe
        return f'{100 * t / length:.3f}'.rstrip('0').rstrip('.') + '%'

    def floor_div(k: int) -> str:                       # floor(|n| / 1000^k), from --tm, which is |--tick|
        d = 1000 ** k
        return 'var(--tm)' if k == 0 else f'calc((var(--tm) - {(d - 1) / 2}) / {d})'   # 499.5, 499999.5

    def counting(rows: list) -> str:
        """Keyframes that hold each year's values, count to the next year's as it turns over and
        count back to the first year's in the rewind. A row is a year's {property: value}."""
        props = lambda row: ';'.join(f'--{name}:{value}' for name, value in row.items())
        frames = [f'0%{{{props(rows[0])}}}']
        for k, t in enumerate(flips, 1):
            frames += [f'{at(t)}{{{props(rows[k - 1])}}}', f'{at(t + COUNT)}{{{props(rows[k])}}}']
        return ''.join(frames) + f'{at(rewind)}{{{props(rows[-1])}}}100%{{{props(rows[0])}}}'

    text = lambda v: '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'     # as a CSS string
    values = [v for _, v in years]
    yr = [int(q[:4]) for q, _ in years]
    prefix = quarter_label(years[-1][0], lang).removesuffix(str(yr[-1]))   # 'Q1 ', 'الربع الأول ': the year comes last
    year, steps, rules = [f'0%{{--yr:{yr[0]}}}'], [], []
    glow = 'drop-shadow(0 0 5px var(--mint-glow))'
    for k, t in enumerate(flips, 1):
        year += [f'{at(t)}{{--yr:{yr[k - 1]};opacity:1;transform:none}}',
                 f'{at(t + .01)}{{--yr:{yr[k]};opacity:0;transform:translateY(.4em);animation-timing-function:var(--ease)}}',
                 f'{at(t + .4)}{{opacity:1;transform:none}}']
        # Year k's squares flash in and settle to mint, dim to the earlier years' colour when the
        # next year comes, and fade out in the rewind; the latest year stays bright to the end.
        latest = k == len(flips)
        dim = '' if latest else f'{at(flips[k])}{{fill:var(--mint)}}{at(flips[k] + .5)}{{fill:var(--cell-old)}}'
        unlit = (f'{at(flips[k])}{{filter:{glow}}}{at(flips[k] + .5)}{{filter:none}}' if not latest
                 else f'{at(rewind)}{{filter:{glow}}}{at(rewind + .45)}{{filter:none}}')
        steps.append(f'@keyframes um-s{k}{{0%,{at(t)}{{opacity:0;fill:var(--cell-flash);stroke-width:3}}'
                     f'{at(t + .15)}{{fill:var(--cell-flash)}}{at(t + .3)}{{opacity:1}}{at(t + .55)}{{stroke-width:0}}'
                     f'{at(t + .75)}{{fill:var(--mint)}}{dim}{at(rewind)}{{opacity:1}}{at(rewind + .45)}{{opacity:0}}'
                     f'100%{{opacity:0;stroke-width:0;fill:var({"--mint" if latest else "--cell-old"})}}}}\n'
                     f'@keyframes um-g{k}{{0%,{at(t + .2)}{{filter:none}}{at(t + .75)}{{filter:{glow}}}{unlit}100%{{filter:none}}}}\n')
        rules.append(f'.um-years .s{k}{{animation:um-g{k} {length:g}s var(--ease) infinite both}}'
                     f'.um-years .s{k}>g{{stroke:var(--cell-flash);animation:um-s{k} {length:g}s var(--ease) infinite both;'
                     f'animation-delay:calc(var(--b,0) * 24ms)}}\n')
    year += [f'{at(rewind)}{{--yr:{yr[-1]}}}', f'100%{{--yr:{yr[0]}}}']

    # The figures under the count: the first year has none, so they wait at 0, muted, and light
    # up as it turns over. Then each figure counts to the next year's with the count, and back
    # to 0 in the rewind.
    counts, turns = '', ''
    if len(stats) == len(years) and None not in stats[1:]:
        later = stats[1:]
        rows = ([{'tick': 0}] + [{'tick': g} for g, _, _, _ in later],
                [{'tick': 0, 'tn': later[0][2]}] + [{'tick': r, 'tn': n} for _, r, n, _ in later],
                [{'tick': 0}] + [{'tick': a} for _, _, _, a in later])
        lit = (f'0%,{at(flips[0])}{{opacity:.4}}{at(flips[0] + .25)}{{opacity:1}}'
               f'{at(length - .25)}{{opacity:1}}100%{{opacity:.4}}')
        ordinals = ' '.join(text(ordinal(n)) for n in range(1, max(n for _, _, n, _ in later) + 1))
        counts = (''.join(f'@keyframes hero-f{i}{{{counting(r)}}}\n' for i, r in enumerate(rows))
                  + f'@keyframes hero-on{{{lit}}}\n'
                  '@counter-style tick-arrow{system:fixed 0;symbols:"▼ " "▲ " "▲ "}\n'
                  f'@counter-style tick-sign{{system:fixed 0;symbols:"{MINUS}" "" "+"}}\n'
                  + (f'@counter-style tick-ord{{system:fixed 1;symbols:{ordinals}}}\n' if 'tick-ord' in RANK[lang] else ''))
        widest = [max(column, key=len) for column in zip(*(figure_text(row, lang) for row in later))]
        run = lambda i: f'animation:hero-f{i} {length:g}s var(--ease-io) infinite both,hero-on {length:g}s linear infinite both'
        turns = ('.hero-stats .hs-v{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}\n'
                 # each figure counts over its widest value, which keeps the width
                 '.hero-stats .hs-a{display:inline-grid}.hs-a::before,.hs-a>span{display:block;grid-area:1/1}.hs-a::before{visibility:hidden}\n'
                 + ''.join(f'.hv{i}::before{{content:{text(w)}}}' for i, w in enumerate(widest)) + '\n'
                 '.hs-c{--ts:calc(clamp(-1,var(--tick),1) + 1)}\n'                # the sign: 0 below zero, 1 at zero, 2 above
                 # growth, in tenths of a per cent: the arrow, the whole per cents and the tenths
                 f'.hv0 .hs-c{{{run(0)};--ti:calc((var(--tm) - 4.5) / 10);--tf:calc(var(--tm) - 10 * var(--ti))}}\n'
                 '.hv0 .hs-c::after{counter-reset:tka var(--ts) tki var(--ti) tkf var(--tf);'
                 f'content:counter(tka,tick-arrow) counter(tki) "{POINT[lang]}" counter(tkf) "%"}}\n'
                 f'.hv1 .hs-c{{{run(1)}}}.hv1 .hs-c::after{{counter-reset:tkr var(--tick) tkn var(--tn);content:{RANK[lang]}}}\n'
                 # the accounts added: the sign, then digit groups as the count's
                 f'.hv2 .hs-c{{{run(2)}}}.hv2 .hs-c::before{{counter-reset:tka var(--ts);content:counter(tka,tick-sign)}}\n')

    width = _width(years)
    digits = ''.join(f'.tick-anim .tg{i}{{--ta:{floor_div(width - 1 - i)};--th:{floor_div(width - i)}}}' for i in range(width))
    last = f'.tick-anim .tg{width - 1}'
    props = ''.join(f"@property --{name}{{syntax:'<integer>';inherits:true;initial-value:{value}}}\n"
                    for name, value in (('tick', values[-1]), ('yr', yr[-1]), ('tm', 0), ('ta', 0), ('th', 0), ('tg', 0), ('tl', 0),
                                        ('td', 0), ('tz', 0), ('ts', 0), ('ti', 0), ('tf', 0), ('tn', 0)))
    squares = ','.join(f'.s{k}' for k in range(1, len(years)))
    return ('/* Home: the hero replays the years, generated from data/derived by site/djsite/pages/home.py */\n'
            + props
            + f'@counter-style tick-sep{{system:fixed 0;symbols:"" "{GROUP[lang]}"}}\n'
            '@counter-style tick-zeros{system:fixed 0;symbols:"" "0" "00" "000"}\n'
            '@counter-style tick-blank{system:fixed 0;symbols:""}\n'
            '@counter-style tick-digits{system:extends decimal;range:1 infinite;fallback:tick-blank}\n'
            f'@keyframes hero-tick{{{counting([{"tick": v} for v in values])}}}\n@keyframes hero-yr{{{"".join(year)}}}\n'
            + ''.join(steps) + counts
            + '@media (prefers-reduced-motion:no-preference){@supports (color:rgb(from white r g b)){\n'
            f'.hero-n .tick-anim{{display:inline;animation:hero-tick {length:g}s var(--ease-io) infinite both}}\n'
            '.hero-n .tick-static{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}\n'
            # each digit group of a number: this group's value, whether digits come before it (then it
            # takes its separator and leading zeros), and how many digits it has without them; the
            # last group always has one, so a number at 0 prints 0
            '.tick-anim,.hs-c{--tm:max(var(--tick),-1 * var(--tick))}\n'
            + digits + '\n'
            '.tick-anim span{--tg:calc(var(--ta) - 1000 * var(--th));--tl:clamp(0,var(--th),1);'
            '--td:calc(clamp(0,var(--tg),1) + clamp(0,var(--tg) - 9,1) + clamp(0,var(--tg) - 99,1));--tz:calc(var(--tl) * (3 - var(--td)))}\n'
            f'{last}{{--td:calc(1 + clamp(0,var(--tg) - 9,1) + clamp(0,var(--tg) - 99,1))}}\n'
            '.tick-anim span::before{counter-reset:tks var(--tl);content:counter(tks,tick-sep)}'
            '.hero-n .tick-anim span::before{margin-inline:calc(var(--tl) * -.16em)}\n'
            '.tick-anim span::after{counter-reset:tkz var(--tz) tkg var(--tg);content:counter(tkz,tick-zeros) counter(tkg,tick-digits)}\n'
            f'{last}::after{{content:counter(tkz,tick-zeros) counter(tkg)}}\n'
            '.hero-when .yr-static{display:none}\n'
            f'.hero-when .yr-anim{{display:inline-block;counter-reset:yr var(--yr);animation:hero-yr {length:g}s linear infinite both}}\n'
            f'.hero-when .yr-anim::after{{content:"{prefix}" counter(yr)}}\n'
            '.hero-pause{display:inline-flex}\n'
            + turns
            # the first year's squares grow in as the page loads (90-motion.css); the later years' are this loop's
            + f'.um.um-years :is({squares}) rect{{animation:none}}\n'
            + ''.join(rules)
            + '.hero:is(.hero-idle,:has(.hero-pause input:checked)) :is(.tick-anim,.yr-anim,.um-years g,.um-years rect,.hs-a span)'
            '{animation-play-state:paused}\n}}\n')


# ---------------------------------------------------------------- the account ticker
def ticker(ctx, value: int, years: list) -> Markup:
    """The account count. Everyone gets the plain number; where motion is welcome and the
    browser can animate it, the page's stylesheet swaps in a copy that counts through the years."""
    sep = f'<span class="ts">{GROUP[ctx.lang]}</span>'
    static = sep.join(_groups(value))
    anim = ''
    if len(years) > 1:
        anim = '<span class="tick-anim" aria-hidden="true">' + ''.join(f'<span class="tg{i}"></span>' for i in range(_width(years))) + '</span>'
    return Markup(f'<span class="hero-n num" dir="ltr"><span class="tick-static">{static}</span>{anim}</span>')


def when(ctx, years: list) -> Markup:
    """Above the count, the quarter it is for: the latest, or the year the replay has reached,
    beside a button that pauses the replay (WCAG 2.2.2)."""
    if len(years) < 2:
        anim = pause = ''
    else:
        anim = '<span class="yr-anim"></span>'
        pause = (f'<label class="hero-pause"><input class="sr-only" type="checkbox">{icon("pause", 16, 2, "icon i-pause")}'
                 f'{icon("play", 16, 2, "icon i-play")}<span class="sr-only">{ctx.t("home.pause")}</span></label>')
    return Markup(f'<div class="hero-when"><span class="hero-yr" aria-hidden="true"><span class="yr-static">'
                  f'{quarter_label(ctx.site.data.quarter, ctx.lang)}</span>{anim}</span>{pause}</div>')


# ---------------------------------------------------------------- hero
def units_chart(ctx) -> UnitMap:
    """The hero's unit map, drawn a year at a time for the replay."""
    data = ctx.site.data
    a = data.overview()['accounts']
    q, before = data.quarter, year_earlier(data.quarter)
    years = history(data)
    chart = UnitMap(id='home-units', quarter=q, title={}, summary={}, total=int(a['value']), start=int(a['year_earlier']),
                    per=PER, history=tuple(years) if len(years) > 1 else ())
    squares, added = chart.squares
    first, first_squares = years[0][0], (chart.steps() or (squares,))[0]
    per = lambda lang: fint(PER, lang)
    chart.title = ctx.both('home.fig_map', per=per)
    chart.summary = ctx.both('home.map_desc_years', per=per, first=lambda lang: quarter_label(first, lang),
                             first_total=lambda lang: fint(first_squares, lang), last=lambda lang: quarter_label(q, lang),
                             total=lambda lang: fint(squares, lang), added=lambda lang: fint(added, lang),
                             quarter=lambda lang: quarter_label(before, lang))
    chart.start_label = ctx.both('home.map_earlier')
    chart.added_label = ctx.both('home.map_new_year')
    chart.total_label = {lang: quarter_label(q, lang) for lang in LANGS}
    chart.square_label = ctx.both('home.map_quantity')
    return chart


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def _stat(value: Markup, label, up: bool = False) -> str:
    return f'<div class="hs{" hs-up" if up else ""}"><dt>{label}</dt><dd>{value}</dd></div>'


def figures(ctx) -> list:
    """The hero's three figures, (value, label): growth in a year, the rank for it in North
    Africa and the accounts added. The release's share images show them too (site/tools/share.py);
    the hero labels the last one without a quarter, since it follows the year it replays."""
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
    years = history(data)
    (growth, growth_label), (rank, rank_label), (added, _) = figures(ctx)

    def each_year(i: int, latest: str) -> str:
        """Where the replay counts the figure through the years, printed by Home's stylesheet; the
        accounts added in digit groups, as the count above."""
        if len(years) < 2:
            return ''
        cls, direction = ('num nums', 'rtl') if has_arabic(latest) else ('num', 'ltr')     # as num() would
        groups = ''.join(f'<span class="tg{g}"></span>' for g in range(_width(years))) if i == 2 else ''
        return (f'<span class="hs-a hv{i} {cls}" dir="{direction}" aria-hidden="true">'
                f'<span class="hs-c{" tick-anim" if groups else ""}">{groups}</span></span>')

    growth_html = f'<span class="num hs-v" dir="ltr"><span aria-hidden="true">▲ </span>{esc(growth)}</span>'
    stats = (_stat(Markup(growth_html + each_year(0, growth)), growth_label, up=True)
             + _stat(Markup(num(rank, 'num hs-v') + each_year(1, rank)), rank_label)
             + _stat(Markup(num(added, 'num hs-v') + each_year(2, added)), ctx.t('home.stat_added_year')))

    n, direction, _ = editorial.streak(data.series('yoy', 'DZ'))
    lead = ''
    if direction:
        many, one = ('home.streak_many', 'home.streak_one') if direction > 0 else ('home.slowed_many', 'home.slowed_one')
        lead = ctx.t(many, count=editorial.count_phrase(ctx, n)) if n > 1 else ctx.t(one)
    lede = Markup(f'{lead} {ctx.t("home.map_note", per=fint(PER, lang), first=years[0][0][:4])}'.strip())
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
<div class="hero-count enter d1">{when(ctx, years)}
<h1 id="hero-h" class="hero-h">{ticker(ctx, int(a['value']), years)} <span class="hero-tail">{ctx.t('home.h1_tail')}</span></h1></div>
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
    years = history(ctx.site.data)
    return Page(title=ctx.s('pages.home.title'), description=ctx.s('pages.home.description'), body=Markup(body),
                css=minify_css(hero_css(ctx.lang, years, year_figures(ctx.site.data, years))))   # Home's alone
