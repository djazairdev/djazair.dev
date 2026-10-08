"""External rankings (ticket #38, IDX-11, PRD Appendix A.6): GitHub's one-off GDC26 ranking of
African economies by git pushes per 1,000 working-age people, corrected for VPN use, labelled
as GitHub's dataset. Algeria isn't in it, so its bar is djazair.dev's estimate, drawn as an
outline and named as an estimate everywhere it appears. Then how the estimate is made, the
same estimate for the economies GitHub lists, to show how far it can be off, and what to
keep in mind. Every sentence with a figure is computed from the ``gdc26`` table."""
from __future__ import annotations

import math

from .. import components as C
from .. import outlook
from ..charts import HBar, HBarChart
from ..context import Ctx, Page
from ..figures import figure
from ..fmt import and_list, date_label, fdec, fint, num, ordinal, quarter_label
from ..markup import Markup, join
from ..scorecard import CORE_PEERS, NORTH_AFRICA
from . import collaboration

QUARTERS = ('2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2')      # GitHub's four quarters
OUTLIER = 0.25          # GitHub's figure this far from the estimate (as a share) is named, not counted as close


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def rows(data, kind: str) -> list:
    """The ``gdc26`` rows of one list: 'africa', 'world' or 'estimate'."""
    return [r for r in data.rows('gdc26') if r['list'] == kind]


def estimates(data) -> dict:
    return {r['economy']: r for r in rows(data, 'estimate')}


def period(ctx) -> str:
    return f'{_q(ctx, QUARTERS[0])} – {_q(ctx, QUARTERS[-1])}'


def whole(v, lang: str) -> str:
    """Per-1,000 figures as GitHub's ranking reads: whole numbers."""
    return fint(round(v), lang)


def rank_text(ctx, rank: int) -> str:
    return ordinal(rank) if ctx.en else str(rank)


def item(ctx, code: str, rank: int) -> Markup:
    return ctx.t('rankings.na_item', name=collaboration.cell_name(ctx, code), rank=num(rank_text(ctx, rank)))


# ---------------------------------------------------------------- figure: GitHub's top ten and Algeria's estimate
def chart(ctx) -> HBarChart:
    data = ctx.site.data
    span = {lang: f'{quarter_label(QUARTERS[0], lang)} – {quarter_label(QUARTERS[-1], lang)}' for lang in ('en', 'ar')}
    bars = [HBar(r['economy'], collaboration.label(ctx, r['economy']), r['per_1k_working_age'], rank=r['rank'])
            for r in rows(data, 'africa')]
    dz = estimates(data).get('DZ')
    if dz:
        bars.append(HBar('DZ', ctx.both('rankings.dz_label'), dz['per_1k_working_age'], estimate=True))
    return HBarChart(id='rankings-africa', quarter=data.quarter, title=ctx.both('rankings.fig_title', period=span),
                     summary=ctx.both('rankings.fig_summary', period=span), unit=ctx.both('rankings.unit'), bars=bars,
                     fmt=whole, change_fmt=lambda v, lang: '', category_label=ctx.both('rankings.category'),
                     now_label=ctx.both('rankings.unit'), highlight='DZ', split=False,
                     source='GitHub GDC26 supplementary data; Algeria: djazair.dev estimate')


def lede(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    africa = rows(data, 'africa')
    (first, second, third), tenth = africa[:3], africa[-1]
    out = [ctx.t('rankings.lede_top', first=collaboration.cell_name(ctx, first['economy']),
                 a=num(whole(first['per_1k_working_age'], lang)), second=collaboration.cell_name(ctx, second['economy']),
                 b=num(whole(second['per_1k_working_age'], lang)), third=collaboration.cell_name(ctx, third['economy']),
                 c=num(whole(third['per_1k_working_age'], lang)))]
    na = [r for r in africa if r['economy'] in NORTH_AFRICA]
    if na:
        out.append(ctx.t('rankings.lede_na', list=Markup(and_list([item(ctx, r['economy'], r['rank']) for r in na], lang))))
    dz = estimates(data).get('DZ')
    if dz and 'DZ' not in [r['economy'] for r in africa]:
        out.append(ctx.t('rankings.lede_dz', dz=num(whole(dz['per_1k_working_age'], lang)),
                         t=num(whole(tenth['per_1k_working_age'], lang)), tenth=collaboration.cell_name(ctx, tenth['economy'])))
    return Markup(' '.join(str(x) for x in out))


def world_note(ctx) -> Markup:
    """GitHub's other list, the 30 with the most pushes: which African economies it has."""
    found = [r for r in rows(ctx.site.data, 'world') if r['region'] == 'Africa']
    if not found:
        return ctx.t('rankings.world_none')
    return ctx.t('rankings.world_note', list=Markup(and_list([item(ctx, r['economy'], r['rank']) for r in found], ctx.lang)))


# ---------------------------------------------------------------- how the estimate is made
def estimate_section(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    dz = estimates(data)['DZ']
    released = [q for q in QUARTERS if q in data.quarters]
    latest = released[-1]
    head = [(ctx.t('rankings.est_col_step'), 'start'), (ctx.t('rankings.est_col_value'), 'end')]
    body = []
    for q in QUARTERS:
        v = dz[f'pushes_{q[:4]}_q{q[-1]}']
        label = (ctx.t('rankings.est_row_q', quarter=_q(ctx, q)) if q in released
                 else ctx.t('rankings.est_row_q_assumed', quarter=_q(ctx, q), latest=_q(ctx, latest)))
        body.append((q, [label, (num(fint(v, lang)), v)]))
    year = data.manifest['gdc26']['population_year']
    body += [('total', [ctx.t('rankings.est_row_total'), (num(fint(dz['pushes'], lang)), dz['pushes'])]),
             ('people', [ctx.t('rankings.est_row_people', year=str(year)),
                         (num(fint(dz['working_age_population'], lang)), dz['working_age_population'])])]
    foot = [('per_1k', [ctx.t('rankings.est_row_per'), (num(fdec(dz['per_1k_working_age'], 1, lang)), dz['per_1k_working_age'])])]
    table = C.data_table(ctx.t('rankings.est_caption'), head, body, cls='rank-est', foot=foot)
    tenth = rows(data, 'africa')[-1]
    need = tenth['per_1k_working_age'] * dz['working_age_population'] / 1000
    text = [ctx.t('rankings.est_lede')]
    assumed = [q for q in QUARTERS if q not in released]
    if assumed:
        text.append(ctx.t('rankings.est_assumed', latest=_q(ctx, latest),
                          quarters=Markup(and_list([_q(ctx, q) for q in assumed], lang))))
    need_text = ctx.t('rankings.est_need', tenth=collaboration.cell_name(ctx, tenth['economy']),
                      t=num(whole(tenth['per_1k_working_age'], lang)),
                      x=num(fdec(tenth['per_1k_working_age'] / dz['per_1k_working_age'], 1, lang)),
                      need=num(fdec(need / 1e6, 2, lang)), have=num(fdec(dz['pushes'] / 1e6, 2, lang)))
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/gdc26.csv') + C.action_link('JSON', f'/data/{folder}/gdc26.json')
    inner = Markup(f'{table}<p class="fig-note rank-need">{need_text}</p>{C.source_line(ctx.t("rankings.est_source"), acts)}')
    return C.section('estimate', ctx.t('rankings.est_eyebrow'),
                     ctx.t('rankings.est_title', dz=num(whole(dz['per_1k_working_age'], lang))), inner,
                     lede=Markup(' '.join(str(x) for x in text)), size='s')


# ---------------------------------------------------------------- the estimate against GitHub's figures
def checked(data) -> list:
    """(economy, GitHub's rank, GitHub's figure, the estimate, GitHub ÷ estimate) for GitHub's ten."""
    est = estimates(data)
    out = []
    for r in rows(data, 'africa'):
        e = est.get(r['economy'])
        mine = e['per_1k_working_age'] if e else None
        out.append((r['economy'], r['rank'], r['per_1k_working_age'], mine, r['per_1k_working_age'] / mine if mine else None))
    return out


def check_section(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    found = checked(data)
    close = [c for c in found if c[4] is not None and abs(c[4] - 1) <= OUTLIER]
    far = [c for c in found if c[4] is not None and abs(c[4] - 1) > OUTLIER]
    p = math.ceil(max(abs(c[4] - 1) for c in close) * 100) if close else 0
    text = [ctx.t('rankings.check_lede', p=num(fint(p, lang)), k=num(fint(len(close), lang)))]
    text += [ctx.t('rankings.check_outlier', name=collaboration.cell_name(ctx, c[0]), r=num(fdec(c[4], 1, lang))) for c in far]
    listed = {c[0] for c in found}
    est = estimates(data)
    unlisted = [c for c in CORE_PEERS if c not in listed and c in est]
    if unlisted:
        items = [ctx.t('rankings.unlisted_item', name=collaboration.cell_name(ctx, c), v=num(whole(est[c]['per_1k_working_age'], lang)))
                 for c in unlisted]
        text.append(ctx.t('rankings.check_unlisted', list=Markup(and_list(items, lang))))

    head = [(ctx.t('rankings.category'), 'start'), (ctx.t('rankings.col_rank'), 'end'), (ctx.t('rankings.col_github'), 'end'),
            (ctx.t('rankings.col_estimate'), 'end'), (ctx.t('rankings.col_ratio'), 'end')]
    cell = lambda v, f: ('—', '') if v is None else (num(f(v)), v)
    eco = lambda c: Markup(f'<span class="eco"><span class="eco-sq" aria-hidden="true"></span>{collaboration.cell_name(ctx, c)}</span>')
    body = [(code, [eco(code), (num(fint(rank, lang)), rank), cell(theirs, lambda v: whole(v, lang)),
                    cell(mine, lambda v: whole(v, lang)), cell(ratio, lambda v: fdec(v, 2, lang))])
            for code, rank, theirs, mine, ratio in found]
    body += [(c, [eco(c), ('—', ''), ('—', ''), cell(est[c]['per_1k_working_age'], lambda v: whole(v, lang)), ('—', '')])
             for c in unlisted]
    if 'DZ' in est:
        body.append(('DZ', [eco('DZ'), ('—', ''), ('—', ''), cell(est['DZ']['per_1k_working_age'], lambda v: whole(v, lang)),
                            ('—', '')]))
    table = C.data_table(ctx.t('rankings.check_caption'), head, body, cls='rank-check', highlight='DZ')
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/gdc26.csv') + C.action_link('JSON', f'/data/{folder}/gdc26.json')
    return C.section('check', ctx.t('rankings.check_eyebrow'), ctx.t('rankings.check_title'),
                     Markup(f'{table}{C.source_line(ctx.t("rankings.check_source"), acts)}'),
                     lede=Markup(' '.join(str(x) for x in text)), size='s')


def read_well(ctx) -> Markup:
    cards = join(f'<div class="limit"><h3>{ctx.t(f"rankings.{key}")}</h3><p>{ctx.t(f"rankings.{key}_text")}</p></div>'
                 for key in ('rw_once', 'rw_vpn', 'rw_estimate', 'rw_people'))
    return C.section('read', ctx.t('rankings.read_eyebrow'), ctx.t('rankings.read_title'),
                     Markup(f'<div class="limits">{cards}</div>'), size='s')


def head(ctx) -> Markup:
    return C.page_head(eyebrow_text=ctx.t('rankings.eyebrow'), title=ctx.t('rankings.title'), lede=ctx.t('rankings.intro'))


def render(ctx: Ctx) -> Page:
    data = ctx.site.data
    source = ctx.t('rankings.source', date=date_label(data.manifest['gdc26']['date'], ctx.lang))
    fig = figure(ctx, chart(ctx), 1, source=source, lede=lede(ctx), note=world_note(ctx))
    body = Markup(f'{head(ctx)}{outlook.global_table(ctx)}<section class="rank-body" aria-label="{ctx.ta("rankings.fig_label")}"><div class="container">'
                  f'<h2 class="t-section">{ctx.t("rankings.fig_label")}</h2><p class="lede">{ctx.t("rankings.lede")}</p>'
                  f'<div class="outlook-actions">{C.btn(ctx.t("rankings.methodology"), ctx.url("methodology", hash="gdc26"), "secondary")}</div>'
                  f'{fig}</div></section>{estimate_section(ctx)}{check_section(ctx)}{read_well(ctx)}')
    return Page(title=ctx.s('pages.rankings.title'), description=ctx.s('pages.rankings.description'), body=body)
