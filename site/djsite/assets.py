"""Stylesheet, script, fonts and icons: copied to ``dist/assets`` with content-hashed names."""
from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .config import STATIC_DIR
from .markup import Markup

# Fonts preloaded on every page: the files the first screen needs (see 00-fonts.css).
PRELOAD = {
    'en': ['tajawal-latin-400.woff2', 'jetbrains-mono-latin.woff2'],
    'ar': ['tajawal-arabic-400.woff2', 'jetbrains-mono-latin.woff2'],
}


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:10]


def minify_css(css: str) -> str:
    """Drop comments and indentation. Safe for our own CSS, which keeps strings simple."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    lines = (line.strip() for line in css.splitlines())
    return '\n'.join(line for line in lines if line)


@dataclass
class Assets:
    css: str
    js: str
    fonts: set = field(default_factory=set)
    scripts: dict = field(default_factory=dict)   # name -> URL of page-specific scripts

    def preloads(self, lang: str) -> Markup:
        return Markup(''.join(
            f'<link rel="preload" href="/assets/fonts/{name}" as="font" type="font/woff2" crossorigin>'
            for name in PRELOAD[lang] if name in self.fonts))


def _write_hashed(out: Path, stem: str, ext: str, data: bytes) -> str:
    name = f'{stem}.{_hash(data)}.{ext}'
    (out / 'assets' / name).write_bytes(data)
    return f'/assets/{name}'


def build(out: Path) -> Assets:
    (out / 'assets' / 'fonts').mkdir(parents=True, exist_ok=True)

    css_files = sorted((STATIC_DIR / 'css').glob('*.css'))
    css = '\n'.join(minify_css(p.read_text('utf-8')) for p in css_files)
    css_url = _write_hashed(out, 'site', 'css', css.encode('utf-8'))

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

    shutil.copy2(STATIC_DIR / 'favicon.svg', out / 'favicon.svg')
    return Assets(css=css_url, js=js_url, fonts=fonts, scripts=scripts)
