"""HTML-safe strings.

Every helper that returns HTML returns ``Markup``. Anything else (data values,
names read from GitHub, numbers) goes through ``esc`` before it reaches a page.
"""
from __future__ import annotations

import html
from typing import Iterable


class Markup(str):
    """A string that is already safe HTML; ``esc`` leaves it unchanged."""

    __slots__ = ()

    def __html__(self) -> 'Markup':
        return self


def esc(value) -> Markup:
    """Escape text for use in element content or a double-quoted attribute."""
    if isinstance(value, Markup):
        return value
    if value is None:
        return Markup('')
    return Markup(html.escape(str(value), quote=True))


def join(parts: Iterable, sep: str = '') -> Markup:
    """Join parts that are already HTML (f-strings built from escaped values)."""
    return Markup(sep.join(str(p) for p in parts))


def attrs(**kw) -> Markup:
    """Render attributes. ``class_`` → ``class``, ``aria_label`` → ``aria-label``.

    ``True`` renders a bare attribute; ``False`` and ``None`` drop it.
    """
    out = []
    for key, value in kw.items():
        if value is None or value is False:
            continue
        name = key.rstrip('_').replace('_', '-')
        out.append(f' {name}' if value is True else f' {name}="{esc(value)}"')
    return Markup(''.join(out))
