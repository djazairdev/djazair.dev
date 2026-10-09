"""Languages (ticket #22, IDX-08): the ten languages the most developers in Algeria pushed in
during the quarter, with the change on a year earlier, drawn as bars split into last year's
developers and those added since. The lede is computed from the data. Then what to keep in
mind (the counts can't be added up) and the first three languages in each core peer."""
from __future__ import annotations

from .. import components as C
from ..charts import HBar, HBarChart
from ..context import Ctx, Page
from ..figures import figure
from ..fmt import and_list, fint, fpct, num, quarter_label
from ..markup import Markup, esc, join
from ..scorecard import CORE_PEERS, year_earlier
from . import overview

TOP = 10


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def rows(data, economy: str = 'DZ') -> list:
    """The economy's languages in the latest quarter, by rank."""
    return sorted((r for r in data.rows('languages') if r['economy'] == economy and r['quarter'] == data.quarter),
                  key=lambda r: r['rank'])


def always_first(data, language: str) -> bool:
    """Was ``language`` first in Algeria in every quarter since 2020?"""
    first = {r['quarter']: r['language'] for r in data.rows('languages_algeria') if r['rank'] == 1}
    return all(first.get(q) == language for q in data.quarters)


def chart(ctx) -> HBarChart:
    data = ctx.site.data
    q, before = data.quarter, year_earlier(data.quarter)
    both = lambda key, **kw: ctx.both(f'languages.{key}', **kw)
    quarter = {lang: quarter_label(q, lang) for lang in ('en', 'ar')}
    bars = [HBar(r['language'], r['language'], r['pushers'], r['pushers_year_earlier'], r['rank']) for r in rows(data)[:TOP]]
    return HBarChart(id='languages-top', quarter=q, title=both('fig_title', quarter=quarter),
                     summary=both('fig_summary', quarter=quarter), unit=ctx.both('chart.developers'),
                     bars=bars, fmt=lambda v, lang: fint(v, lang), change_fmt=lambda v, lang: fpct(v, 1, lang),
                     category_label=both('category'), now_label=quarter,
                     before_label={lang: quarter_label(before, lang) for lang in ('en', 'ar')},
                     added_label=both('added'), change_label=both('change'))


def _name(language: str) -> Markup:
    """A language name in running text, isolated so 'C++' keeps its signs in Arabic."""
    return Markup(f'<bdi lang="en">{esc(language)}</bdi>')


def lede(ctx) -> Markup:
    """Who leads, what entered the top ten and what grew fastest, from the data."""
    data = ctx.site.data
    lang = ctx.lang
    langs = rows(data)
    top = langs[:TOP]
    names = lambda items: Markup(and_list([_name(r['language']) for r in items], lang))
    lead = top[0]
    out = [ctx.t('languages.lede_lead_always', lang=_name(lead['language']), first=_q(ctx, data.quarters[0]))
           if always_first(data, lead['language']) else ctx.t('languages.lede_lead', lang=_name(lead['language']))]
    new = [r for r in top if not r['rank_year_earlier'] or r['rank_year_earlier'] > TOP]
    gone = [r for r in langs[TOP:] if r['rank_year_earlier'] and r['rank_year_earlier'] <= TOP]
    if new:
        out.append(ctx.t('languages.lede_new', new=names(new), out=names(gone)) if gone
                   else ctx.t('languages.lede_new_only', new=names(new)))
    grew = [r for r in top if r['change'] is not None]
    if grew:
        fast = max(grew, key=lambda r: r['change'])
        out.append(ctx.t('languages.lede_fast', lang=_name(fast['language']), pct=num(fpct(fast['change'], 1, lang))))
    return Markup(' '.join(str(x) for x in out))


def head(ctx) -> Markup:
    data = ctx.site.data
    actions = [C.btn(ctx.t('languages.download'), f'/data/{data.folder.name}/languages.csv', arrow=False, attrs=' download'),
               C.btn(ctx.t('languages.methodology'), ctx.url('data', hash='languages'), 'secondary')]
    return C.page_head(eyebrow_text=ctx.t('languages.eyebrow'), title=ctx.t('languages.title', quarter=_q(ctx, data.quarter)),
                       lede=ctx.t('languages.lede'), meta=overview.meta(ctx), actions=actions)


def read_well(ctx) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    langs = rows(data)
    total = sum(r['pushers'] for r in langs[:TOP])
    items = [('rw_add', {'sum': num(fint(total, lang))}), ('rw_markup', {}),
             ('rw_threshold', {'quarter': _q(ctx, data.quarter), 'n': num(fint(len(langs), lang))})]
    cards = join(f'<div class="limit"><h3>{ctx.t(f"languages.{key}")}</h3><p>{ctx.t(f"languages.{key}_text", **values)}</p></div>'
                 for key, values in items)
    return C.section('read', ctx.t('languages.read_eyebrow'), ctx.t('languages.read_title'),
                     Markup(f'<div class="limits">{cards}</div>'), size='s')


def peers_table(ctx) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    head = [(ctx.t('overview.col_economy'), 'start')] + [(ctx.t(f'languages.col_{k}'), 'start') for k in ('first', 'second', 'third')]
    head.append((ctx.t('languages.col_listed'), 'end'))
    body = []
    for code in ('DZ',) + CORE_PEERS:
        langs = rows(data, code)
        names = [Markup(f'<span class="lang-n" lang="en" dir="ltr">{esc(r["language"])}</span>') for r in langs[:3]]
        names += ['—'] * (3 - len(names))
        body.append((code, [overview.economy_cell(ctx, code)] + names + [(num(fint(len(langs), lang)), len(langs))]))
    table = C.data_table(ctx.t('languages.peers_caption', quarter=_q(ctx, data.quarter)), head, body, cls='lang-peers', highlight='DZ')
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/languages.csv') + C.action_link('JSON', f'/data/{folder}/languages.json')
    src = C.source_line(ctx.t('languages.peers_source', quarter=_q(ctx, data.quarter)), acts)
    return C.section('peers', ctx.t('languages.peers_eyebrow'), ctx.t('languages.peers_title'), Markup(f'{table}{src}'),
                     lede=ctx.t('languages.peers_lede'), size='s')


def render(ctx: Ctx) -> Page:
    data = ctx.site.data
    fig = figure(ctx, chart(ctx), 1, source=ctx.t('languages.source', quarter=_q(ctx, data.quarter)), lede=lede(ctx))
    body = Markup(f'{head(ctx)}<section class="lang-body" aria-label="{ctx.ta("languages.fig_label")}"><div class="container">'
                  f'{fig}</div></section>{peers_table(ctx)}{read_well(ctx)}')
    return Page(title=ctx.s('pages.languages.title'), description=ctx.s('pages.languages.description'), body=body)
