"""Small HTML inspection helpers for the tests (standard library only)."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


class Doc(HTMLParser):
    """Collects what the site tests check: <html> attributes, title, links, anchors, ids."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.html = {}
        self.title = ''
        self.links = []          # <link> attribute dicts
        self.anchors = []        # <a> attribute dicts
        self.ids = set()
        self.body_first = None   # (tag, attrs) of the first element inside <body>
        self.elements = []       # (tag, attrs) in document order
        self._title = False
        self._body = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else '') for k, v in attrs}
        self.elements.append((tag, a))
        if 'id' in a:
            self.ids.add(a['id'])
        if tag == 'html':
            self.html = a
        elif tag == 'title' and not self._body:     # the document title, not an SVG's
            self._title = True
        elif tag == 'link':
            self.links.append(a)
        elif tag == 'body':
            self._body = True
            return
        if tag == 'a':
            self.anchors.append(a)
        if self._body and self.body_first is None:
            self.body_first = (tag, a)

    def handle_endtag(self, tag):
        if tag == 'title':
            self._title = False

    def handle_data(self, data):
        if self._title:
            self.title += data

    def find(self, tag: str, **want):
        """Elements with ``tag`` whose attributes include every ``want`` (class matches one token)."""
        out = []
        for t, a in self.elements:
            if t != tag:
                continue
            ok = True
            for k, v in want.items():
                k = k.rstrip('_').replace('_', '-')
                if k == 'class':
                    ok = v in a.get('class', '').split()
                else:
                    ok = a.get(k) == v
                if not ok:
                    break
            if ok:
                out.append(a)
        return out


def resolve(dist: Path, href: str):
    """Map a root-relative URL to the file the static host would serve, or None."""
    path = href.split('#', 1)[0].split('?', 1)[0]
    if not path.startswith('/'):
        return None
    target = dist / path.lstrip('/')
    if path.endswith('/'):
        target = target / 'index.html'
    return target


VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Texts(HTMLParser):
    """Text nodes with the direction of their nearest ancestor that sets one (dir or SVG direction)."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, direction or None)
        self.items = []          # (text, direction)
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        a = dict(attrs)
        self.stack.append((tag, a.get('dir') or a.get('direction')))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not data.strip() or any(t in ('script', 'style') for t, _ in self.stack):
            return
        direction = next((d for _, d in reversed(self.stack) if d), None)
        self.items.append((data, direction))
