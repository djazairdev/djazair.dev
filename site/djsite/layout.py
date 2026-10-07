"""The page shell: document head, skip link, header, Index sub-nav, notices and footer."""
from __future__ import annotations

from .config import BEACON_URL, LANGS, OG_LOCALES, OTHER, REPO_URL, SITE_URL, THEME_COLOR
from .context import Ctx, Page
from .icons import icon, mark, wordmark
from .markup import Markup, esc, join

# (main-nav key, route it links to)
MAIN_NAV = [('index', 'overview'), ('hub', 'hub'), ('reports', 'reports'), ('methodology', 'methodology'), ('data', 'data')]

# Index sections, in order; an item shows only once its page exists.
SUB_NAV = ['overview', 'peers', 'trends', 'languages', 'topics', 'collaboration', 'rankings']

# (heading key, [(label key, route key, #hash)])
FOOTER = [
    ('footer.index', [('subnav.overview', 'overview', ''), ('subnav.peers', 'peers', ''),
                      ('subnav.trends', 'trends', ''), ('subnav.languages', 'languages', ''), ('subnav.topics', 'topics', '')]),
    ('footer.hub', [('footer.issues', 'hub', 'issues'), ('footer.projects', 'hub', 'projects'),
                    ('footer.list', 'hub', 'list')]),
    ('footer.project', [('nav.methodology', 'methodology', ''), ('footer.data', 'data', ''),
                        ('footer.changelog', 'data', 'changelog'), ('footer.corrections', 'data', 'corrections'),
                        ('footer.about', 'about', '')]),
]


def _current(ctx: Ctx, target: str) -> str:
    """aria-current value for a link to route ``target``: 'page' on that page, 'true' inside its section."""
    return 'page' if ctx.route.key == target else 'true'


def main_nav_links(ctx: Ctx) -> Markup:
    out = []
    for section, target in MAIN_NAV:
        if not ctx.has(target):
            continue
        cur = f' aria-current="{_current(ctx, target)}"' if ctx.route.section == section else ''
        out.append(f'<a href="{ctx.url(target)}"{cur}>{ctx.t("nav." + section)}</a>')
    return join(out)


def lang_switch(ctx: Ctx) -> Markup:
    out = []
    for code in LANGS:
        target = ctx.route.key if ctx.route.switchable else 'home'
        label = 'EN' if code == 'en' else 'ع'
        name = 'English' if code == 'en' else 'العربية'
        cur = ' aria-current="true"' if code == ctx.lang else ''
        out.append(f'<a href="{ctx.url(target, lang=code)}" lang="{code}" hreflang="{code}" aria-label="{name}"'
                   f' data-lang="{code}"{cur}>{label}</a>')
    return Markup(f'<div class="lang-switch" role="group" aria-label="{ctx.ta("a11y.language")}">{join(out)}</div>')


def header(ctx: Ctx) -> Markup:
    return Markup(f'''<header class="site-header">
<div class="container header-row">
<a class="brand" href="{ctx.url('home')}" aria-label="{ctx.ta('a11y.home')}">{mark(28)}{wordmark()}</a>
<nav class="main-nav" aria-label="{ctx.ta('a11y.main_nav')}">{main_nav_links(ctx)}</nav>
<div class="header-end">
{lang_switch(ctx)}
<a class="source-link wide" href="{REPO_URL}" aria-label="{ctx.ta('a11y.source')}">{icon('code', 17)}<span>{ctx.t('nav.source')}</span></a>
<details class="menu">
<summary class="menu-btn" aria-label="{ctx.ta('a11y.menu')}">{icon('menu', 20, 1.8, 'icon i-open')}{icon('close', 20, 1.8, 'icon i-close')}</summary>
<nav class="menu-panel" aria-label="{ctx.ta('a11y.main_nav')}">{main_nav_links(ctx)}
<a class="menu-source" href="{REPO_URL}">{icon('code', 17)}<span>{ctx.t('a11y.source')}</span></a></nav>
</details>
</div>
</div>
</header>''')


def subnav(ctx: Ctx) -> Markup:
    if not ctx.route.sub:
        return Markup('')
    out = []
    for key in SUB_NAV:
        if not ctx.has(key):
            continue
        cur = ' aria-current="page"' if ctx.route.sub == key else ''
        out.append(f'<a href="{ctx.url(key)}"{cur}>{ctx.t("subnav." + key)}</a>')
    return Markup(f'<nav class="subnav" aria-label="{ctx.ta("a11y.index_nav")}">'
                  f'<div class="container subnav-row">{join(out)}</div></nav>')


def footer(ctx: Ctx) -> Markup:
    cols = []
    for heading, links in FOOTER:
        items = ''.join(f'<li><a href="{ctx.url(route, hash=hash_)}">{ctx.t(label)}</a></li>'
                        for label, route, hash_ in links if ctx.has(route))
        cols.append(f'<nav class="footer-col" aria-label="{ctx.ta(heading)}"><h2>{ctx.t(heading)}</h2><ul>{items}</ul></nav>')
    return Markup(f'''<footer class="site-footer">
<div class="container">
<div class="footer-top">
<div class="footer-brand"><a class="brand brand-lg" href="{ctx.url('home')}" aria-label="{ctx.ta('a11y.home')}">{mark(36)}{wordmark()}</a>
<p>{ctx.t('site.tagline')}</p></div>
<div class="footer-cols">{join(cols)}</div>
</div>
<div class="footer-legal"><p>{ctx.t('footer.legal')}</p><p>{ctx.t('footer.independent')}</p></div>
</div>
</footer>''')


def notices(ctx: Ctx) -> Markup:
    items = []
    if not ctx.site.catalog.reviewed(ctx.lang):
        items.append(ctx.t('notice.draft'))
    if ctx.fallbacks:
        items.append(ctx.t('notice.fallback'))
    if not items:
        return Markup('')
    body = ''.join(f'<p>{icon("info", 16)}<span>{x}</span></p>' for x in items)
    return Markup(f'<div class="notice" role="note"><div class="container">{body}</div></div>')


def head_links(ctx: Ctx, page: Page) -> Markup:
    """Canonical and hreflang links, or noindex for pages kept out of search."""
    if not (ctx.route.indexed and page.indexed):
        return Markup('<meta name="robots" content="noindex">')
    key = ctx.route.key
    alts = ''.join(f'<link rel="alternate" hreflang="{l}" href="{ctx.abs_url(key, l)}">' for l in LANGS)
    x_default = SITE_URL + '/' if key == 'home' else ctx.abs_url(key, 'en')
    return Markup(f'<link rel="canonical" href="{ctx.abs_url(key)}">{alts}'
                  f'<link rel="alternate" hreflang="x-default" href="{x_default}">')


def social(site, lang: str, title: str, description: str, url: str, image_alt: str) -> Markup:
    """Open Graph and X card tags: what a shared link shows. One image per language."""
    image = site.assets.share.get(lang)
    tags = [('og:type', 'website'), ('og:site_name', 'djazair.dev'), ('og:title', title), ('og:description', description),
            ('og:url', url), ('og:locale', OG_LOCALES[lang]), ('og:locale:alternate', OG_LOCALES[OTHER[lang]])]
    if image:
        tags += [('og:image', SITE_URL + image), ('og:image:width', '1200'), ('og:image:height', '630'),
                 ('og:image:alt', image_alt)]
    out = ''.join(f'<meta property="{name}" content="{esc(value)}">' for name, value in tags)
    return Markup(out + f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">')


def share_tags(ctx: Ctx, page: Page, title: str) -> Markup:
    if not (ctx.route.indexed and page.indexed):
        return Markup('')
    # Shared links name the site separately (og:site_name), so the title drops " · djazair.dev".
    return social(ctx.site, ctx.lang, title.removesuffix(' · djazair.dev'), page.description,
                  ctx.abs_url(ctx.route.key), ctx.s('share.alt'))


def full_title(ctx: Ctx, page: Page) -> str:
    if page.full_title:
        return page.full_title
    if ctx.route.key == 'home':
        return f'djazair.dev · {ctx.s("site.tagline")}'
    if ctx.route.section == 'index' and ctx.route.key != 'overview':
        return f'{page.title} · {ctx.s("pages.overview.title")} · djazair.dev'
    return f'{page.title} · djazair.dev'


def document(ctx: Ctx, page: Page) -> str:
    assets = ctx.site.assets
    # Render the shell after the body so fallbacks from every part are counted before the notice.
    head_html, sub_html, foot_html = header(ctx), subnav(ctx), footer(ctx)
    title = full_title(ctx, page)
    scripts = ''.join(f'<script src="{src}" defer></script>' for src in (assets.js, *page.scripts))
    if ctx.site.analytics:      # Cloudflare Web Analytics: no cookies (docs/deploy.md#analytics)
        scripts += f'<script src="{BEACON_URL}" defer data-cf-beacon=\'{{"token": "{ctx.site.analytics}"}}\'></script>'
    return f'''<!doctype html>
<html lang="{ctx.lang}" dir="{ctx.dir}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(page.description)}">
{head_links(ctx, page)}
{share_tags(ctx, page, title)}
<meta name="theme-color" content="{THEME_COLOR}">
<meta name="color-scheme" content="dark">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
{assets.preloads(ctx.lang)}
{assets.inline_style()}
{scripts}
{page.head}
</head>
<body>
<a class="skip" href="#main">{ctx.t('a11y.skip')}</a>
{head_html}
{sub_html}
{notices(ctx)}
<main id="main" tabindex="-1">
{page.body}
</main>
{foot_html}
</body>
</html>
'''
