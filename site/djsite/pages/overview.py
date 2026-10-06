"""Index overview, "Where Algeria stands" (ticket #19; Overview boards in docs/design): the six
headline indicators with their change, medians, ranks and what each measures (IDX-05, IDX-12,
IDX-13), Algeria and six peers with the group medians, and what the numbers can't tell you.
Every number comes from the derived data."""
from __future__ import annotations

from .. import components as C
from ..context import Ctx, Page
from ..fmt import date_label, fdec, fint, fpct, num, quarter_label
from ..markup import Markup, esc, join
from ..scorecard import CORE_PEERS, indicators, name

# Peers table: (peers field = overview indicator, header string, formatter)
COLUMNS = [
    ('accounts', 'overview.col_accounts', lambda v, lang: fint(v, lang)),
    ('yoy', 'overview.col_growth', lambda v, lang: fpct(v, 1, lang)),
    ('pushes_per_account', 'overview.col_pushes', lambda v, lang: fdec(v, 2, lang)),
    ('repos_per_account', 'overview.col_repos', lambda v, lang: fdec(v, 2, lang)),
    ('orgs_per_account', 'overview.col_orgs', lambda v, lang: fdec(v, 4, lang)),
    ('topics', 'overview.col_topics', lambda v, lang: fint(v, lang) if float(v).is_integer() else fdec(v, 1, lang)),
    ('accounts_per_million', 'overview.col_permillion', lambda v, lang: fint(v, lang)),
]
MEDIANS = [('north_africa', 'overview.med_na'), ('core_peers', 'overview.med_cp'), ('africa', 'overview.med_af')]


def _q(ctx, q: str, style: str = 'text') -> str:
    return quarter_label(q, ctx.lang, style)


def zip_url(data) -> str:
    return f'/data/{data.folder.name}/{data.zip_name}'


def meta(ctx) -> list:
    """Data quarter, release date, schedule and licence: the meta row of the Index pages."""
    data = ctx.site.data
    return [(ctx.t('overview.meta_data'), _q(ctx, data.quarter)),
            (ctx.t('overview.meta_released'), date_label(data.release_date, ctx.lang, short=ctx.en)),
            (ctx.t('overview.meta_updated'), ctx.t('overview.meta_quarterly')),
            (ctx.t('overview.meta_licence'), 'CC0')]


def head(ctx) -> Markup:
    data = ctx.site.data
    actions = [C.btn(ctx.t('overview.download_all'), zip_url(data), arrow=False, attrs=' download'),
               C.btn(ctx.t('overview.methodology'), ctx.url('methodology'), 'secondary')]
    return C.page_head(eyebrow_text=ctx.t('overview.eyebrow'), title=ctx.t('overview.title', quarter=_q(ctx, data.quarter)),
                       lede=ctx.t('overview.lede', n=data.overview()['yoy']['africa_ranked']), meta=meta(ctx), actions=actions)


def cards(ctx) -> Markup:
    data = ctx.site.data
    q = data.quarter
    year = data.peers()['DZ']['population_year']
    out = []
    for i, ind in enumerate(indicators(ctx), 1):
        if ind.key == 'permillion':
            source = ctx.t('overview.ind_source_pop', quarter=_q(ctx, q), year=year)
        else:
            source = ctx.t('overview.ind_source', quarter=_q(ctx, q))
        body = Markup(f'{C.measures(ctx, ind.does, ind.doesnt)}<p class="ind-src">{source}</p>')
        out.append(C.indicator_card(n=i, title=ind.title, quarter=_q(ctx, q, 'short'), value=ind.value,
                                    extras=Markup(ind.delta + ind.chip), viz=ind.viz, ranks=ind.ranks, medians=ind.medians,
                                    measures_html=C.details(ctx.t('measures.summary'), body), lang=ctx.lang, id_=f'ind-{ind.key}'))
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/overview.csv') + C.action_link('JSON', f'/data/{folder}/overview.json')
    src = C.source_line(ctx.t('overview.source', quarter=_q(ctx, q), date=date_label(data.release_date, ctx.lang), year=year), acts)
    return Markup(f'<section class="ov-cards" aria-label="{ctx.ta("overview.cards_label")}"><div class="container">'
                  f'<div class="ind-grid">{join(out)}</div>{src}</div></section>')


def table_head(ctx) -> list:
    return [(ctx.t('overview.col_economy'), 'start')] + [(ctx.t(label), 'end') for _, label, _ in COLUMNS]


def economy_cell(ctx, code: str) -> tuple:
    return Markup(f'<span class="eco"><span class="eco-sq" aria-hidden="true"></span>{name(ctx, code)}</span>'), None


def peers_table(ctx, link: bool = True, lede=None) -> Markup:
    """Algeria and the six core peers with the group medians. The Peers page shows it with a
    lede and without the link to itself."""
    data = ctx.site.data
    lang = ctx.lang
    peers, ov = data.peers(), data.overview()

    def cells(values: dict) -> list:
        return [('—', '') if values.get(key) is None else (num(fmt(values[key], lang)), values[key]) for key, _, fmt in COLUMNS]

    rows = [(code, [economy_cell(ctx, code)] + cells(peers[code])) for code in ('DZ',) + CORE_PEERS]
    foot = []
    for group, label in MEDIANS:
        values = {key: ov[key][f'{group}_median'] for key, _, _ in COLUMNS}
        foot.append((f'median_{group}', [ctx.t(label, n=ov['yoy'][f'{group}_ranked'])] + cells(values)))
    table = C.data_table(ctx.t('overview.peers_caption', quarter=_q(ctx, data.quarter)), table_head(ctx), rows, sortable=True,
                         cls='peers-wrap', highlight='DZ', foot=foot, announce=C.sort_text(ctx))
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/peers.csv') + C.action_link('JSON', f'/data/{folder}/peers.json')
    src = C.source_line(ctx.t('overview.peers_source', quarter=_q(ctx, data.quarter), year=peers['DZ']['population_year']), acts)
    more = C.btn(ctx.t('overview.peers_open'), ctx.url('peers'), 'secondary', size='s') if link else ''
    return C.section('peers', ctx.t('overview.peers_eyebrow'), ctx.t('overview.peers_title'), Markup(f'{table}{src}'),
                     lede=lede, size='s', head_extra=more)


def limits(ctx) -> Markup:
    data = ctx.site.data
    items = [('lim_accounts', {}), ('lim_location', {}), ('lim_pushes', {}),
             ('lim_lag', {'quarter': _q(ctx, data.quarter), 'date': date_label(data.release_date, ctx.lang)})]
    cards_html = join(f'<div class="limit"><h3>{ctx.t(f"overview.{key}")}</h3><p>{ctx.t(f"overview.{key}_sub", **values)}</p></div>'
                      for key, values in items)
    more = C.btn(ctx.t('overview.limits_more'), ctx.url('methodology', hash='limitations'), 'secondary', size='s')
    return C.section('limits', ctx.t('overview.limits_eyebrow'), ctx.t('overview.limits_title'),
                     Markup(f'<div class="limits">{cards_html}</div><div class="limits-more">{more}</div>'), size='s')


def render(ctx: Ctx) -> Page:
    body = head(ctx) + cards(ctx) + peers_table(ctx) + limits(ctx)
    return Page(title=ctx.s('pages.overview.title'), description=ctx.s('pages.overview.description'), body=Markup(body))
