"""Country account standings, a sourced external outlook and an illustrative Algeria scenario.
Measured quarterly data, published forecasts and user assumptions stay separate.
"""
from __future__ import annotations

import csv
import io
import json
import math

from . import components as C
from .config import CONTENT_DIR
from .fmt import fdec, fint, fpct, num, quarter_label
from .markup import Markup, esc, join

TARGET = '2030-Q1'
AFRICAN_FORECASTS = ('EG', 'NG', 'ZA', 'KE', 'MA')
SOURCE = 'https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/'


def standings(data) -> list:
    """Competition ranks: tied counts share a place; missing counts and EU are excluded."""
    rows = sorted((dict(r) for r in data.rows('indicators')
                   if r['quarter'] == data.quarter and r['economy'] != 'EU' and r['accounts'] is not None),
                  key=lambda r: (-r['accounts'], r['economy']))
    rank, previous = 0, None
    for i, r in enumerate(rows, 1):
        if r['accounts'] != previous:
            rank = i
        r['rank'] = rank
        previous = r['accounts']
    return rows


def horizon(start: str, end: str = TARGET) -> float:
    def quarter_index(q):
        year, quarter = q.split('-Q')
        if int(quarter) not in range(1, 5):
            raise ValueError('invalid quarter')
        return int(year) * 4 + int(quarter) - 1
    return (quarter_index(end) - quarter_index(start)) / 4


def future(accounts: int, rate: float, years: float) -> float:
    if accounts <= 0 or rate < 0 or years <= 0:
        raise ValueError('a growth scenario needs positive accounts, a future target and a nonnegative rate')
    return accounts * (1 + rate) ** years


def required_rate(accounts: int, years: float, target: int = 1_000_000) -> float:
    if accounts <= 0 or years <= 0 or target <= 0:
        raise ValueError('invalid target or baseline')
    return max(0.0, (target / accounts) ** (1 / years) - 1)


def forecasts() -> dict:
    facts = json.loads((CONTENT_DIR / 'octoverse' / '2025-country-outlook.json').read_text('utf-8'))
    codes = [r['economy'] for r in facts['rows']]
    if len(set(codes)) != len(codes) or 'DZ' in codes or any(r['projected_accounts'] <= 0 for r in facts['rows']):
        raise ValueError('invalid published forecast data')
    return facts


def country(ctx, code):
    for group in ('economy', 'world'):
        if f'{group}.{code}' in ctx.site.catalog.flat['en']:
            return ctx.t(f'{group}.{code}')
    return Markup(esc(code))


def csv_url(ctx, rows):
    buf = io.StringIO(newline='')
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(('economy', 'rank', 'accounts', 'yoy', 'quarter'))
    writer.writerows((r['economy'], r['rank'], r['accounts'], r['yoy'] if r['yoy'] is not None else '', r['quarter']) for r in rows)
    return ctx.site.add_file(f'/data/{ctx.site.data.folder.name}/global-accounts.csv', buf.getvalue().encode())


def section(ctx, id_, kind, inner, **values):
    return Markup(str(C.section(id_, ctx.t(f'outlook.{kind}.eyebrow'), ctx.t(f'outlook.{kind}.title'), inner,
                               lede=ctx.t(f'outlook.{kind}.lede', **values))).replace('section section-m', 'section section-m outlook-section'))


def bars(ctx, rows, *, forecast=False):
    largest = max(r['projected_accounts' if forecast else 'accounts'] for r in rows)
    items = []
    for r in rows:
        v = r['projected_accounts' if forecast else 'accounts']
        value = ctx.t('outlook.forecast.value', value=num(fdec(v / 1e6, 1, ctx.lang))) if forecast else num(fint(v, ctx.lang))
        rank = '' if forecast else f'<span class="num country-rank">{r["rank"]:02d}</span>'
        items.append(f'<li class="country-bar{" is-dz" if r["economy"] == "DZ" else ""}" data-economy="{r["economy"]}">'
                     f'<div class="country-bar-label">{rank}<span>{country(ctx, r["economy"])}</span>{value}</div>'
                     f'<span class="country-bar-track" aria-hidden="true"><span style="width:{v / largest * 100:.4f}%"></span></span></li>')
    return Markup(f'<ol class="country-bars{" forecast-bars" if forecast else ""}">{join(items)}</ol>')


def world(ctx):
    data = ctx.site.data
    rows = standings(data)
    dz = next(r for r in rows if r['economy'] == 'DZ')
    q = quarter_label(data.quarter, ctx.lang)
    stats = (f'<dl class="world-stats"><div class="world-position"><dt>{ctx.t("outlook.world.rank")}</dt>'
             f'<dd><span class="num">#{dz["rank"]}</span><small>{ctx.t("outlook.world.of", n=num(len(rows)))}</small></dd></div>'
             f'<div><dt>{ctx.t("outlook.world.accounts")}</dt><dd>{num(fint(dz["accounts"], ctx.lang))}</dd></div>'
             f'<div><dt>{ctx.t("outlook.world.growth")}</dt><dd class="mint">{num(fpct(dz["yoy"], 1, ctx.lang)) if dz["yoy"] is not None else "—"}</dd></div></dl>')
    preview = rows[:5] + ([] if dz in rows[:5] else [dz])
    viz = f'<figure class="world-preview"><figcaption>{ctx.t("outlook.world.caption", quarter=q)}</figcaption>{bars(ctx, preview)}</figure>'
    source = f'<p class="outlook-source">{ctx.t("outlook.world.source", quarter=q)} '
    source += f'<a href="{csv_url(ctx, rows)}" download>{ctx.t("outlook.world.csv")}</a></p>'
    inner = Markup(f'<div class="world-grid">{stats}{viz}</div><p class="outlook-note">{ctx.t("outlook.world.note")}</p>{source}'
                   f'<div class="outlook-actions">{C.btn(ctx.t("outlook.world.full"), ctx.url("rankings", hash="global-accounts"), "secondary")}</div>')
    return section(ctx, 'world-standing', 'world', inner)


def global_table(ctx):
    rows = standings(ctx.site.data)
    q = quarter_label(ctx.site.data.quarter, ctx.lang)
    head = [(ctx.t('outlook.world.country'), 'start'), (ctx.t('outlook.world.position'), 'end'),
            (ctx.t('outlook.world.count'), 'end'), (ctx.t('outlook.world.yoy'), 'end')]
    body = [(r['economy'], [Markup(f'{country(ctx, r["economy"])} <span class="economy-code">{r["economy"]}</span>'),
                            (num(r['rank']), r['rank']), (num(fint(r['accounts'], ctx.lang)), r['accounts']),
                            ('—', '') if r['yoy'] is None else (num(fpct(r['yoy'], 1, ctx.lang)), r['yoy'])]) for r in rows]
    table = C.data_table(ctx.t('outlook.world.table_caption', quarter=q, n=num(len(rows))), head, body,
                         sortable=True, sorted_by=(2, 'descending'), cls='global-accounts-table', highlight='DZ', announce=C.sort_text(ctx))
    table = Markup(str(table).replace('class="is-dz" data-key="DZ"', 'class="is-dz" data-key="DZ" id="global-accounts-DZ"'))
    inner = Markup(f'<p class="outlook-note">{ctx.t("outlook.world.note")}</p>'
                   f'<div class="outlook-actions">{C.btn(ctx.t("outlook.world.locate"), "#global-accounts-DZ", "secondary", "s")}</div>{table}'
                   f'<p class="outlook-source">{ctx.t("outlook.world.source", quarter=q)} '
                   f'<a href="{csv_url(ctx, rows)}" download>{ctx.t("outlook.world.csv")}</a></p>')
    return C.section('global-accounts', ctx.t('outlook.world.eyebrow'), ctx.t('outlook.world.table_title'), inner,
                     lede=ctx.t('outlook.world.table_lede'))


def outlook(ctx):
    facts = forecasts()
    url = ctx.site.add_file('/data/octoverse-2025/country-outlook.json', (json.dumps(facts, ensure_ascii=False, indent=2)+'\n').encode())
    radios = join(f'<label><input type="radio" name="outlook-group" value="{group}" id="outlook-{group}"'
                  f'{" checked" if group == "africa" else ""}><span>{ctx.t(f"outlook.forecast.{group}")}</span></label>' for group in ('africa', 'global'))
    plots = []
    for group in ('africa', 'global'):
        rows = [r for r in facts['rows'] if r['economy'] in AFRICAN_FORECASTS] if group == 'africa' else facts['rows'][:10]
        plots.append(f'<figure class="forecast-view forecast-{group}" aria-labelledby="forecast-{group}-caption">'
                     f'<figcaption id="forecast-{group}-caption">{ctx.t(f"outlook.forecast.{group}_caption")}</figcaption>'
                     f'<p class="forecast-unit">{ctx.t("outlook.forecast.unit")}</p>{bars(ctx, rows, forecast=True)}</figure>')
    inner = Markup(f'<div class="forecast-switch"><fieldset class="forecast-controls"><legend class="sr-only">{ctx.t("outlook.forecast.choose")}</legend>{radios}</fieldset>{join(plots)}</div>'
                   f'<p class="outlook-note">{ctx.t("outlook.forecast.note")}</p>'
                   f'{C.details(ctx.t("outlook.forecast.method_title"), Markup(f"<p>{ctx.t('outlook.forecast.method')}</p>"))}'
                   f'<p class="outlook-source">{ctx.t("outlook.forecast.source")} <a href="{SOURCE}">{ctx.t("outlook.world.read")}</a> · '
                   f'<a href="{url}" download>{ctx.t("outlook.forecast.data")}</a></p>'
                   f'<aside class="participation-note" aria-labelledby="participation-h"><h3 id="participation-h">{ctx.t("outlook.world.participation")}</h3>'
                   f'<p>{ctx.t("outlook.world.participation_text")} <a href="{SOURCE}">{ctx.t("outlook.world.read")}</a></p></aside>')
    return section(ctx, 'developer-outlook', 'forecast', inner)


def scenario(ctx):
    data = ctx.site.data
    years = horizon(data.quarter)
    # The fixed Q1 2030 scenario expires rather than silently becoming a backward forecast.
    if years <= 0:
        return Markup('')
    accounts = next(r['accounts'] for r in standings(data) if r['economy'] == 'DZ')
    q, end = quarter_label(data.quarter, ctx.lang), quarter_label(TARGET, ctx.lang)
    ceiling = math.ceil(max(1_000_000, future(accounts, .35, years)) / 500_000) * 500_000
    def path(rate):
        return ' '.join(f'{"M" if i == 0 else "L"}{44 + i / 48 * 410:.2f},{230 - future(accounts, rate, years * i / 48) / ceiling * 200:.2f}'
                        if i else f'M44,{230 - accounts / ceiling * 200:.2f}' for i in range(49))
    svg = (f'<svg class="scenario-chart" viewBox="0 0 480 260" aria-hidden="true" data-ceiling="{ceiling}">'
           f'<path class="scenario-grid" d="M44 30V230H454"/>'
           f'<path class="scenario-goal" d="M44 {230-1e6/ceiling*200:.2f}H454"/>'
           f'<text class="scenario-tick" x="8" y="236">0</text>'
           f'<text class="scenario-tick" x="44" y="20">{esc(fdec(ceiling/1e6, 1, ctx.lang))}M</text>'
           f'{join(f"<path class=\"scenario-reference\" d=\"{path(r)}\"/>" for r in (.1,.15,.2))}'
           f'<path class="scenario-selected" data-scenario-path d="{path(.15)}"/>'
           f'<circle class="scenario-endpoint" data-scenario-end cx="454" cy="{230-future(accounts,.15,years)/ceiling*200:.2f}" r="4"/></svg>')
    examples = [(str(r), [num(fpct(r, 0, ctx.lang)), (num(fint(round(future(accounts,r,years)), ctx.lang)), round(future(accounts,r,years)))]) for r in (.1,.15,.2)]
    table = C.data_table(ctx.t('outlook.scenario.table'), [(ctx.t('outlook.scenario.rate'), 'start'), (ctx.t('outlook.scenario.total', quarter=end), 'end')], examples)
    inner = Markup(f'<div class="scenario-panel" data-growth-scenario data-base="{accounts}" data-years="{years}" data-lang="{ctx.lang}">'
                   f'<div class="scenario-readout"><dl><div><dt>{ctx.t("outlook.scenario.result", quarter=end)}</dt>'
                   f'<dd><output class="num" dir="ltr" data-scenario-total aria-live="polite" aria-atomic="true">{fint(round(future(accounts,.15,years)),ctx.lang)}</output></dd></div>'
                   f'<div><dt>{ctx.t("outlook.scenario.required")}</dt><dd class="num scenario-needed" dir="ltr">{fpct(required_rate(accounts,years),2,ctx.lang)}</dd></div></dl>'
                   f'<div class="scenario-control" hidden><label for="scenario-growth">{ctx.t("outlook.scenario.label")}</label>'
                   f'<output for="scenario-growth" class="num" dir="ltr" data-scenario-rate>15%</output>'
                   f'<input id="scenario-growth" type="range" min="0" max="35" step="0.25" value="15" aria-describedby="scenario-assumptions">'
                   f'<span class="scenario-range-ends" aria-hidden="true"><span>0%</span><span>35%</span></span></div></div>'
                   f'<figure class="scenario-figure"><figcaption>{ctx.t("outlook.scenario.chart", start=q,end=end)}</figcaption>'
                   f'<p class="scenario-goal-label">{ctx.t("outlook.scenario.target")} <span class="num">1,000,000</span></p>{svg}'
                   f'<div class="scenario-dates"><span>{q}</span><span>{end}</span></div>'
                   f'<p class="scenario-legend"><span class="score-line" aria-hidden="true"></span>{ctx.t("outlook.scenario.selected")} · <span class="num" data-scenario-legend>15%</span></p>'
                   f'<p class="outlook-note">{ctx.t("outlook.scenario.references")}</p></figure></div>'
                   f'<p class="outlook-note" id="scenario-assumptions">{ctx.t("outlook.scenario.note",accounts=num(fint(accounts,ctx.lang)),quarter=q)}</p>'
                   f'{C.details(ctx.t("outlook.scenario.table"), Markup(f"{table}<p>{ctx.t('outlook.scenario.formula')}</p>"))}'
                   f'<aside class="scenario-action"><div><h3>{ctx.t("outlook.scenario.action_title")}</h3><p>{ctx.t("outlook.scenario.action_text")}</p></div>'
                   f'{C.btn(ctx.t("outlook.scenario.cta"),ctx.url("hub")+"?kind=gfi#issues")}</aside>')
    return section(ctx, 'algeria-scenario', 'scenario', inner, quarter=end)
