"""Data and downloads (ticket #24; PRD IDX-15, IDX-16, §13): every derived table as CSV and
JSON with its size, the data behind every chart, stable addresses for code, the full
changelog and corrections log, and the licence and attribution. Source definitions share the document layout.

Everything listed is a file the build writes: the tables come from the quarter's manifest,
and the charts from what the other pages registered (``Site.charts``), which is why this
page is rendered last.
"""
from __future__ import annotations

from .. import components as C
from .. import logs, outlook
from ..config import CONTENT_DIR
from ..context import Ctx, Page
from ..data import manifests
from ..fmt import date_label, fint, fsize, num, quarter_label
from ..markup import Markup, esc, join
from ..charts import loc
from . import overview
from .methodology import REPO, toc, renderer
from ..markdown import sections
from ..icons import icon
from .. import structured

SITE = 'https://djazair.dev'
SECTIONS = ('tables', 'country-data', 'charts', 'reading', 'addresses', 'changelog', 'corrections', 'licence')
# The pipeline's order: Algeria first, then the groups, the series, and the full table last.
TABLES = ('overview', 'peers', 'groups', 'ranks', 'trends', 'languages', 'languages_algeria', 'topics', 'collaboration',
          'gdc26', 'indicators', 'revisions')


class Sec:
    def __init__(self, id_: str, title: Markup):
        self.id, self.title = id_, title


def _q(ctx, q: str) -> str:
    return quarter_label(q, ctx.lang)


def head(ctx) -> Markup:
    data = ctx.site.data
    tables = {f['table'] for f in data.files.values() if 'table' in f}
    meta = [(ctx.t('overview.meta_data'), _q(ctx, data.quarter)),
            (ctx.t('overview.meta_released'), date_label(data.release_date, ctx.lang, short=ctx.en)),
            (ctx.t('downloads.meta_tables'), str(len(tables))),
            (ctx.t('overview.meta_licence'), 'CC0')]
    actions = [C.btn(ctx.t('downloads.download_all'), overview.zip_url(data), arrow=False, attrs=' download'),
               C.btn(ctx.t('downloads.dictionary'), f'{REPO}/blob/main/data/README.md', 'secondary')]
    return Markup(str(C.page_head(eyebrow_text=ctx.t('downloads.eyebrow'), title=ctx.t('downloads.title'),
                                 lede=ctx.t('downloads.lede'), meta=meta, actions=actions))
                  .replace('class="page-head"', 'class="page-head data-page-head"'))


def start(ctx) -> Markup:
    """Three task-based entry points, before the detailed file catalogue."""
    cards = join(f'<li><a href="#{target}"><h2>{ctx.t(f"downloads.start.{key}.title")}{icon("arrow", 20)}</h2>'
                 f'<p>{ctx.t(f"downloads.start.{key}.text")}</p></a></li>'
                 for key, target in (('download', 'tables'), ('understand', 'reading'), ('reuse', 'addresses')))
    return Markup(f'<nav class="container data-start" aria-label="{ctx.ta("downloads.start_label")}"><ul>{cards}</ul></nav>')


def country_data(ctx) -> Markup:
    """The generated country files have their own provenance, outside the quarterly bundle."""
    rows = outlook.standings(ctx.site.data)
    actual = outlook.csv_url(ctx, rows)
    forecast = '/data/octoverse-2025/country-outlook.json'
    # The overview registers the shared source file before this page is rendered.
    cards = []
    for key, url, fmt in (('standing', actual, 'CSV'), ('forecast', forecast, 'JSON')):
        size = len(ctx.site.files[url])
        cards.append(f'<article class="data-country-card"><p class="eyebrow">{ctx.t(f"downloads.country.{key}.kind",quarter=_q(ctx,ctx.site.data.quarter))}</p>'
                     f'<h3>{ctx.t(f"downloads.country.{key}.title")}</h3><p>{ctx.t(f"downloads.country.{key}.text", quarter=_q(ctx,ctx.site.data.quarter))}</p>'
                     f'<div>{_file(url,fmt,size,ctx.lang)}</div></article>')
    return Markup(f'<p>{ctx.t("downloads.country.lede")}</p><div class="data-country-grid">{join(cards)}</div>')


def reading(ctx) -> Markup:
    """Keep source definitions and stable formula anchors together without repeating logs."""
    secs = sections((CONTENT_DIR / 'methodology' / f'{ctx.lang}.md').read_text('utf-8'))
    md = renderer(ctx)
    panels = []
    for s in secs:
        if s.id not in ('sources', 'indicators', 'peer-groups', 'limitations', 'updates'):
            continue
        body = str(md.render(s.body)).replace('<h3', '<h4').replace('</h3>', '</h4>')
        panels.append(f'<details class="data-method" id="{s.id}"><summary><h3>{md.inline(s.title)}</h3>{icon("chev",18)}</summary>'
                      f'<div class="data-method-body">{body}</div></details>')
    return Markup(f'<p>{ctx.t("downloads.reading_lede")}</p><div class="data-methods">{join(panels)}</div>')


def _file(url: str, label: str, size: int, lang: str) -> str:
    return (f'<a class="act" href="{esc(url)}" download><span>{label}</span>'
            f'<span class="dl-size" dir="ltr">{esc(fsize(size, lang))}</span></a>')


def tables(ctx) -> Markup:
    data = ctx.site.data
    lang = ctx.lang
    folder = data.folder.name
    by_table = {}
    for name, f in data.files.items():
        if 'table' in f:
            by_table.setdefault(f['table'], {})[name.rsplit('.', 1)[1]] = (name, f)
    rows = []
    for table in sorted(by_table, key=lambda t: (TABLES.index(t) if t in TABLES else len(TABLES), t)):
        files = by_table[table]
        f = files.get('csv', files.get('json'))[1]
        links = ''.join(_file(f'/data/{folder}/{name}', kind.upper(), entry['bytes'], lang) for kind, (name, entry) in sorted(files.items()))
        rows.append(f'<li class="tb-row" id="t-{esc(table)}"><div class="tb-a"><h3>{ctx.t(f"downloads.t.{table}.title")}</h3>'
                    f'<code dir="ltr">{esc(table)}</code></div><p class="tb-d">{ctx.t(f"downloads.t.{table}.text")}</p>'
                    f'<span class="tb-n">{ctx.t("downloads.rows", n=num(fint(f["rows"], lang)))}</span><div class="tb-f">{links}</div></li>')
    extra = [('manifest.json', ctx.t('downloads.manifest')), ('README.md', ctx.t('downloads.readme'))]
    extras = ''.join(f'<a class="act" href="/data/{folder}/{name}">{label}</a>' for name, label in extra)
    earlier = [m for m in manifests() if m['quarter'] != data.quarter]
    if earlier:
        past = ''.join(f'<li><a href="/data/{m["quarter"].lower()}/manifest.json">{_q(ctx, m["quarter"])}</a></li>' for m in earlier)
        earlier_html = f'<p class="tb-more">{ctx.t("downloads.earlier")}</p><ul class="tb-past">{past}</ul>'
    else:
        earlier_html = f'<p class="tb-more">{ctx.t("downloads.earlier_none", quarter=_q(ctx, data.quarter))}</p>'
    lede = ctx.t('downloads.tables_lede', n=len(by_table), quarter=_q(ctx, data.quarter), release=data.release[:12])
    return Markup(f'<p>{lede}</p><ol class="tb-list">{"".join(rows)}</ol>'
                  f'<div class="tb-extra"><p>{ctx.t("downloads.checksums")}</p><div class="tb-f">{extras}</div></div>{earlier_html}')


def page_name(ctx, key: str) -> Markup:
    """A page's name in the chart list: a report's own title, or the page title."""
    if key.startswith('report-'):  # Archived report tooling may render explicit test fixtures.
        from ..reports import all_reports
        report = next(r for r in all_reports() if r.key == key)
        return esc(report.source(ctx.lang)[0]['title'])
    return ctx.t(f'pages.{key}.title')


def charts(ctx) -> Markup:
    lang = ctx.lang
    groups = {}
    for chart_id, c in ctx.site.charts.items():
        groups.setdefault(c['route'], []).append((chart_id, c))
    out = []
    for key in (r.key for r in ctx.site.routes.values() if r.key in groups):
        items = ''.join(
            f'<li><span class="ch-t">{esc(loc(c["title"], lang))}</span><code dir="ltr">{esc(chart_id)}</code>'
            f'<span class="tb-f"><a class="act" href="{esc(c["csv"][0])}" download="{esc(c["csv"][1])}">CSV</a>'
            f'<a class="act" href="{esc(c["json"][0])}" download="{esc(c["json"][1])}">JSON</a></span></li>'
            for chart_id, c in groups[key])
        name = ctx.t('downloads.page_home') if key == 'home' else page_name(ctx, key)
        out.append(f'<div class="ch-group"><h3><a class="ch-link" href="{ctx.url(key)}">{name}</a></h3><ul class="ch-list">{items}</ul></div>')
    return Markup(f'<p>{ctx.t("downloads.charts_lede")}</p><div class="ch">{"".join(out)}</div>')


def addresses(ctx) -> Markup:
    data = ctx.site.data
    folder = data.folder.name
    lines = [f'# {ctx.s("downloads.code_latest")}', f'latest: {SITE}/data/latest.json',
             f'# {ctx.s("downloads.code_quarter").replace("{quarter}", data.quarter)}',
             f'table: {SITE}/data/{folder}/<table>.csv', f'json: {SITE}/data/{folder}/<table>.json',
             f'manifest: {SITE}/data/{folder}/manifest.json', f'zip: {SITE}/data/{folder}/{data.zip_name}',
             f'# {ctx.s("downloads.code_charts")}', f'chart: {SITE}/charts/{folder}/<chart>.csv']
    return Markup(f'<p>{ctx.t("downloads.addresses_lede")}</p>{C.code_block(ctx, "djazair.dev/data", lines)}')


def changelog(ctx) -> Markup:
    return Markup(f'<p>{ctx.t("downloads.changelog_lede")}</p>'
                  f'<div class="log-card">{logs.entry_list(ctx, logs.changelog(ctx), "")}</div>')


def corrections(ctx) -> Markup:
    report = C.btn(ctx.t('methodology.report'), logs.report_url())
    return Markup(f'<p>{ctx.t("downloads.corrections_lede")}</p>'
                  f'<div class="log-card">{logs.entry_list(ctx, logs.corrections(ctx), ctx.t("logs.none"))}</div>'
                  f'<div class="doc-actions">{report}</div>')


def licence(ctx) -> Markup:
    data = ctx.site.data
    attribution = ctx.t('downloads.attribution_text', quarter=_q(ctx,data.quarter),url=ctx.abs_url('data'))
    return Markup(f'<p>{ctx.t("downloads.licence_lede")}</p>'
                  f'<figure class="cite"><figcaption><span class="cite-t">{ctx.t("downloads.attribution")}</span>'
                  f'<button type="button" class="act" data-copy data-copied="{ctx.ta("code.copied")}" hidden>{ctx.t("code.copy")}</button>'
                  f'</figcaption><p class="cite-text">{attribution}</p>'
                  f'<p class="cite-l">{ctx.t("downloads.attribution_note", year=data.peers()["DZ"]["population_year"])}</p></figure>')


def render(ctx: Ctx) -> Page:
    parts = {'tables': tables, 'country-data': country_data, 'charts': charts, 'reading': reading,
             'addresses': addresses, 'changelog': changelog,
             'corrections': corrections, 'licence': licence}
    secs = [Sec(key, ctx.t(f'downloads.sec_{key}')) for key in SECTIONS]
    body = join(f'<section class="doc-sec" id="{s.id}" aria-labelledby="{s.id}-h"><h2 id="{s.id}-h">'
                f'<span class="sec-n" aria-hidden="true">{i:02d}</span>{s.title}</h2>{parts[s.id](ctx)}</section>'
                for i, s in enumerate(secs, 1))
    page = Markup(f'{head(ctx)}{start(ctx)}<div class="container doc data-doc">{toc(ctx, secs)}<div class="doc-main">{body}</div></div>')
    return Page(title=ctx.s('pages.data.title'), description=ctx.s('pages.data.description'), body=page,
                scripts=(ctx.site.assets.scripts['data'],),
                head=Markup(str(structured.catalog(ctx)) + f'<link rel="alternate" type="text/markdown" href="/{ctx.lang}/data/index.md">'))
