"""The page at ``/``.

How ``/`` picks a language: a small inline script sends the reader to ``/ar/`` or
``/en/``. It uses the language the reader last chose with the switcher (stored in
``localStorage`` under ``djz-lang``), otherwise the first of the browser's preferred
languages that is Arabic or English, otherwise English. Without JavaScript the page
is a plain bilingual chooser, and search engines see it as the ``x-default`` page.
"""
from __future__ import annotations

from ..config import SITE_URL, THEME_COLOR
from ..context import Site
from ..icons import mark, wordmark
from ..layout import social
from ..markup import esc

REDIRECT_JS = (
    "(function(){var l;try{l=localStorage.getItem('djz-lang')}catch(e){}"
    "if(l!=='en'&&l!=='ar'){l='en';var n=navigator.languages||[navigator.language||''];"
    "for(var i=0;i<n.length;i++){var c=String(n[i]).toLowerCase().slice(0,2);"
    "if(c==='ar'){l='ar';break}if(c==='en')break}}"
    "location.replace('/'+l+'/'+location.search)})();"
)


def render(site: Site) -> str:
    cat = site.catalog
    en_tag, ar_tag = esc(cat.lookup('en', 'site.tagline')[0]), esc(cat.lookup('ar', 'site.tagline')[0])
    desc = esc(cat.lookup('en', 'pages.home.description')[0])
    share = social(site, 'en', f"djazair.dev · {cat.lookup('en', 'site.tagline')[0]}", cat.lookup('en', 'pages.home.description')[0],
                   SITE_URL + '/', cat.lookup('en', 'share.alt')[0])
    return f'''<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>djazair.dev · {en_tag}</title>
<meta name="description" content="{desc}">
<script>{REDIRECT_JS}</script>
<link rel="canonical" href="{SITE_URL}/">
<link rel="alternate" hreflang="en" href="{SITE_URL}/en/">
<link rel="alternate" hreflang="ar" href="{SITE_URL}/ar/">
<link rel="alternate" hreflang="x-default" href="{SITE_URL}/">
{share}
<meta name="theme-color" content="{THEME_COLOR}">
<meta name="color-scheme" content="dark">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
{site.assets.preloads('en')}
{site.assets.inline_style(route='root')}
</head>
<body class="chooser-page">
<main class="chooser">
{mark(96)}
<h1>{wordmark()}</h1>
<p class="chooser-tag">{en_tag}</p>
<p class="chooser-tag" lang="ar" dir="rtl">{ar_tag}</p>
<nav class="chooser-links" aria-label="Language · اللغة">
<a class="btn btn-primary" href="/en/" lang="en" hreflang="en" data-lang="en">English</a>
<a class="btn btn-secondary" href="/ar/" lang="ar" hreflang="ar" dir="rtl" data-lang="ar">العربية</a>
</nav>
</main>
</body>
</html>
'''
