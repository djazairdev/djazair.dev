"""Stylesheet, scripts, fonts and icons.

Scripts are copied to ``dist/assets`` with content-hashed names. Fixed font subsets are
self-hosted there too. Each page inlines shared CSS and its own route's rules, saving a
render-blocking round trip without transferring unrelated pages' styles.
"""
from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .config import LANGS, STATIC_DIR
from .markup import Markup

# Fonts preloaded on every page: the files the first screen needs (see 05-fonts.css).
PRELOAD = {
    'en': ['tajawal-latin-400.woff2', 'jetbrains-mono-latin.woff2'],
    'ar': ['tajawal-arabic-400.woff2', 'jetbrains-mono-latin.woff2'],
}


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:10]


def minify_css(css: str) -> str:
    """Compact whitespace outside strings, preserving calc operators and descendant selectors."""
    tokens = re.split(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*.*?\*/)', css, flags=re.S)
    for i, token in enumerate(tokens):
        if token.startswith('/*'):
            tokens[i] = ''
        elif not token.startswith(('"', "'")):
            token = re.sub(r'\s+', ' ', token)
            tokens[i] = re.sub(r'\s*([{};])\s*', r'\1', token)
    return ''.join(tokens).strip()


@dataclass
class Assets:
    style: str                 # the whole stylesheet, for a <style> element in each page
    js: str
    fonts: set = field(default_factory=set)
    scripts: dict = field(default_factory=dict)   # name -> URL of page-specific scripts
    share: dict = field(default_factory=dict)     # lang -> URL of the 1200 × 630 share image (site/tools/share.py)
    release_share: dict = field(default_factory=dict)   # lang -> URL of the quarter's share image, when there is one
    styles: dict = field(default_factory=dict)          # route -> only the styles that page uses

    def inline_style(self, extra: str = '', route: str = '') -> Markup:
        """The stylesheet for a <style> element, with the page's own rules after it (Home's hero)."""
        if '</' in extra:
            raise ValueError('a page\'s rules must not contain "</": they are inlined in a <style> element')
        base = self.styles.get(route, self.style)
        css = base + minify_css(extra)
        return Markup(f'<style>{css}</style>')

    def preloads(self, lang: str, route: str = '') -> Markup:
        names = list(PRELOAD[lang])
        if route == 'hub':
            names.append(f'tajawal-{"latin" if lang == "en" else "arabic"}-800.woff2')
        return Markup(''.join(
            f'<link rel="preload" href="/assets/fonts/{name}" as="font" type="font/woff2" crossorigin>'
            for name in names if name in self.fonts))


def _write_hashed(out: Path, stem: str, ext: str, data: bytes) -> str:
    name = f'{stem}.{_hash(data)}.{ext}'
    (out / 'assets' / name).write_bytes(data)
    return f'/assets/{name}'


def build(out: Path, release: str = '', langs: tuple = LANGS) -> Assets:
    """``release``: the folder of the quarter being built (2026-q1), whose share images are used
    when site/tools/share.py --release drew them. ``langs``: the published languages, whose share
    images are copied."""
    (out / 'assets' / 'fonts').mkdir(parents=True, exist_ok=True)

    css_files = sorted((STATIC_DIR / 'css').glob('*.css'))
    parts = {p.name: minify_css(p.read_text('utf-8')) for p in css_files}
    css = ''.join(parts.values())
    common = {name for name in parts if int(name[:2]) < 50 or int(name[:2]) >= 90}
    groups = {
        'home': ('50-home.css',),
        'overview': ('51-index.css', '52-outlook.css'),
        'hub': ('53-hub.css',), 'localisation': ('53-hub.css',),
        'meetups': ('53-hub.css',), 'about': ('52-docs.css',),
        'data': ('52-docs.css', '55-data.css'),
        'notfound': (), 'root': (), 'invitation': (),
    }
    for route in ('peers', 'trends', 'languages', 'topics', 'collaboration', 'rankings'):
        groups[route] = ('51-index.css',)
    styles = {route: ''.join(value for name, value in parts.items() if name in common or name in extra)
              for route, extra in groups.items()}
    # Keep the issue feed stable on slow connections: use preloaded fonts on the
    # first paint when available, otherwise keep the fallback for this page load.
    styles['hub'] = styles['hub'].replace('font-display: swap', 'font-display: optional')
    if '</' in css:
        raise ValueError('the stylesheet must not contain "</": it is inlined in a <style> element')

    js_url = _write_hashed(out, 'site', 'js', (STATIC_DIR / 'js' / 'site.js').read_bytes())
    scripts = {}
    for path in sorted((STATIC_DIR / 'js').glob('*.js')):
        if path.name != 'site.js':
            scripts[path.stem] = _write_hashed(out, path.stem, 'js', path.read_bytes())

    fonts = set()
    for path in sorted((STATIC_DIR / 'fonts').glob('*.woff2')):
        shutil.copy2(path, out / 'assets' / 'fonts' / path.name)
        fonts.add(path.name)
    for path in sorted((STATIC_DIR / 'fonts').glob('*.txt')):   # font licences travel with the fonts
        shutil.copy2(path, out / 'assets' / 'fonts' / path.name)

    share = {path.stem: _write_hashed(out, f'share-{path.stem}', 'png', path.read_bytes())
             for path in sorted((STATIC_DIR / 'share').glob('*.png')) if path.stem in langs}
    release_share = {}
    if release:
        release_share = {path.stem: _write_hashed(out, f'share-{release}-{path.stem}', 'png', path.read_bytes())
                         for path in sorted((STATIC_DIR / 'share' / release).glob('*.png')) if path.stem in langs}

    shutil.copy2(STATIC_DIR / 'favicon.svg', out / 'favicon.svg')
    shutil.copy2(STATIC_DIR / 'logo.png', out / 'logo.png')
    return Assets(style=css, js=js_url, fonts=fonts, scripts=scripts, share=share, release_share=release_share,
                  styles=styles)
