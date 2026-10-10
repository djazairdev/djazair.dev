"""Index overview: six detailed indicators, their comparison groups and sources.
Full comparison tables and limitations live on Peers and Methodology respectively.
Every number comes from the derived data."""
from __future__ import annotations

from .. import components as C
from .. import outlook
from ..context import Ctx, Page
from ..fmt import date_label, fdec, fint, fpct, num, quarter_label
from ..icons import icon
from ..markup import Markup, esc, join
from ..scorecard import AFRICA_MIN_ACCOUNTS, CORE_PEERS, NORTH_AFRICA, indicators, name, year_earlier

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
    actions = [C.btn(ctx.t('overview.download_all'), zip_url(data), arrow=False, attrs=' download')]
    return C.page_head(eyebrow_text=ctx.t('overview.eyebrow'), title=ctx.t('overview.title', quarter=_q(ctx, data.quarter)),
                       lede=ctx.t('overview.lede'), meta=meta(ctx), actions=actions)


def reading_guide(ctx) -> Markup:
    """The ranking and comparison explanation belongs with the detailed Index."""
    data = ctx.site.data
    overview = data.overview()
    lang = ctx.lang
    return Markup(f'<div class="index-guide"><p>{ctx.t("overview.reading.guide")}</p>'
                   f'<details class="index-groups"><summary>{ctx.t("overview.reading.groups_title")}{icon("chev", 14)}</summary><dl>'
                   f'<div><dt>{ctx.t("ind.north_africa")}</dt><dd>{join((ctx.t("economy." + k) for k in NORTH_AFRICA), ", ")}.</dd></div>'
                   f'<div><dt>{ctx.t("ind.africa")}</dt><dd>{ctx.t("overview.reading.africa_group", n=overview["accounts"]["africa_ranked"], min=num(fint(AFRICA_MIN_ACCOUNTS, lang)), quarter=_q(ctx, year_earlier(data.quarter)))}</dd></div>'
                   f'<div><dt>{ctx.t("overview.reading.peers")}</dt><dd>{join((ctx.t("economy." + k) for k in CORE_PEERS), ", ")}.</dd></div>'
                   f'</dl><p>{ctx.t("overview.reading.median_definition")}</p></details></div>')


def cards(ctx) -> Markup:
    data = ctx.site.data
    q = data.quarter
    year = data.peers()['DZ']['population_year']
    out = []
    for i, ind in enumerate(indicators(ctx), 1):
        bars = ind.key in ('topics', 'permillion')
        legend = ''
        if not bars:
            median = (f'<li><i class="score-line score-line-median" aria-hidden="true"></i>{ctx.t("overview.chart_median")}</li>'
                      if ind.key != 'accounts' else '')
            legend = (f'<ul class="ind-chart-key" aria-label="{ctx.ta("chart.legend")}">'
                      f'<li><i class="score-line" aria-hidden="true"></i>{ctx.t("economy.DZ")}</li>{median}</ul>')
        viz = Markup(f'<figure class="ind-chart"><figcaption>{ctx.t("overview.chart_peers" if bars else "overview.chart_trend")}</figcaption>'
                     f'{ind.viz}{legend}</figure>')
        out.append(C.indicator_card(n=i, title=ind.title, quarter=_q(ctx, q, 'short'), value=ind.value,
                                    extras=Markup(ind.delta + ind.chip), viz=viz, ranks=ind.ranks, medians=ind.medians,
                                    measures_html=C.measures_disclosure(ctx, ind.does, ind.doesnt),
                                    median_label=ctx.t('overview.medians_label'), lang=ctx.lang, id_=f'ind-{ind.key}', heading_level=3))
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/overview.csv') + C.action_link('JSON', f'/data/{folder}/overview.json')
    src = C.source_line(ctx.t('overview.source', quarter=_q(ctx, q), date=date_label(data.release_date, ctx.lang), year=year), acts)
    intro = (f'<header class="section-head outlook-detail-head">{C.eyebrow(ctx.t("outlook.details.eyebrow"))}'
             f'<h2 class="t-section" id="detailed-indicators-h">{ctx.t("outlook.details.title")}</h2><p class="lede">{ctx.t("outlook.details.lede")}</p></header>')
    return Markup(f'<section class="ov-cards" id="detailed-indicators" aria-labelledby="detailed-indicators-h"><div class="container">'
                  f'{intro}{reading_guide(ctx)}<div class="ind-grid">{join(out)}</div>{src}</div></section>')


def table_head(ctx) -> list:
    return [(ctx.t('overview.col_economy'), 'start')] + [(ctx.t(label), 'end') for _, label, _ in COLUMNS]


def economy_cell(ctx, code: str) -> tuple:
    return Markup(f'<span class="eco"><span class="eco-sq" aria-hidden="true"></span>{name(ctx, code)}</span>'), None


def peers_table(ctx, lede=None) -> Markup:
    """The Peers page's comparison table: Algeria, six core peers and group medians."""
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
    return C.section('peers', ctx.t('overview.peers_eyebrow'), ctx.t('overview.peers_title'), Markup(f'{table}{src}'),
                     lede=lede, size='s')


def next_steps(ctx) -> Markup:
    """Give each detailed page a clear destination instead of copying its content here."""
    destinations = [('peers', ''), ('trends', ''), ('data', 'limitations')]
    links = join(f'<li><a href="{ctx.url(route, hash=fragment)}"><span class="overview-next-title">'
                 f'{ctx.t(f"overview.next.{route}.title")}{icon("arrow", 18)}</span>'
                 f'<span class="overview-next-desc">{ctx.t(f"overview.next.{route}.description")}</span></a></li>'
                 for route, fragment in destinations)
    return Markup(f'<nav class="overview-next container" aria-labelledby="overview-next-h">'
                  f'{C.h2(ctx.t("overview.next.title"), "overview-next-h")}<ul>{links}</ul></nav>')


def render(ctx: Ctx) -> Page:
    body = head(ctx) + outlook.world(ctx) + outlook.outlook(ctx) + outlook.scenario(ctx) + cards(ctx) + next_steps(ctx)
    return Page(title=ctx.s('pages.overview.title'), description=ctx.s('pages.overview.description'), body=Markup(body),
                scripts=(ctx.site.assets.scripts['index-outlook'],))
