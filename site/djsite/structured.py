"""Search-readable metadata, using the same release and descriptions as the Data page."""
from __future__ import annotations

import calendar
import json

from .config import ORG_URL, SITE_URL
from .markup import Markup
from . import outlook

ORG_ID = f'{SITE_URL}/#organization'
CATALOG_ID = f'{SITE_URL}/en/data/#catalog'


def script(value: dict) -> Markup:
    # JSON escaping alone does not stop a source string from closing an HTML script tag.
    payload = json.dumps(value, ensure_ascii=True, separators=(',', ':'))
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return Markup(f'<script type="application/ld+json">{payload}</script>')


def page(ctx, title: str, description: str, indexed: bool = True) -> Markup:
    if not ctx.route.indexed or not indexed:
        return Markup('')
    url = ctx.abs_url(ctx.route.key)
    webpage = {'@type': 'WebPage', '@id': url + '#webpage', 'url': url,
               'name': title, 'description': description, 'inLanguage': ctx.lang,
               'isPartOf': {'@id': SITE_URL + '/#website'}}
    if ctx.route.key == 'data':
        webpage['mainEntity'] = {'@id': CATALOG_ID}
    return script({'@context': 'https://schema.org', '@graph': [
        {'@type': 'Organization', '@id': ORG_ID, 'name': 'djazair.dev',
         'url': SITE_URL + '/', 'sameAs': [ORG_URL]},
        {'@type': 'WebSite', '@id': SITE_URL + '/#website', 'name': 'djazair.dev',
         'url': SITE_URL + '/', 'inLanguage': ['en', 'ar'], 'publisher': {'@id': ORG_ID}},
        webpage]})


def quarter_date(q: str, end: bool = False) -> str:
    year, quarter = q.split('-Q')
    month = (int(quarter) - 1) * 3 + (3 if end else 1)
    day = calendar.monthrange(int(year), month)[1] if end else 1
    return f'{year}-{month:02d}-{day:02d}'


def download(url: str, fmt: str, size: int) -> dict:
    return {'@type': 'DataDownload', 'contentUrl': SITE_URL + url,
            'encodingFormat': {'csv': 'text/csv', 'json': 'application/json'}[fmt],
            'contentSize': f'{size} bytes'}


def datasets(ctx) -> list:
    data = ctx.site.data
    base = f'/data/{data.folder.name}/'
    grouped = {}
    for name, entry in sorted(data.files.items()):
        if 'table' in entry:
            grouped.setdefault(entry['table'], []).append(download(base + name, name.rsplit('.', 1)[1], entry['bytes']))
    result = []
    for table, distributions in grouped.items():
        source = data.table(table)
        quarters = sorted({r['quarter'] for r in source['rows'] if r.get('quarter')})
        node = {'@type': 'Dataset', '@id': SITE_URL + base + table + '#dataset',
                'identifier': f'djazair.dev:{data.folder.name}:{table}',
                'name': ctx.s(f'downloads.t.{table}.title'),
                'description': ctx.s(f'downloads.t.{table}.text'),
                'url': ctx.abs_url('data') + '#t-' + table,
                'inLanguage': ctx.lang, 'creator': {'@id': ORG_ID},
                'license': data.manifest['licence_url'],
                'version': data.release, 'dateModified': data.manifest['generated_at'][:10],
                'isBasedOn': [data.manifest['source']],
                'includedInDataCatalog': {'@id': CATALOG_ID},
                'distribution': distributions,
                'variableMeasured': [{'@type': 'PropertyValue', 'name': c['name'], 'description': c['description']}
                                     for c in source['columns']]}
        if quarters:
            node['temporalCoverage'] = quarter_date(quarters[0]) + '/' + quarter_date(quarters[-1], end=True)
        if table == 'gdc26':
            node['temporalCoverage'] = '2025-07-01/2026-06-30'
            node['isBasedOn'].append(data.manifest['gdc26']['source'])
        # Retain the separate population-input licence rather than implying it is CC0.
        if (any('population' in c['name'] or 'per_million' in c['name'] for c in source['columns'])
                or any(r.get('indicator') == 'accounts_per_million' for r in source['rows'])):
            indicator = 'SP.POP.1564.TO' if table == 'gdc26' else 'SP.POP.TOTL'
            node['isBasedOn'].append({'@type': 'Dataset', 'name': f'World Bank, World Development Indicators ({indicator})',
                                     'url': f'https://data.worldbank.org/indicator/{indicator}',
                                     'license': 'https://creativecommons.org/licenses/by/4.0/'})
        result.append(node)
    global_url = base + 'global-accounts.csv'
    result.append({'@type': 'Dataset', '@id': SITE_URL + global_url + '#dataset',
                   'name': ctx.s('downloads.country.standing.title'),
                   'description': ctx.s('downloads.country.standing.text').replace('{quarter}', data.quarter),
                   'url': ctx.abs_url('data') + '#country-data', 'inLanguage': ctx.lang,
                   'creator': {'@id': ORG_ID}, 'license': data.manifest['licence_url'],
                   'version': data.release, 'isBasedOn': data.manifest['source'],
                   'temporalCoverage': quarter_date(data.quarter) + '/' + quarter_date(data.quarter, end=True),
                   'spatialCoverage': 'Worldwide', 'includedInDataCatalog': {'@id': CATALOG_ID},
                   'distribution': [download(global_url, 'csv', len(ctx.site.files[global_url]))]})
    facts = outlook.forecasts()
    forecast_url = '/data/octoverse-2025/country-outlook.json'
    # This publication is a forecast. Its original publisher has not supplied a CC0 licence.
    result.append({'@type': 'Dataset', '@id': SITE_URL + forecast_url + '#dataset',
                   'name': ctx.s('downloads.country.forecast.title'),
                   'description': ctx.s('downloads.country.forecast.text'),
                   'url': ctx.abs_url('data') + '#country-data', 'inLanguage': ctx.lang,
                   'creator': {'@type': 'Organization', 'name': 'GitHub', 'url': 'https://github.com/'},
                   'isBasedOn': facts['source_url'], 'citation': facts['source_url'],
                   'datePublished': facts['published'], 'temporalCoverage': str(facts['target_year']),
                   'includedInDataCatalog': {'@id': CATALOG_ID},
                   'distribution': [download(forecast_url, 'json', len(ctx.site.files[forecast_url]))]})
    return result


def catalog(ctx) -> Markup:
    nodes = datasets(ctx)
    return script({'@context': 'https://schema.org', '@graph': [
        {'@type': 'DataCatalog', '@id': CATALOG_ID, 'name': 'djazair.dev Developer Index data',
         'url': ctx.abs_url('data'), 'publisher': {'@id': ORG_ID},
         'dataset': [{'@id': node['@id']} for node in nodes]}, *nodes]})
