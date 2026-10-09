"""Deterministic public discovery files. All addresses use the production canonical domain."""
from __future__ import annotations

from xml.etree import ElementTree as ET
import re

from .config import CONTENT_DIR, REPO_URL, SITE_URL
from .context import Ctx
from .markdown import sections

# Renew this after checking that the reporting channels still work (RFC 9116).
SECURITY_EXPIRES = '2027-10-01T00:00:00Z'
SECURITY = f'''Contact: {REPO_URL}/security/advisories/new
Contact: mailto:contact@djazair.dev
Expires: {SECURITY_EXPIRES}
Preferred-Languages: en, ar
Canonical: {SITE_URL}/.well-known/security.txt
Policy: {REPO_URL}/blob/main/SECURITY.md
'''


def write(out, site, xml: str) -> None:
    urls = [node.text for node in ET.fromstring(xml).findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    (out / 'sitemap.txt').write_text('\n'.join(urls) + '\n', 'utf-8')
    (out / '.well-known').mkdir(exist_ok=True)
    (out / '.well-known' / 'security.txt').write_text(SECURITY, 'utf-8')
    (out / 'security.txt').write_text(SECURITY, 'utf-8')
    data = site.data
    guide = f'''# djazair.dev

> An open initiative helping Algeria's developers understand their community, contribute to open source, propose and vote on project ideas, and meet collaborators in their cities.

The Developer Index measures GitHub accounts and activity using the GitHub Innovation Graph.
The latest measured quarter is {data.quarter}; its source release was published on {data.release_date}.
Accounts include inactive accounts and are assigned by network location. They are not a count of professional developers or active open-source contributors.
Rank 1 means the highest value for one measure, not the best developers. There is no combined score.
GitHub Octoverse's 2030 outlook is a separate published forecast. The Algeria calculator uses illustrative assumptions, not a prediction.
Quarterly derived data is CC0; population inputs are World Bank CC BY 4.0. Do not apply CC0 to the separately sourced Octoverse forecast.

## Main pages

'''
    for key in ('home', 'overview', 'rankings', 'peers', 'trends', 'languages', 'topics', 'collaboration', 'hub', 'meetups', 'data', 'about'):
        if key not in site.routes or 'en' not in site.indexed.get(key, ()):
            continue
        ctx = Ctx(site, 'en', site.routes[key])
        label = 'Home' if key == 'home' else ctx.s(f'pages.{key}.title')
        guide += f'- [{label}]({ctx.abs_url(key)}): English page; Arabic version at {ctx.abs_url(key, lang="ar")}\n'
    guide += f'''
## Data and definitions

- [Data guide in Markdown]({SITE_URL}/en/data/index.md): release, definitions, limitations, and direct CSV/JSON download links.
- [Latest release pointer]({SITE_URL}/data/latest.json): resolve the current immutable release folder.
- [Release manifest]({SITE_URL}/data/{data.folder.name}/manifest.json): file sizes, SHA-256 checksums and source references.
- [Release README]({SITE_URL}/data/{data.folder.name}/README.md): table descriptions and licensing.
- [Data dictionary]({REPO_URL}/blob/main/data/README.md): column definitions and formulas.
- [All indexed pages]({SITE_URL}/sitemap.txt): canonical English and Arabic URLs.

## Participation

- [Open source]({SITE_URL}/en/hub/): find contribution opportunities and list projects.
- [Propose and vote on ideas]({REPO_URL}/discussions/categories/ideas): GitHub Discussions.
- [Meet local collaborators](https://founders.coffee/ar/algeria): founders.coffee's Algeria community; event registration is on that separate service.
- [Organisation](https://github.com/djazairdev): public projects and contributions.

## Optional

- [Source code]({REPO_URL}): pipeline, site build and contribution documentation.
- [Security reporting]({SITE_URL}/.well-known/security.txt): private disclosure channels.
'''
    (out / 'llms.txt').write_text(guide, 'utf-8')
    # A native Markdown guide avoids requiring AI readers to interpret chart SVGs or animation.
    for lang in ('en', 'ar'):
        ctx = Ctx(site, lang, site.routes['data'])
        text = f'# {ctx.s("pages.data.title")}\n\n{ctx.s("pages.data.description")}\n\n'
        text += f'{data.quarter} · {data.release_date}\n\n'
        text += f'[Canonical HTML page]({ctx.abs_url("data")})\n\n'
        for section in sections((CONTENT_DIR / 'methodology' / f'{lang}.md').read_text('utf-8')):
            if section.id in ('sources', 'indicators', 'peer-groups', 'limitations', 'updates'):
                body = re.sub(r'route:([a-z-]+)', lambda m: ctx.abs_url('data' if m[1] == 'methodology' else m[1]), section.body)
                text += f'## {section.title}\n\n{body}\n\n'
        text += '\n## CSV and JSON\n\n'
        for table in sorted({f['table'] for f in data.files.values() if 'table' in f}):
            text += f'### {ctx.s(f"downloads.t.{table}.title")}\n\n{ctx.s(f"downloads.t.{table}.text")}\n\n'
            for name, entry in sorted(data.files.items()):
                if entry.get('table') == table:
                    text += f'- [{name}]({SITE_URL}/data/{data.folder.name}/{name})\n'
            text += '\n'
        text += f'[Column definitions and formulas]({REPO_URL}/blob/main/data/README.md)\n'
        (out / lang / 'data' / 'index.md').write_text(text, 'utf-8')
