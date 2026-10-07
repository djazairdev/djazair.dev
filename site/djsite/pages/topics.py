"""Topics (ticket #36, IDX-09, AC-IDX-3): how many repository topics GitHub publishes for
Algeria, the economies' topics above its 100-developer threshold, against the six core peers
and the North African median, a year earlier and since 2020. Then Algeria's own topics, the
largest topics in each peer, and what to keep in mind: topics count labels, not activity.
Every sentence with a figure is computed from the data."""
from __future__ import annotations

from statistics import median

from .. import components as C
from ..charts import HBar, HBarChart, Line, LineChart, tick_int
from ..context import Ctx, Page
from ..figures import figure
from ..fmt import fdec, fint, fpct, num, quarter_label
from ..markup import Markup, esc, join
from ..scorecard import CORE_PEERS, year_earlier
from . import overview

TOP = 5            # topics shown for each peer
STEADY = 4         # quarters with the same count before the sentence says so


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def count(data, code: str, quarter: str = '') -> int:
    """Topics GitHub published for ``code`` in ``quarter`` (default: the latest)."""
    values = data.series('topics', code)
    i = data.quarters.index(quarter) if quarter else -1
    return int(values[i] or 0)


def rows(data, economy: str = 'DZ') -> list:
    """The economy's topics in the latest quarter, largest first."""
    return sorted((r for r in data.rows('topics') if r['economy'] == economy and r['quarter'] == data.quarter),
                  key=lambda r: r['rank'])


def name(topic: str) -> Markup:
    """A topic as GitHub writes it: always left to right, in the monospace face."""
    return Markup(f'<span class="topic-n" lang="en" dir="ltr">{esc(topic)}</span>')


def medians(data) -> dict:
    """The North African and core-peer medians of the topic count, as published."""
    return {'na': data.series('topics', 'median_north_africa')[-1], 'core': data.series('topics', 'median_core_peers')[-1]}


def fmt_median(v, lang: str) -> str:
    """A median: whole, or with one decimal when it falls between two counts (15.5)."""
    return fint(v, lang) if float(v).is_integer() else fdec(v, 1, lang)


# ---------------------------------------------------------------- figure 1: Algeria and the peers
def chart(ctx) -> HBarChart:
    data = ctx.site.data
    q, before = data.quarter, year_earlier(data.quarter)
    quarter = {lang: quarter_label(q, lang) for lang in ('en', 'ar')}
    codes = sorted(('DZ',) + CORE_PEERS, key=lambda c: (-count(data, c), c))
    bars = [HBar(c, ctx.both(f'economy.{c}'), count(data, c), count(data, c, before)) for c in codes]
    return HBarChart(id='topics-peers', quarter=q, title=ctx.both('topics.fig_title', quarter=quarter),
                     summary=ctx.both('topics.fig_summary', quarter=quarter), unit=ctx.both('topics.unit'),
                     bars=bars, fmt=lambda v, lang: fint(v, lang), change_fmt=lambda v, lang: fint(v, lang, sign=True),
                     category_label=ctx.both('topics.category'), now_label=quarter,
                     before_label={lang: quarter_label(before, lang) for lang in ('en', 'ar')},
                     added_label=ctx.both('topics.added'), change_label=ctx.both('topics.change'),
                     highlight='DZ', highlight_label=ctx.both('economy.DZ'), change_kind='diff')


def lede(ctx) -> Markup:
    """Algeria against the North African median, then the three peers with the most topics."""
    data, lang = ctx.site.data, ctx.lang
    n, m = count(data, 'DZ'), medians(data)
    side = 'at' if n == m['na'] else 'above' if n > m['na'] else 'below'
    out = [ctx.t(f'topics.lede_{side}', n=num(fint(n, lang)), quarter=_q(ctx, data.quarter), median=num(fmt_median(m['na'], lang)))]
    top = sorted(CORE_PEERS, key=lambda c: (-count(data, c), c))[:3]
    names = {k: ctx.t(f'economy.{c}') for k, c in zip(('first', 'second', 'third'), top)}
    figures = {k: num(fint(count(data, c), lang)) for k, c in zip('abc', top)}
    out.append(ctx.t('topics.lede_peers', **names, **figures, median=num(fmt_median(m['core'], lang))))
    return Markup(' '.join(str(x) for x in out))


# ---------------------------------------------------------------- figure 2: since 2020
def trend_chart(ctx) -> LineChart:
    data = ctx.site.data
    qs = data.quarters
    first, last = qs[0], qs[-1]
    ql = lambda quarter: (lambda lang: quarter_label(quarter, lang))
    dz = data.series('topics', 'DZ')
    lines = [Line(c, ctx.both(f'economy.{c}'), data.series('topics', c), 'peer') for c in CORE_PEERS]
    lines.append(Line('median_north_africa', ctx.both('trends.na_median'), data.series('topics', 'median_north_africa'), 'median'))
    lines.append(Line('DZ', ctx.both('economy.DZ'), dz, 'dz'))
    return LineChart(id='topics-trend', quarter=last, x=qs, lines=lines, fmt=lambda v, lang: fint(v, lang), tick_fmt=tick_int,
                     title=ctx.both('topics.fig2_title', **{'from': first[:4], 'to': last[:4]}),
                     summary=ctx.both('topics.fig2_summary', **{'from': ql(first), 'to': ql(last)}, last=ql(last),
                                      value=lambda lang: fint(dz[-1], lang)),
                     unit=ctx.both('topics.unit'), peers_label=ctx.both('trends.six_peers'))


# ---------------------------------------------------------------- Algeria's topics
def steady(data) -> tuple:
    """(first, last) quarter of the stretch before the latest quarter in which Algeria's count
    stayed the same, if it lasted at least ``STEADY`` quarters and the latest quarter differs."""
    values, qs = data.series('topics', 'DZ'), data.quarters
    if len(values) < STEADY + 1 or values[-1] == values[-2]:
        return None
    i = len(values) - 2
    while i > 0 and values[i - 1] == values[-2]:
        i -= 1
    return (qs[i], qs[-2]) if len(values) - 1 - i >= STEADY else None


def list_lede(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    m = num(fint(count(data, 'DZ'), lang))
    span = steady(data)
    if span:
        out = [ctx.t('topics.list_steady', **{'from': _q(ctx, span[0]), 'to': _q(ctx, span[1])},
                     n=num(fint(count(data, 'DZ', span[1]), lang)), quarter=_q(ctx, data.quarter), m=m)]
    else:
        out = [ctx.t('topics.list_count', m=m, quarter=_q(ctx, data.quarter),
                     before=num(fint(count(data, 'DZ', year_earlier(data.quarter)), lang)))]
    new = [r['topic'] for r in rows(data) if r['rank_year_earlier'] is None]
    if new:
        out.append(ctx.t('topics.list_new', names=Markup(', '.join(str(name(t)) for t in new))))
    return Markup(' '.join(str(x) for x in out))


def algeria_table(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    head = [(ctx.t('topics.col_topic'), 'start'), (ctx.t('topics.col_pushers'), 'end'),
            (ctx.t('topics.col_before'), 'end'), (ctx.t('topics.col_change'), 'end')]
    body = []
    for r in rows(data):
        missing = ('—', '')
        body.append((r['topic'], [name(r['topic']), (num(fint(r['pushers'], lang)), r['pushers']),
                                  missing if r['pushers_year_earlier'] is None else (num(fint(r['pushers_year_earlier'], lang)), r['pushers_year_earlier']),
                                  missing if r['change'] is None else (num(fpct(r['change'], 1, lang)), r['change'])]))
    table = C.data_table(ctx.t('topics.list_caption', quarter=_q(ctx, data.quarter)), head, body, cls='topics-dz')
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/topics.csv') + C.action_link('JSON', f'/data/{folder}/topics.json')
    src = C.source_line(ctx.t('topics.list_source', quarter=_q(ctx, data.quarter)), acts)
    note = f'<p class="fig-note">{ctx.t("topics.list_note")}</p>'
    return C.section('algeria', ctx.t('topics.list_eyebrow'), ctx.t('topics.list_title'), Markup(f'{table}{note}{src}'),
                     lede=list_lede(ctx), size='s')


# ---------------------------------------------------------------- the peers' topics
def peers_table(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    head = [(ctx.t('overview.col_economy'), 'start'), (ctx.t('topics.col_count'), 'end'), (ctx.t('topics.col_top'), 'start')]
    body = []
    for code in ('DZ',) + CORE_PEERS:
        n = count(data, code)
        top = Markup(f'<span class="topic-list">{join(name(r["topic"]) for r in rows(data, code)[:TOP])}</span>') if n else '—'
        body.append((code, [overview.economy_cell(ctx, code), (num(fint(n, lang)), n), top]))
    m = medians(data)
    foot = [('median_north_africa', [ctx.t('topics.median_na'), (num(fmt_median(m['na'], lang)), m['na']), '']),
            ('median_core_peers', [ctx.t('topics.median_core'), (num(fmt_median(m['core'], lang)), m['core']), ''])]
    table = C.data_table(ctx.t('topics.peers_caption', quarter=_q(ctx, data.quarter)), head, body, cls='topics-peers',
                         highlight='DZ', foot=foot)
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/topics.csv') + C.action_link('JSON', f'/data/{folder}/topics.json')
    src = C.source_line(ctx.t('topics.peers_source', quarter=_q(ctx, data.quarter)), acts)
    return C.section('peers', ctx.t('topics.peers_eyebrow'), ctx.t('topics.peers_title'), Markup(f'{table}{src}'),
                     lede=ctx.t('topics.peers_lede'), size='s')


def read_well(ctx) -> Markup:
    cards = join(f'<div class="limit"><h3>{ctx.t(f"topics.{key}")}</h3><p>{ctx.t(f"topics.{key}_text")}</p></div>'
                 for key in ('rw_labels', 'rw_threshold', 'rw_add', 'rw_size'))
    return C.section('read', ctx.t('topics.read_eyebrow'), ctx.t('topics.read_title'),
                     Markup(f'<div class="limits">{cards}</div>'), size='s')


def head(ctx) -> Markup:
    data = ctx.site.data
    actions = [C.btn(ctx.t('topics.download'), f'/data/{data.folder.name}/topics.csv', arrow=False, attrs=' download'),
               C.btn(ctx.t('topics.methodology'), ctx.url('methodology', hash='topics'), 'secondary')]
    return C.page_head(eyebrow_text=ctx.t('topics.eyebrow'), title=ctx.t('topics.title', quarter=_q(ctx, data.quarter)),
                       lede=ctx.t('topics.lede', a=name('python'), b=name('machine-learning')), meta=overview.meta(ctx),
                       actions=actions)


def render(ctx: Ctx) -> Page:
    data = ctx.site.data
    qs = data.quarters
    fig1 = figure(ctx, chart(ctx), 1, source=ctx.t('topics.source', quarter=_q(ctx, data.quarter)), lede=lede(ctx))
    fig2 = figure(ctx, trend_chart(ctx), 2, source=ctx.t('topics.fig2_source', **{'from': _q(ctx, qs[0]), 'to': _q(ctx, qs[-1])}))
    body = Markup(f'{head(ctx)}<section class="topics-body" aria-label="{ctx.ta("topics.fig_label")}"><div class="container">'
                  f'{fig1}{fig2}</div></section>{algeria_table(ctx)}{peers_table(ctx)}{read_well(ctx)}')
    return Page(title=ctx.s('pages.topics.title'), description=ctx.s('pages.topics.description'), body=body)
