"""A strict reader for the small part of YAML that ``projects.yml`` uses (ticket #15).

The project runs on the standard library only, so this reads:

- mappings (``key: value``) and block sequences (``- item``), nested by indentation with spaces;
- one-line flow sequences (``[arabic, payments]``);
- plain, 'single-quoted' and "double-quoted" scalars, ``true``/``false``, ``null``/``~`` and
  integers (YAML 1.2 core schema: ``yes`` and ``no`` stay strings), and ``#`` comments.

Anything else (anchors, tags, block scalars, flow mappings, tabs, duplicate keys) is an
error that names the line, rather than being read in some surprising way. Dates stay
strings; the schema checks their format. ``load`` also returns the line of every value,
keyed by its path, so errors can point at the line to fix.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

KEY = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?$')
INT = re.compile(r'^[-+]?[0-9]+$')
UNSUPPORTED = {'&': 'anchors', '*': 'aliases', '!': 'tags', '|': 'block scalars', '>': 'block scalars',
               '{': 'flow mappings', '%': 'directives', '@': 'reserved characters', '`': 'reserved characters'}


class YAMLError(ValueError):
    def __init__(self, line: int, message: str):
        super().__init__(f'line {line}: {message}')
        self.line = line
        self.message = message


@dataclass
class Line:
    no: int          # 1-based
    indent: int
    text: str        # without indentation and comment


def _strip_comment(raw: str, no: int) -> str:
    """Drop a trailing comment: a # at the start or after a space, outside quotes."""
    quote = None
    i = 0
    while i < len(raw):
        c = raw[i]
        if quote:
            if c == '\\' and quote == '"':
                i += 2
                continue
            if c == quote:
                if quote == "'" and raw[i + 1:i + 2] == "'":
                    i += 2
                    continue
                quote = None
        elif c in '"\'' and (i == 0 or raw[i - 1] in ' \t[,:-'):
            quote = c
        elif c == '#' and (i == 0 or raw[i - 1] in ' \t'):
            return raw[:i].rstrip()
        i += 1
    if quote:
        raise YAMLError(no, f'a {quote} quote is not closed on this line')
    return raw.rstrip()


def _lines(text: str) -> list:
    out = []
    for no, raw in enumerate(text.splitlines(), 1):
        if no == 1 and raw.startswith('﻿'):
            raw = raw[1:]
        body = raw.lstrip(' ')
        if body.startswith('\t'):
            raise YAMLError(no, 'indent with spaces, not tabs')
        content = _strip_comment(body, no)
        if not content or (content == '---' and not out):
            continue
        if content in ('---', '...'):
            raise YAMLError(no, 'only one document is allowed')
        out.append(Line(no, len(raw) - len(body), content))
    return out


def scalar(text: str, no: int):
    """A plain, quoted or flow-sequence value written on one line."""
    text = text.strip()
    if text.startswith('['):
        if not text.endswith(']'):
            raise YAMLError(no, 'a [ list must close with ] on the same line')
        inner = text[1:-1].strip()
        if not inner:
            return []
        items, buf, quote = [], '', None
        for c in inner:
            if quote:
                buf += c
                if c == quote:
                    quote = None
            elif c in '"\'':
                quote = c
                buf += c
            elif c in '[]{}':
                raise YAMLError(no, 'lists inside lists are not supported')
            elif c == ',':
                items.append(buf)
                buf = ''
            else:
                buf += c
        items.append(buf)
        if any(not item.strip() for item in items):
            raise YAMLError(no, 'an empty item in a [ ] list (two commas in a row, or a comma at the end)')
        return [scalar(item, no) for item in items]
    if text.startswith('"'):
        if len(text) < 2 or not text.endswith('"'):
            raise YAMLError(no, 'text after the closing " quote')
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise YAMLError(no, f'cannot read the quoted text {text}') from None
    if text.startswith("'"):
        if len(text) < 2 or not text.endswith("'") or "'" in text[1:-1].replace("''", ''):
            raise YAMLError(no, "text after the closing ' quote")
        return text[1:-1].replace("''", "'")
    if text[0] in UNSUPPORTED:
        raise YAMLError(no, f'{UNSUPPORTED[text[0]]} ({text[0]}) are not supported in this file')
    if text.startswith('- ') or text == '-':
        raise YAMLError(no, 'a list item must start on its own line')
    if re.search(r':(\s|$)', text):
        raise YAMLError(no, f'unexpected ": " in {text!r}; put the value in quotes')
    if text in ('true', 'True', 'TRUE'):
        return True
    if text in ('false', 'False', 'FALSE'):
        return False
    if text in ('null', 'Null', 'NULL', '~'):
        return None
    if INT.match(text):
        return int(text)
    return text


class _Parser:
    def __init__(self, lines: list):
        self.lines = lines
        self.i = 0
        self.where: dict = {}          # path -> line

    def peek(self):
        return self.lines[self.i] if self.i < len(self.lines) else None

    def block(self, indent: int, path: tuple):
        line = self.peek()
        if self._is_item(line):
            return self.sequence(line.indent, path)
        return self.mapping(line.indent, path)

    @staticmethod
    def _is_item(line) -> bool:
        return line is not None and (line.text == '-' or line.text.startswith('- '))

    def mapping(self, indent: int, path: tuple) -> dict:
        out: dict = {}
        while (line := self.peek()) is not None and line.indent == indent and not self._is_item(line):
            m = KEY.match(line.text)
            if not m:
                raise YAMLError(line.no, f'expected "key: value", found {line.text!r}')
            key, rest = m.group(1), m.group(2)
            if key in out:
                raise YAMLError(line.no, f'"{key}" appears twice')
            self.i += 1
            self.where[path + (key,)] = line.no
            nxt = self.peek()
            if rest:
                out[key] = scalar(rest, line.no)
            elif nxt is not None and (nxt.indent > indent or (nxt.indent == indent and self._is_item(nxt))):
                out[key] = self.block(nxt.indent, path + (key,))
            else:
                out[key] = None
        line = self.peek()
        if line is not None and line.indent > indent:
            raise YAMLError(line.no, 'unexpected indentation')
        return out

    def sequence(self, indent: int, path: tuple) -> list:
        out: list = []
        while (line := self.peek()) is not None and line.indent == indent and self._is_item(line):
            here = path + (len(out),)
            self.where[here] = line.no
            rest = line.text[1:].lstrip(' ')
            if not rest:
                self.i += 1
                nxt = self.peek()
                out.append(self.block(nxt.indent, here) if nxt is not None and nxt.indent > indent else None)
            elif KEY.match(rest):
                # "- key: value" starts a mapping whose keys line up with the first one.
                column = indent + len(line.text) - len(rest)
                self.lines[self.i] = Line(line.no, column, rest)
                out.append(self.mapping(column, here))
            else:
                self.i += 1
                out.append(scalar(rest, line.no))
        line = self.peek()
        if line is not None and line.indent > indent:
            raise YAMLError(line.no, 'unexpected indentation')
        return out


def load(text: str) -> tuple:
    """(value, {path: line}) for ``text``. Raises YAMLError."""
    lines = _lines(text)
    if not lines:
        return None, {}
    parser = _Parser(lines)
    if lines[0].indent:
        raise YAMLError(lines[0].no, 'the first line must not be indented')
    value = parser.block(0, ())
    if parser.peek() is not None:
        raise YAMLError(parser.peek().no, 'unexpected indentation')
    return value, parser.where
