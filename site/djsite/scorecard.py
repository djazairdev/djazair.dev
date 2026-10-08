"""The six headline indicators, as the Home scorecard and the Index overview show them
(tickets #18 and #19; PRD §9.2). Every value comes from the derived data.

Each ``Indicator`` holds what both pages need: the value, a chip comparing it with a peer
median, a sparkline or bars, Algeria's ranks, a note, the medians and what it measures.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import components as C
from .charts import hbars, spark
from .fmt import fdec, fint, fpct, num, quarter_label
from .markup import Markup, esc

CORE_PEERS = ('MA', 'TN', 'EG', 'NG', 'KE', 'ZA')
NORTH_AFRICA = ('DZ', 'EG', 'LY', 'MA', 'MR', 'SD', 'TN')
AFRICA_MIN_ACCOUNTS = 20_000    # the Africa ranking group's minimum, as in pipeline/config.py
NAMES = ('DZ', 'EG', 'LY', 'MA', 'MR', 'SD', 'TN', 'NG', 'KE', 'ZA')
SAME = 0.005                     # within half a per cent of the median reads "= median"


@dataclass
class Indicator:
    key: str                     # accounts, pushes, repos, orgs, topics, permillion
    title: Markup
    value: str
    chip: Markup
    viz: Markup
    ranks: list                  # [(label, rank, of)]
    note: Markup
    medians: list = field(default_factory=list)   # [(label, text)]
    delta: Markup = Markup('')                    # change on a year earlier (overview)
    does: list = field(default_factory=list)
    doesnt: list = field(default_factory=list)


def name(ctx, code: str) -> Markup:
    return ctx.t(f'economy.{code}')


def year_earlier(q: str) -> str:
    year, n = q.split('-Q')
    return f'{int(year) - 1}-Q{n}'


def _chip(ctx, figure: str, words_key: str, kind: str = 'flat', **values) -> Markup:
    """A chip with a figure and words: mono and left to right in English; in Arabic the words
    read right to left and the figure is isolated."""
    fig = esc(figure) if ctx.en else num(figure)
    return C.chip(Markup(f'{fig} {ctx.t(words_key, **values)}'), kind)


def _vs_median(ctx, value, median) -> Markup:
    change = value / median - 1
    if abs(change) < SAME:
        return C.chip(ctx.t('ind.eq_na'), 'flat')
    return _chip(ctx, fpct(change, 0, ctx.lang), 'ind.vs_na')


def _vs_peers(ctx, value, median) -> Markup:
    return _chip(ctx, fpct(value / median - 1, 0, ctx.lang), 'ind.vs_peers')


def _year_chip(ctx, now, before, quarter: str) -> Markup:
    change = now / before - 1
    arrow = '▲' if change >= 0 else '▼'
    q = quarter_label(year_earlier(quarter), ctx.lang, 'short')
    return _chip(ctx, f'{arrow} {fpct(abs(change), 0, ctx.lang, sign=False)}', 'ind.vs_q', quarter=q)


def _spark(ctx, data, indicator: str, median: bool) -> Markup:
    q = data.quarters
    values = data.series(indicator, 'DZ')
    svg = spark(values, data.series(indicator, 'median_north_africa') if median else None)
    return C.spark_block(svg, quarter_label(q[0], ctx.lang, 'axis'), quarter_label(q[-1], ctx.lang, 'axis'))


def _bars(ctx, peers: dict, field_: str, fmt) -> Markup:
    """Algeria and the three core peers with the highest values."""
    top = sorted((c for c in CORE_PEERS if peers[c][field_] is not None), key=lambda c: -peers[c][field_])[:3]
    rows = [(c, peers[c][field_]) for c in top] + [('DZ', peers['DZ'][field_])]
    names = {c: name(ctx, c) for c in NAMES}
    return hbars(rows, fmt, names)


def indicators(ctx) -> list:
    """The six indicators for ``ctx.lang``, in the order the pages show them."""
    data = ctx.site.data
    ov, peers = data.overview(), data.peers()
    lang, quarter = ctx.lang, data.quarter
    na, af, ap = ctx.t('ind.north_africa'), ctx.t('ind.africa'), ctx.t('ind.algeria_peers')
    ranks = lambda row: [(na, row['north_africa_rank'], row['north_africa_ranked']),
                         (af, row['africa_rank'], row['africa_ranked'])]
    meds = lambda row, f: [(ctx.t('ind.med_na'), f(row['north_africa_median'])), (ctx.t('ind.med_cp'), f(row['core_peers_median'])),
                           (ctx.t('ind.med_af', n=row['africa_ranked']), f(row['africa_median']))]
    a, y = ov['accounts'], ov['yoy']
    p, r, o = ov['pushes_per_account'], ov['repos_per_account'], ov['orgs_per_account']
    t, pm = ov['topics'], ov['accounts_per_million']
    d2 = lambda v: fdec(v, 2, lang)
    d4 = lambda v: fdec(v, 4, lang)
    up_chip = _chip(ctx, f'▲ {fpct(y["value"], 1, lang, sign=False)}', 'ind.in_year', 'up')
    out = [
        Indicator('accounts', ctx.t('ind.accounts.title'), fint(a['value'], lang), up_chip, _spark(ctx, data, 'accounts', False),
                  ranks(a), ctx.t('ind.accounts.note', median=num(fint(a['north_africa_median'], lang))),
                  meds(a, lambda v: fint(v, lang))),
        Indicator('pushes', ctx.t('ind.pushes.title'), d2(p['value']), _vs_median(ctx, p['value'], p['north_africa_median']),
                  _spark(ctx, data, 'pushes_per_account', True), ranks(p),
                  ctx.t('ind.pushes.note', avg=num(d2(ov['pushes_per_account_4q']['value'])), median=num(d2(p['north_africa_median']))),
                  meds(p, d2), _year_chip(ctx, p['value'], p['year_earlier'], quarter)),
        Indicator('repos', ctx.t('ind.repos.title'), d2(r['value']), _vs_median(ctx, r['value'], r['north_africa_median']),
                  _spark(ctx, data, 'repos_per_account', True), ranks(r),
                  ctx.t('ind.median_note', median=num(d2(r['north_africa_median']))), meds(r, d2),
                  _year_chip(ctx, r['value'], r['year_earlier'], quarter)),
        Indicator('orgs', ctx.t('ind.orgs.title'), d4(o['value']), _vs_median(ctx, o['value'], o['north_africa_median']),
                  _spark(ctx, data, 'orgs_per_account', True), ranks(o),
                  ctx.t('ind.median_note', median=num(d4(o['north_africa_median']))), meds(o, d4),
                  _year_chip(ctx, o['value'], o['year_earlier'], quarter)),
        Indicator('topics', ctx.t('ind.topics.title'), fint(t['value'], lang), _vs_peers(ctx, t['value'], t['core_peers_median']),
                  _bars(ctx, peers, 'topics', lambda v: fint(v, lang)),
                  [(ap, t['algeria_and_peers_rank'], t['algeria_and_peers_ranked'])], ctx.t('ind.topics.note'),
                  [(ctx.t('ind.med_cp'), fdec(t['core_peers_median'], 1, lang))]),
        Indicator('permillion', ctx.t('ind.permillion.title'), fint(pm['value'], lang),
                  _vs_peers(ctx, pm['value'], pm['core_peers_median']),
                  _bars(ctx, peers, 'accounts_per_million', lambda v: fint(v, lang)),
                  [(ap, pm['algeria_and_peers_rank'], pm['algeria_and_peers_ranked'])],
                  ctx.t('ind.permillion.note', year=num(str(peers['DZ']['population_year']))),
                  [(ctx.t('ind.med_cp'), fint(pm['core_peers_median'], lang))]),
    ]
    for ind in out:
        ind.does, ind.doesnt = ctx.tl(f'ind.{ind.key}.does'), ctx.tl(f'ind.{ind.key}.doesnt')
    return out
