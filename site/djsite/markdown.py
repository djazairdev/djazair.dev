"""A small Markdown renderer for the text pages (Methodology, About), standard library only (D21).

It covers what ``content/`` uses and nothing more:

- ``## Heading {#id}`` (the page module usually splits a file into sections at ``##`` first);
- paragraphs, ``-`` and ``1.`` lists, pipe tables;
- ``**bold**``, ``*italic*``, `` `code` `` (always left to right) and ``[links](url)``. A link to
  ``route:<key>`` or ``route:<key>#<id>`` goes to that page in the reader's language;
- ``{{name}}`` placeholders, filled with values the page computes from the data, so figures
  in the text stay true when the data changes. An unknown name fails the build;
- directive blocks, which a page draws with its own components::

      ::: name argument
      Markdown lines
      :::

Text is escaped; content can't inject HTML.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .markup import Markup, esc

_HEADING = re.compile(r'^(#{1,4})\s+(.*?)\s*(?:\{#([\w-]+)\})?\s*$')
_DIRECTIVE = re.compile(r'^(:{3,})\s*([\w-]+)\s*(.*)$')
_UL = re.compile(r'^\s*[-*]\s+(.*)$')
_OL = re.compile(r'^\s*\d+\.\s+(.*)$')
_PLACEHOLDER = re.compile(r'\{\{\s*([\w.]+)\s*\}\}')
_CODE = re.compile(r'`([^`]+)`')
_LINK = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)')
_BOLD = re.compile(r'\*\*(.+?)\*\*')
_ITALIC = re.compile(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])')


@dataclass
class Section:
    id: str
    title: str
    body: str                      # Markdown, without the heading


@dataclass
class Renderer:
    """``values`` fill placeholders (Markup is used as is; anything else is escaped).
    ``link(key, hash)`` resolves ``route:`` links. ``directives`` map a name to
    ``handler(lines, argument, renderer) -> Markup``."""
    values: dict = field(default_factory=dict)
    link: Optional[Callable] = None
    directives: dict = field(default_factory=dict)

    # ---- inline
    def fill(self, text: str) -> str:
        def value(m):
            name = m.group(1)
            if name not in self.values:
                raise KeyError(f'content placeholder {{{{{name}}}}} has no value')
            v = self.values[name]
            return str(v) if isinstance(v, Markup) else str(esc(v))
        return _PLACEHOLDER.sub(value, text)

    def href(self, url: str) -> str:
        if url.startswith('route:'):
            key, _, hash_ = url[6:].partition('#')
            if self.link is None:
                raise ValueError(f'{url}: no route resolver')
            return self.link(key, hash_)
        return url

    def inline(self, text: str) -> Markup:
        """One line or paragraph of inline Markdown."""
        parts = _CODE.split(text)
        out = []
        for i, part in enumerate(parts):
            if i % 2:                                    # code: escaped, no other formatting
                out.append(f'<code dir="ltr">{esc(part)}</code>')
                continue
            s = str(esc(part))
            s = _LINK.sub(lambda m: f'<a href="{esc(self.href(html.unescape(m.group(2))))}">{m.group(1)}</a>', s)
            s = _BOLD.sub(r'<strong>\1</strong>', s)
            s = _ITALIC.sub(r'<em>\1</em>', s)
            out.append(self.fill(s))
        return Markup(''.join(out))

    # ---- blocks
    def render(self, text) -> Markup:
        lines = text.splitlines() if isinstance(text, str) else list(text)
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            m = _DIRECTIVE.match(line)
            if m:
                fence, name, arg = m.groups()
                j = i + 1
                while j < len(lines) and lines[j].strip() != fence:
                    j += 1
                if j == len(lines):
                    raise ValueError(f'directive {name!r} is not closed with {fence}')
                if name not in self.directives:
                    raise KeyError(f'no handler for the {name!r} directive')
                out.append(str(self.directives[name](lines[i + 1:j], arg.strip(), self)))
                i = j + 1
                continue
            m = _HEADING.match(line)
            if m:
                level = len(m.group(1))
                ident = f' id="{m.group(3)}"' if m.group(3) else ''
                out.append(f'<h{level}{ident}>{self.inline(m.group(2))}</h{level}>')
                i += 1
                continue
            if line.lstrip().startswith('|'):
                j = i
                while j < len(lines) and lines[j].lstrip().startswith('|'):
                    j += 1
                out.append(str(self.table(lines[i:j])))
                i = j
                continue
            for pattern, tag in ((_UL, 'ul'), (_OL, 'ol')):
                if pattern.match(line):
                    items, i = self._list(lines, i, pattern)
                    out.append(f'<{tag}>' + ''.join(f'<li>{self.inline(x)}</li>' for x in items) + f'</{tag}>')
                    break
            else:
                j = i
                para = []
                while j < len(lines) and lines[j].strip() and not self._starts_block(lines[j]):
                    para.append(lines[j].strip())
                    j += 1
                out.append(f'<p>{self.inline(" ".join(para))}</p>')
                i = j
        return Markup('\n'.join(out))

    @staticmethod
    def _starts_block(line: str) -> bool:
        return bool(_DIRECTIVE.match(line) or _HEADING.match(line) or _UL.match(line) or _OL.match(line)
                    or line.lstrip().startswith('|'))

    @staticmethod
    def _list(lines: list, i: int, pattern) -> tuple:
        """List items from line ``i``: an item continues on indented lines."""
        items = []
        while i < len(lines):
            m = pattern.match(lines[i])
            if m:
                items.append(m.group(1).strip())
            elif lines[i].startswith(('  ', '\t')) and lines[i].strip() and items:
                items[-1] += ' ' + lines[i].strip()
            else:
                break
            i += 1
        return items, i

    def table(self, lines: list) -> Markup:
        rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
        if len(rows) < 2 or not all(re.fullmatch(r':?-{3,}:?', c) for c in rows[1]):
            raise ValueError(f'not a pipe table: {lines[0]!r}')
        head = ''.join(f'<th scope="col">{self.inline(c)}</th>' for c in rows[0])
        body = ''.join('<tr>' + ''.join(f'<th scope="row">{self.inline(c)}</th>' if n == 0 else f'<td>{self.inline(c)}</td>'
                                        for n, c in enumerate(r)) + '</tr>' for r in rows[2:])
        return Markup(f'<div class="table-wrap md-table" tabindex="0" role="region" aria-label="{esc(_text(rows[0][0]))}">'
                      f'<table class="dt cols-{len(rows[0])}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def _text(md: str) -> str:
    return re.sub(r'[*`]', '', md)


def sections(text: str) -> list:
    """Split a file at its ``## Title {#id}`` headings. Text before the first one is ignored."""
    out = []
    for block in re.split(r'^(?=## )', text, flags=re.M):
        if not block.startswith('## '):
            continue
        head, _, body = block.partition('\n')
        m = _HEADING.match(head)
        if not m or not m.group(3):
            raise ValueError(f'section heading without an id: {head!r}')
        out.append(Section(m.group(3), m.group(2), body.strip('\n')))
    return out


def items(lines: list) -> list:
    """Split directive lines at ``### Title {#id}`` headings: [(title, id, [lines])]."""
    out = []
    for line in lines:
        m = _HEADING.match(line)
        if m and len(m.group(1)) == 3:
            out.append((m.group(2), m.group(3), []))
        elif out:
            out[-1][2].append(line)
        elif line.strip():
            raise ValueError(f'text before the first ### heading in a directive: {line!r}')
    return out


def paragraphs(lines: list) -> list:
    """Lines grouped into paragraphs at blank lines."""
    out, cur = [], []
    for line in lines:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            out.append(' '.join(cur))
            cur = []
    if cur:
        out.append(' '.join(cur))
    return out
