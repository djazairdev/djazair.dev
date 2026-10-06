"""Interface strings: one JSON file per language in ``site/i18n/``.

Rules (PRD §11 and D13):

- English is the source. A key that a page uses but ``en.json`` lacks fails the build.
- A key missing from ``ar.json`` falls back to the English text, marked ``lang="en"``,
  and the page shows a notice that some text isn't translated yet.
- ``ar.json`` carries ``_meta.reviewed``. Until a fluent reviewer signs the Arabic off,
  Arabic pages say that the text is a draft.

Strings are plain text: they are escaped when rendered. ``{name}`` placeholders are
filled with values that are escaped too, unless they are already ``Markup``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import LANGS
from .markup import Markup, esc

_PLACEHOLDER = re.compile(r'\{(\w+)\}')


class MissingString(KeyError):
    """A page asked for a key that en.json doesn't have."""


def _flatten(tree: dict, prefix: str = '') -> dict:
    out = {}
    for key, value in tree.items():
        if key.startswith('_'):
            continue
        name = f'{prefix}{key}'
        if isinstance(value, dict):
            out.update(_flatten(value, name + '.'))
        else:
            out[name] = value
    return out


def fill(template: str, values: dict) -> Markup:
    """Escape ``template`` and replace its ``{name}`` placeholders."""
    def replace(match):
        name = match.group(1)
        if name not in values:
            raise KeyError(f'placeholder {{{name}}} has no value in {template!r}')
        return esc(values[name])
    return Markup(_PLACEHOLDER.sub(replace, esc(template)))


class Catalog:
    """All interface strings, by language."""

    def __init__(self, folder: Path):
        self.raw = {lang: json.loads((folder / f'{lang}.json').read_text('utf-8')) for lang in LANGS}
        self.flat = {lang: _flatten(self.raw[lang]) for lang in LANGS}

    def meta(self, lang: str) -> dict:
        return self.raw[lang].get('_meta', {})

    def reviewed(self, lang: str) -> bool:
        return lang == 'en' or bool(self.meta(lang).get('reviewed'))

    def lookup(self, lang: str, key: str):
        """Return ``(value, is_fallback)``."""
        source = self.flat['en']
        if key not in source:
            raise MissingString(f'{key!r} is missing from site/i18n/en.json')
        if lang != 'en':
            value = self.flat[lang].get(key)
            if value not in (None, '', []):
                return value, False
            return source[key], True
        return source[key], False

    def missing(self, lang: str) -> list:
        """Keys in en.json that ``lang`` doesn't translate."""
        return sorted(k for k in self.flat['en'] if self.flat[lang].get(k) in (None, '', []))

    def stale(self, lang: str) -> list:
        """Keys in ``lang`` that en.json no longer has."""
        return sorted(k for k in self.flat[lang] if k not in self.flat['en'])
