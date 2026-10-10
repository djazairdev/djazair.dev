"""The page at ``/``.

How ``/`` picks a language: a small inline script sends the reader to one of the published
languages (``config.PUBLISHED``, listed in ``data-langs`` on the page). It uses the language
the reader last chose with the switcher (stored in ``localStorage`` under ``djz-lang``) if it
is published, otherwise the first of the browser's preferred languages that is, otherwise the
first published one. Without JavaScript the page is a plain chooser, and search engines see it
as Home's ``x-default`` page.

While English is the only published language (D28: Arabic waits for its review, #61), the
script sends everyone to ``/en/``, keeping the query string, and without JavaScript a meta
refresh does the same, with a plain link to ``/en/`` as well.
"""
from __future__ import annotations

from ..config import DIRS, SITE_URL, THEME_COLOR
from ..context import Site
from ..icons import mark, wordmark
from ..layout import social
from ..markup import esc

# The same script whatever is published, so the hash in the Content-Security-Policy stays put.
REDIRECT_JS = (
    "(function(){var p=document.documentElement.getAttribute('data-langs').split(' '),l;"
    "try{l=localStorage.getItem('djz-lang')}catch(e){}"
    "if(p.indexOf(l)<0){l=p[0];var n=navigator.languages||[navigator.language||''];"
    "for(var i=0;i<n.length;i++){var c=String(n[i]).toLowerCase().slice(0,2);"
    "if(p.indexOf(c)>=0){l=c;break}}}"
    "location.replace('/'+l+'/'+location.search)})();"
)
NAMES = {'en': 'English', 'ar': 'العربية'}


def render(site: Site) -> str:
    cat, langs = site.catalog, site.published
    en_tag = esc(cat.lookup('en', 'site.tagline')[0])
    tags = ''.join(f'<p class="chooser-tag" lang="{lang}" dir="{DIRS[lang]}">{esc(cat.lookup(lang, "site.tagline")[0])}</p>'
                   for lang in langs)
    links = ''.join(f'<a class="btn btn-{"primary" if i == 0 else "secondary"}" href="/{lang}/" lang="{lang}" hreflang="{lang}" '
                    f'dir="{DIRS[lang]}" data-lang="{lang}">{NAMES[lang]}</a>' for i, lang in enumerate(langs))
    alts = ''.join(f'<link rel="alternate" hreflang="{lang}" href="{SITE_URL}/{lang}/">\n' for lang in langs)
    refresh = f'<meta http-equiv="refresh" content="0; url=/{langs[0]}/">\n' if len(langs) == 1 else ''
    desc = esc(cat.lookup('en', 'pages.home.description')[0])
    share = social(site, 'en', f"djazair.dev · {cat.lookup('en', 'site.tagline')[0]}", cat.lookup('en', 'pages.home.description')[0],
                   SITE_URL + '/', cat.lookup('en', 'share.alt')[0])
    return f'''<!doctype html>
<html lang="en" dir="ltr" data-langs="{' '.join(langs)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>djazair.dev · {en_tag}</title>
<meta name="description" content="{desc}">
<script>{REDIRECT_JS}</script>
{refresh}<link rel="canonical" href="{SITE_URL}/">
{alts}<link rel="alternate" hreflang="x-default" href="{SITE_URL}/">
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
{tags}
<nav class="chooser-links" aria-label="Language · اللغة">
{links}
</nav>
</main>
</body>
</html>
'''
