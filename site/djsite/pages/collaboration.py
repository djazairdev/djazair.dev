"""Collaboration (ticket #37, IDX-10): the economies Algerian developers collaborate with most,
from GitHub's economy_collaborators. Its weight is the git pushes sent and pull requests opened
by developers in one economy to repositories owned in another, so the page reads it both
ways: where those from developers in Algeria went, and where those to repositories owned in
Algeria came from, against a year earlier and since 2020. Then every listed economy both
ways, and what to keep in mind.

GitHub also lists the European Union as one economy, and its weight is the sum of the
members it lists (a pipeline test checks this), so rankings and totals leave it out and a
note says so. Every sentence with a figure is computed from the data."""
from __future__ import annotations

from .. import components as C
from ..charts import HBar, HBarChart, Line, LineChart, tick_int
from ..context import Ctx, Page
from ..figures import figure
from ..fmt import and_list, fint, fpct, num, quarter_label
from ..markup import Markup, esc, join
from ..scorecard import year_earlier
from . import overview

SENT, RECEIVED = 'sent', 'received'
EU = 'EU'
EU_MEMBERS = ('AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU',
              'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE')       # as in pipeline/config.py


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def partners(data, direction: str, quarter: str = '') -> dict:
    """{partner: weight} in ``direction`` in ``quarter`` (default: the latest), the EU included."""
    q = quarter or data.quarter
    return {r['partner']: r['weight'] for r in data.rows('collaboration') if r['quarter'] == q and r['direction'] == direction}


def ranked(data, direction: str, quarter: str = '') -> list:
    """(partner, weight, rank) for the economies listed, without the EU, largest first."""
    q = quarter or data.quarter
    rows = [r for r in data.rows('collaboration') if r['quarter'] == q and r['direction'] == direction and r['partner'] != EU]
    return [(r['partner'], r['weight'], r['rank']) for r in sorted(rows, key=lambda r: (r['rank'], r['partner']))]


def total(data, direction: str, quarter: str = '') -> int:
    """The sum over the economies listed, without the EU."""
    return sum(w for _, w, _ in ranked(data, direction, quarter))


# ---------------------------------------------------------------- names
def _key(ctx, code: str):
    """The catalogue key of an economy's name: African economies, then the rest of the world."""
    for group in ('economy', 'world'):
        if f'{group}.{code}' in ctx.site.catalog.flat['en']:
            return f'{group}.{code}'
    return None


def label(ctx, code: str) -> dict:
    """The economy's name in both languages, for charts; its ISO code if the catalogue has none."""
    key = _key(ctx, code)
    return ctx.both(key) if key else {lang: code for lang in ('en', 'ar')}


def cell_name(ctx, code: str) -> Markup:
    key = _key(ctx, code)
    return ctx.t(key) if key else Markup(esc(code))


def name(ctx, code: str) -> Markup:
    """The name in running text: 'the United States' in English."""
    if f'world_the.{code}' in ctx.site.catalog.flat['en']:
        return ctx.t(f'world_the.{code}')
    return cell_name(ctx, code)


# ---------------------------------------------------------------- figures 1 and 2: one quarter, each way
def chart(ctx, direction: str) -> HBarChart:
    data = ctx.site.data
    q, before = data.quarter, year_earlier(data.quarter)
    then = partners(data, direction, before)
    quarter = {lang: quarter_label(q, lang) for lang in ('en', 'ar')}
    fig = 'fig' if direction == SENT else 'fig2'
    bars = [HBar(p, label(ctx, p), w, then.get(p), rank) for p, w, rank in ranked(data, direction)]
    return HBarChart(id=f'collaboration-{direction}', quarter=q, title=ctx.both(f'collaboration.{fig}_title', quarter=quarter),
                     summary=ctx.both(f'collaboration.{fig}_summary', quarter=quarter), unit=ctx.both('collaboration.unit'),
                     bars=bars, fmt=lambda v, lang: fint(v, lang), change_fmt=lambda v, lang: fpct(v, 0, lang),
                     category_label=ctx.both('collaboration.category'), now_label=quarter,
                     before_label={lang: quarter_label(before, lang) for lang in ('en', 'ar')},
                     change_label=ctx.both('collaboration.change'), split=False,
                     new_label=ctx.both('collaboration.new') if before in data.quarters else '')


def lede_sent(ctx) -> Markup:
    """The largest destination against a year earlier, then the next two."""
    data, lang = ctx.site.data, ctx.lang
    top = ranked(data, SENT)
    first, a, _ = top[0]
    before = partners(data, SENT, year_earlier(data.quarter)).get(first)
    kind = 'new' if before is None else 'up' if a > before else 'down' if a < before else 'same'
    figures = dict(quarter=_q(ctx, data.quarter), first=name(ctx, first), a=num(fint(a, lang)))
    if before is not None:
        figures['before'] = num(fint(before, lang))
    out = [ctx.t(f'collaboration.lede_{kind}', **figures)]
    if len(top) >= 3:
        (second, b, _), (third, c, _) = top[1:3]
        out.append(ctx.t('collaboration.lede_next', second=name(ctx, second), b=num(fint(b, lang)),
                         third=name(ctx, third), c=num(fint(c, lang))))
    return Markup(' '.join(str(x) for x in out))


def lede_received(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    first, a, _ = ranked(data, RECEIVED)[0]
    return ctx.t('collaboration.lede2', total=num(fint(total(data, RECEIVED), lang)),
                 before=num(fint(total(data, RECEIVED, year_earlier(data.quarter)), lang)), first=name(ctx, first),
                 a=num(fint(a, lang)))


def eu_note(ctx, direction: str) -> Markup:
    """Why the EU isn't among the bars, when GitHub lists it."""
    data, lang = ctx.site.data, ctx.lang
    listed = partners(data, direction)
    if EU not in listed:
        return Markup('')
    members = [p for p, _, _ in ranked(data, direction) if p in EU_MEMBERS]
    eu = num(fint(listed[EU], lang))
    if members and listed[EU] == sum(listed[p] for p in members):
        return ctx.t('collaboration.eu_note', eu=eu, members=Markup(and_list([name(ctx, p) for p in members], lang)))
    return ctx.t('collaboration.eu_other', eu=eu)


def source(ctx) -> Markup:
    return ctx.t('collaboration.source', quarter=_q(ctx, ctx.site.data.quarter))


# ---------------------------------------------------------------- figure 3: since 2020
def trend_chart(ctx) -> LineChart:
    data = ctx.site.data
    qs = data.quarters
    sent = [total(data, SENT, q) for q in qs]
    received = [total(data, RECEIVED, q) for q in qs]
    first, last = qs[0], qs[-1]
    ql = lambda quarter: (lambda lang: quarter_label(quarter, lang))
    lines = [Line(RECEIVED, ctx.both('collaboration.line_received'), received, 'hl'),
             Line(SENT, ctx.both('collaboration.line_sent'), sent, 'dz')]
    return LineChart(id='collaboration-trend', quarter=last, x=qs, lines=lines, fmt=lambda v, lang: fint(v, lang),
                     tick_fmt=tick_int, title=ctx.both('collaboration.fig3_title', **{'from': first[:4], 'to': last[:4]}),
                     summary=ctx.both('collaboration.fig3_summary', **{'from': ql(first)}, last=ql(last),
                                      sent=lambda lang: fint(sent[-1], lang), received=lambda lang: fint(received[-1], lang)),
                     unit=ctx.both('collaboration.unit'))


def lede_trend(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    first, last = data.quarters[0], data.quarters[-1]
    n = lambda direction, q: num(fint(total(data, direction, q), lang))
    return ctx.t('collaboration.lede3', first=_q(ctx, first), last=_q(ctx, last), s0=n(SENT, first), r0=n(RECEIVED, first),
                 s1=n(SENT, last), r1=n(RECEIVED, last))


# ---------------------------------------------------------------- both ways
def both_table(ctx) -> Markup:
    data, lang = ctx.site.data, ctx.lang
    sent, received = partners(data, SENT), partners(data, RECEIVED)
    codes = sorted((set(sent) | set(received)) - {EU}, key=lambda c: (-sent.get(c, 0), -received.get(c, 0), c))
    cell = lambda v: ('—', '') if v is None else (num(fint(v, lang)), v)
    head = [(ctx.t('collaboration.category'), 'start'), (ctx.t('collaboration.col_sent'), 'end'),
            (ctx.t('collaboration.col_received'), 'end')]
    body = [(c, [Markup(f'<span class="eco"><span class="eco-sq" aria-hidden="true"></span>{cell_name(ctx, c)}</span>'),
                 cell(sent.get(c)), cell(received.get(c))]) for c in codes]
    foot = [('total', [ctx.t('collaboration.total'), cell(total(data, SENT)), cell(total(data, RECEIVED))])]
    q = _q(ctx, data.quarter)
    table = C.data_table(ctx.t('collaboration.both_caption', quarter=q), head, body, cls='collab-both', sortable=True,
                         sorted_by=(1, 'descending'), foot=foot)
    folder = data.folder.name
    acts = C.action_link('CSV', f'/data/{folder}/collaboration.csv') + C.action_link('JSON', f'/data/{folder}/collaboration.json')
    src = C.source_line(ctx.t('collaboration.both_source', quarter=q), acts)
    return C.section('both', ctx.t('collaboration.both_eyebrow'), ctx.t('collaboration.both_title'), Markup(f'{table}{src}'),
                     lede=ctx.t('collaboration.both_lede', quarter=q), size='s')


def read_well(ctx) -> Markup:
    cards = join(f'<div class="limit"><h3>{ctx.t(f"collaboration.{key}")}</h3><p>{ctx.t(f"collaboration.{key}_text")}</p></div>'
                 for key in ('rw_owner', 'rw_threshold', 'rw_eu', 'rw_place'))
    return C.section('read', ctx.t('collaboration.read_eyebrow'), ctx.t('collaboration.read_title'),
                     Markup(f'<div class="limits">{cards}</div>'), size='s')


def head(ctx) -> Markup:
    data = ctx.site.data
    actions = [C.btn(ctx.t('collaboration.download'), f'/data/{data.folder.name}/collaboration.csv', arrow=False,
                     attrs=' download'),
               C.btn(ctx.t('collaboration.methodology'), ctx.url('data', hash='collaboration'), 'secondary')]
    return C.page_head(eyebrow_text=ctx.t('collaboration.eyebrow'),
                       title=ctx.t('collaboration.title', quarter=_q(ctx, data.quarter)), lede=ctx.t('collaboration.lede'),
                       meta=overview.meta(ctx), actions=actions)


def render(ctx: Ctx) -> Page:
    data = ctx.site.data
    qs = data.quarters
    figs = [figure(ctx, chart(ctx, SENT), 1, source=source(ctx), lede=lede_sent(ctx), note=eu_note(ctx, SENT))]
    if ranked(data, RECEIVED):
        figs.append(figure(ctx, chart(ctx, RECEIVED), 2, source=source(ctx), lede=lede_received(ctx),
                           note=eu_note(ctx, RECEIVED)))
    else:
        figs.append(Markup(f'<p class="fig-lede">{ctx.t("collaboration.none2", quarter=_q(ctx, data.quarter))}</p>'))
    figs.append(figure(ctx, trend_chart(ctx), 3 if ranked(data, RECEIVED) else 2, lede=lede_trend(ctx),
                       source=ctx.t('collaboration.fig3_source', **{'from': _q(ctx, qs[0]), 'to': _q(ctx, qs[-1])})))
    body = Markup(f'{head(ctx)}<section class="collab-body" aria-label="{ctx.ta("collaboration.fig_label")}">'
                  f'<div class="container">{join(figs)}</div></section>{both_table(ctx)}{read_well(ctx)}')
    return Page(title=ctx.s('pages.collaboration.title'), description=ctx.s('pages.collaboration.description'), body=body)
