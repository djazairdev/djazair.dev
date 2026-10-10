"""Peers (ticket #21, IDX-06): Algeria, the six core peers and the group medians,
then rank tables for North Africa (all seven) and Africa (economies with at least
20,000 accounts a year earlier; PRD §9.3). Ranks come from the derived ranks table: 1 is the
highest and ties share a place. Every table sorts by keyboard and announces its new order
(site.js); without JavaScript the rank tables keep their order by accounts."""
from __future__ import annotations

from .. import components as C
from ..context import Ctx, Page
from ..fmt import fint, num, quarter_label
from ..markup import Markup, join
from ..scorecard import AFRICA_MIN_ACCOUNTS
from . import overview
from .overview import COLUMNS

# (group in the derived data, section id, string prefix, median label)
GROUPS = (('north_africa', 'north-africa', 'na', 'overview.med_na'), ('africa', 'africa', 'af', 'overview.med_af'))


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def group_row(data, group: str) -> dict:
    """The group's row in the groups table for the latest quarter: members and medians."""
    return next(r for r in data.rows('groups') if r['group'] == group and r['quarter'] == data.quarter)


def ranks(data, group: str) -> dict:
    """{economy: {indicator: ranks row}} for the latest quarter."""
    out = {}
    for r in data.rows('ranks'):
        if r['group'] == group and r['quarter'] == data.quarter:
            out.setdefault(r['economy'], {})[r['indicator']] = r
    return out


def head(ctx) -> Markup:
    data = ctx.site.data
    folder = data.folder.name
    actions = [C.btn(ctx.t('peers.download'), f'/data/{folder}/ranks.csv', arrow=False, attrs=' download'),
               C.btn(ctx.t('peers.methodology'), ctx.url('data', hash='peer-groups'), 'secondary')]
    return C.page_head(eyebrow_text=ctx.t('peers.eyebrow'), title=ctx.t('peers.title', quarter=_q(ctx, data.quarter)),
                       lede=ctx.t('peers.lede', n=group_row(data, 'africa')['members']), meta=overview.meta(ctx),
                       actions=actions)


def rank_table(ctx, group: str, id_: str, short: str, median: str) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    by = ranks(data, group)
    g = group_row(data, group)
    members = g['economies'].split()
    gap = Markup('<span class="rk rk-gap" aria-hidden="true"></span>')

    def cell(code: str, key: str, fmt) -> tuple:
        r = by.get(code, {}).get(key)
        if r is None or r['value'] is None:
            return Markup(f'—{gap}'), ''
        rank = (f'<span class="rk" aria-hidden="true">{r["rank"]}</span>'
                f'<span class="sr-only"> {ctx.t("peers.rank_sr", rank=r["rank"], of=r["ranked"])}</span>')
        return Markup(f'{num(fmt(r["value"], lang))}{rank}'), r['value']

    def by_accounts(code: str) -> tuple:
        r = by.get(code, {}).get('accounts')
        return (r['rank'] if r else len(members) + 1, ctx.s(f'economy.{code}'))

    rows = [(code, [overview.economy_cell(ctx, code)] + [cell(code, key, fmt) for key, _, fmt in COLUMNS])
            for code in sorted(members, key=by_accounts)]
    medians = [Markup(f'{num(fmt(g[f"median_{key}"], lang))}{gap}') if g.get(f'median_{key}') is not None else Markup(f'—{gap}')
               for key, _, fmt in COLUMNS]
    foot = [(f'median_{group}', [ctx.t(median, n=g['members'])] + medians)]
    caption = ctx.t('peers.caption', group=ctx.s(f'peers.group_{short}'), quarter=_q(ctx, data.quarter))
    table = C.data_table(caption, overview.table_head(ctx), rows, sortable=True, cls='rank-wrap', highlight='DZ',
                         sorted_by=(1, 'descending'), foot=foot, announce=C.sort_text(ctx))
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/ranks.csv') + C.action_link('JSON', f'/data/{folder}/ranks.json')
    year = data.peers()['DZ']['population_year']
    src = C.source_line(ctx.t('peers.source', quarter=_q(ctx, data.quarter), year=year), acts)
    lede = ctx.t(f'peers.{short}_lede', n=g['members'], min=fint(AFRICA_MIN_ACCOUNTS, lang), quarter=_q(ctx, data.quarter))
    return C.section(id_, ctx.t(f'peers.{short}_eyebrow'), ctx.t(f'peers.{short}_title', n=g['members']),
                     Markup(f'{table}{src}'), lede=lede, size='s')


def render(ctx: Ctx) -> Page:
    body = join([head(ctx), overview.peers_table(ctx, lede=ctx.t('peers.core_lede'))]
                + [rank_table(ctx, *group) for group in GROUPS])
    return Page(title=ctx.s('pages.peers.title'), description=ctx.s('pages.peers.description'), body=Markup(body))
