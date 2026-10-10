"""Chart figures (Components board, "Charts"): the numbered label, the wide and phone
drawings, a key where the drawing has no direct labels, the source line with downloads, and
the data table that every chart has (AC-IDX-7).

Each figure registers its chart's downloads with the site (IDX-15): CSV and JSON, the same
in both languages, and SVG files in the dark and light palettes in the page's language.
PNG files are drawn from those SVG files in the browser by site.js. Charts on the Index pages
and Home can also be shared and embedded (``embeds.py``, ticket #42).
"""
from __future__ import annotations

from dataclasses import replace

from . import charts, embeds
from .charts import HBarChart, LineChart, UnitMap, loc
from .components import data_table, details, download_menu, fig_label, frame, source_line
from .config import LANGS
from .fmt import fint, num
from .markup import Markup, esc
from .palette import THEMES

KEY_ORDER = ('dz', 'hl', 'median', 'ref', 'peer')


def credited(ctx, chart):
    """The chart with the site's credit line, unless it has its own: downloads and embeds carry it."""
    if chart.credit:
        return chart
    return replace(chart, credit={lang: ctx.site.catalog.lookup(lang, 'chart.credit')[0] for lang in LANGS})


def downloads(ctx, chart) -> dict:
    """Register the chart's files and return them for ``download_menu``."""
    chart = credited(ctx, chart)
    site, lang, folder = ctx.site, ctx.lang, chart.folder
    stem = f'djazair.dev-{chart.id}-{folder}'
    base = f'/charts/{folder}/{chart.id}'
    files = {'csv': (site.add_file(f'{base}.csv', chart.csv()), f'{stem}.csv'),
             'json': (site.add_file(f'{base}.json', chart.json()), f'{stem}.json')}
    if ctx.route.indexed:
        site.charts.setdefault(chart.id, {'route': ctx.route.key, 'title': chart.title, 'csv': files['csv'], 'json': files['json']})
    for theme, pal in THEMES.items():
        url = site.add_file(f'/charts/{folder}/{lang}/{chart.id}-{theme}.svg', charts.download_svg(chart, lang, pal))
        files[f'svg-{theme}'] = (url, f'{stem}-{lang}-{theme}.svg')
        files[f'png-{theme}'] = (url, f'{stem}-{lang}-{theme}.png')
    return files


def actions(ctx, chart, source, anchor: str, share: bool = True) -> Markup:
    """The chart's downloads, then, on the Index pages and Home, Embed and Share (ticket #42),
    with the chart's embed page. ``anchor``: the id of the figure the chart is in. Trends adds
    one Share for its eight views, after them."""
    chart = credited(ctx, chart)
    out = download_menu(ctx, downloads(ctx, chart))
    if embeds.embeddable(ctx, chart):
        embeds.register(ctx, chart, source, anchor)
        out += embeds.panel(ctx, chart) + (embeds.share(ctx, anchor) if share else Markup(''))
    return out


def line_key(ctx, chart: LineChart) -> Markup:
    """The phone drawing has no end labels, so a key names the lines."""
    items = []
    for ln in sorted(chart.lines, key=lambda ln: KEY_ORDER.index(ln.role)):
        if ln.role == 'peer' and chart.peers_label:
            continue
        items.append(f'<li><span class="sw sw-{ln.role}" aria-hidden="true"></span>{esc(loc(ln.name, ctx.lang))}</li>')
    if chart.peers_label and any(ln.role == 'peer' for ln in chart.lines):
        items.append(f'<li><span class="sw sw-peer" aria-hidden="true"></span>{esc(loc(chart.peers_label, ctx.lang))}</li>')
    return Markup(f'<ul class="chart-key narrow" aria-label="{ctx.ta("chart.legend")}">{"".join(items)}</ul>')


def unit_key(ctx, chart: UnitMap) -> Markup:
    """The squares' colours, with their counts; a map that replays the years has no one count."""
    total, added = chart.squares
    lang = ctx.lang
    old, new = ('', '') if chart.history else (f' {num(fint(total - added, lang))}', f' {num(fint(added, lang))}')
    return Markup(
        f'<ul class="chart-key um-key" aria-label="{ctx.ta("chart.legend")}">'
        f'<li><span class="sw sw-old" aria-hidden="true"></span>{esc(loc(chart.start_label, lang))}{old}</li>'
        f'<li><span class="sw sw-new" aria-hidden="true"></span>{esc(loc(chart.added_label, lang))}{new}</li>'
        f'<li class="um-note">{esc(loc(chart.square_label, lang))}</li></ul>')


def hbar_key(ctx, chart: HBarChart) -> Markup:
    """Year earlier and added since; with a highlighted bar, those in grey and the bar's own name in green."""
    lang = ctx.lang
    old, new = ('sw-pold', 'sw-pnew') if chart.highlight else ('sw-old', 'sw-new')
    lit = (f'<li><span class="sw sw-new" aria-hidden="true"></span>{esc(loc(chart.highlight_label, lang))}</li>'
           if chart.highlight else '')
    return Markup(
        f'<ul class="chart-key" aria-label="{ctx.ta("chart.legend")}">'
        f'<li><span class="sw {old}" aria-hidden="true"></span>{esc(loc(chart.before_label, lang))}</li>'
        f'<li><span class="sw {new}" aria-hidden="true"></span>{esc(loc(chart.added_label, lang))}</li>{lit}</ul>')


def table(ctx, chart) -> Markup:
    names = {k: ctx.t(f'chart.{k}') for k in ('quarter', 'series', 'category', 'value', 'accounts', 'squares')}
    head, rows = charts.table(chart, ctx.lang, names)
    dz_first = isinstance(chart, LineChart) and chart.ordered()[0].role == 'dz'
    tbl = data_table(esc(loc(chart.title, ctx.lang)), head, rows, cls='fig-dt dz-col' if dz_first else 'fig-dt')
    return details(ctx.t('chart.table'), Markup(f'{tbl}<p class="fig-note">{ctx.t("chart.table_note")}</p>'),
                   cls='fig-table', icon_name='table', id_=f'{chart.id}-table')


def figure(ctx, chart, n: int, *, source, controls='', lede='', note='', cls: str = '', footer: bool = True) -> Markup:
    """Figure ``n``. ``source``: HTML for the source line, naming the source and the data
    quarter (IDX-13). ``controls`` sit beside the label; ``lede`` goes under it; ``note``
    under the drawing, for what it leaves out. ``footer`` controls the source and action row;
    downloads and embeds remain registered when it is omitted."""
    chart = credited(ctx, chart)
    lang = ctx.lang
    desc = f'{loc(chart.summary, lang)} {ctx.s("chart.desc_table")}'
    label_id = f'{chart.id}-label'
    head = Markup(f'<div class="fig-head">{fig_label(ctx, n, esc(loc(chart.title, lang)), label_id)}{controls}</div>')
    if isinstance(chart, UnitMap):
        body = charts.svg(chart, lang, 'wide', f'{chart.id}-m', desc) + unit_key(ctx, chart)
    else:
        body = (charts.svg(chart, lang, 'wide', f'{chart.id}-w', desc, cls='wide')
                + charts.svg(chart, lang, 'narrow', f'{chart.id}-n', desc, cls='narrow'))
        if isinstance(chart, LineChart):
            body += line_key(ctx, chart)
        elif isinstance(chart, HBarChart) and chart.split:
            body += hbar_key(ctx, chart)
    lede_html = Markup(f'<p class="fig-lede">{lede}</p>') if lede else ''
    note_html = Markup(f'<p class="fig-note">{note}</p>') if note else ''
    anchor = f'fig-{chart.id}'
    chart_actions = actions(ctx, chart, source, anchor)
    footer_html = source_line(source, chart_actions) if footer else Markup('')
    inner = (head + lede_html + Markup(f'<div class="fig-body">{body}</div>') + note_html
             + footer_html + table(ctx, chart))
    return frame(inner, cls=f'fig {cls}'.strip(), labelledby=label_id, id_=anchor)
