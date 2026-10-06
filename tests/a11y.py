"""Automated accessibility checks on built pages (ticket #29), standard library only.

They cover what tools like axe can decide from the markup alone: names for images, links,
buttons, form fields, tables and landmarks; heading order; unique ids and valid references;
ARIA roles; no focusable content inside aria-hidden; no positive tabindex; the page language.
Colour contrast is checked from the design tokens (tests/test_accessibility.py). What needs
a person (keyboard walkthrough, screen readers, zoom) is in docs/accessibility.md.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
ROLES = {'alert', 'application', 'article', 'banner', 'button', 'cell', 'checkbox', 'columnheader', 'combobox',
         'complementary', 'contentinfo', 'definition', 'dialog', 'document', 'feed', 'figure', 'form', 'grid',
         'gridcell', 'group', 'heading', 'img', 'link', 'list', 'listbox', 'listitem', 'log', 'main', 'marquee',
         'math', 'menu', 'menubar', 'menuitem', 'menuitemcheckbox', 'menuitemradio', 'meter', 'navigation', 'none',
         'note', 'option', 'presentation', 'progressbar', 'radio', 'radiogroup', 'region', 'row', 'rowgroup',
         'rowheader', 'scrollbar', 'search', 'searchbox', 'separator', 'slider', 'spinbutton', 'status', 'switch',
         'tab', 'table', 'tablist', 'tabpanel', 'term', 'textbox', 'timer', 'toolbar', 'tooltip', 'tree', 'treegrid',
         'treeitem'}
FIELDS = {'input', 'select', 'textarea'}
FOCUSABLE = {'a', 'button', 'input', 'select', 'textarea', 'summary'}


class Node:
    def __init__(self, tag: str, attrs: dict, parent=None):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list = []          # Node or str

    def get(self, name: str, default=None):
        return self.attrs.get(name, default)

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self, skip_hidden: bool = True) -> str:
        """Text content, without aria-hidden parts; images and SVGs count by their names."""
        out = []
        for child in self.children:
            if isinstance(child, str):
                out.append(child)
            elif skip_hidden and child.get('aria-hidden') == 'true':
                continue
            elif child.tag == 'img':
                out.append(child.get('alt', ''))
            elif child.tag == 'svg' and child.get('role') == 'img':
                out.append(child.get('aria-label', ''))
            elif child.tag not in ('script', 'style', 'template'):
                out.append(child.text(skip_hidden))
        return re.sub(r'\s+', ' ', ''.join(out)).strip()

    def __repr__(self):
        attrs = ' '.join(f'{k}="{v}"' for k, v in list(self.attrs.items())[:3])
        return f'<{self.tag} {attrs}>'


class Tree(HTMLParser):
    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.root = Node('#document', {})
        self.node = self.root
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v if v is not None else '') for k, v in attrs}, self.node)
        self.node.children.append(node)
        if tag not in VOID:
            self.node = node

    def handle_startendtag(self, tag, attrs):
        self.node.children.append(Node(tag, {k: (v if v is not None else '') for k, v in attrs}, self.node))

    def handle_endtag(self, tag):
        node = self.node
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.node = node.parent

    def handle_data(self, data):
        self.node.children.append(data)


def check(html: str, lang: str) -> list:
    """Problems found in one page, as readable strings (empty when the page passes)."""
    root = Tree(html).root
    nodes = list(root.walk())
    ids = {}
    problems = []
    for n in nodes:
        if 'id' in n.attrs:
            ids.setdefault(n.get('id'), []).append(n)

    def name_of(n: Node, content: bool = True) -> str:
        """The accessible name. Landmarks, groups and images take theirs from the author only
        (``content=False``); links, buttons and headings from their text as well."""
        if n.get('aria-labelledby'):
            return ' '.join(ids[i][0].text() for i in n.get('aria-labelledby').split() if i in ids).strip()
        if n.get('aria-label', '').strip():
            return n.get('aria-label').strip()
        if n.tag in FIELDS:
            if n.get('id') and any(x.tag == 'label' and x.get('for') == n.get('id') for x in nodes):
                return next(x for x in nodes if x.tag == 'label' and x.get('for') == n.get('id')).text()
            label = next((a for a in n.ancestors() if a.tag == 'label'), None)
            if label is not None:
                return label.text()
            return n.get('title', '').strip()
        return (n.text() if content else '') or n.get('title', '').strip()

    def hidden(n: Node) -> bool:
        return any(a.get('aria-hidden') == 'true' for a in [n, *n.ancestors()])

    # ---- the document
    html_el = next((n for n in nodes if n.tag == 'html'), None)
    if html_el is None or html_el.get('lang') != lang or html_el.get('dir') != ('rtl' if lang == 'ar' else 'ltr'):
        problems.append(f'html: lang/dir should be {lang}/{"rtl" if lang == "ar" else "ltr"}')
    if not any(n.tag == 'title' and n.text() for n in nodes if not any(a.tag == 'svg' for a in n.ancestors())):
        problems.append('the page has no <title>')
    mains = [n for n in nodes if n.tag == 'main']
    if len(mains) != 1:
        problems.append(f'{len(mains)} <main> elements')
    # A header or navigation before <main> repeats on every page: the first link must skip it.
    blocks = [n for n in nodes if n.tag in ('header', 'nav') and not any(a.tag == 'main' for a in n.ancestors())]
    skip = next((n for n in nodes if n.tag == 'a'), None)
    if blocks and (skip is None or not skip.get('href', '').startswith('#') or skip.get('href')[1:] not in ids):
        problems.append('the first link is not a skip link to the content')

    # ---- ids and references
    for i, found in ids.items():
        if len(found) > 1:
            problems.append(f'id "{i}" is used {len(found)} times')
    for n in nodes:
        for attr in ('aria-labelledby', 'aria-describedby', 'aria-controls'):
            for ref in n.get(attr, '').split():
                if ref not in ids:
                    problems.append(f'{n!r}: {attr} points to missing id "{ref}"')
        if n.tag == 'label' and n.get('for') and n.get('for') not in ids:
            problems.append(f'{n!r}: for points to missing id "{n.get("for")}"')
        href = n.get('href', '') if n.tag == 'a' else ''
        if href.startswith('#') and len(href) > 1 and href[1:] not in ids:
            problems.append(f'{n!r}: links to missing id "{href[1:]}"')

    # ---- roles, tabindex, aria-hidden
    for n in nodes:
        for role in n.get('role', '').split():
            if role not in ROLES:
                problems.append(f'{n!r}: unknown role "{role}"')
        if n.get('tabindex', '').lstrip('-').isdigit() and int(n.get('tabindex')) > 0:
            problems.append(f'{n!r}: positive tabindex')
        if n.get('aria-hidden') == 'true':
            for d in n.walk():
                if d is not n and (d.tag in FOCUSABLE and (d.tag != 'a' or d.get('href') is not None)
                                   or d.get('tabindex', '-1') not in ('-1', '')):
                    if d.tag != 'input' or d.get('type') != 'hidden':
                        problems.append(f'{d!r}: focusable inside aria-hidden {n!r}')

    # ---- names
    for n in nodes:
        if n.tag == 'img' and 'alt' not in n.attrs:
            problems.append(f'{n!r}: no alt')
        if n.tag == 'svg' and not any(a.tag == 'svg' for a in n.ancestors()):
            if n.get('aria-hidden') != 'true' and not hidden(n):
                if n.get('role') != 'img':
                    problems.append(f'{n!r}: an SVG must be aria-hidden or role="img" with a name')
                elif not (name_of(n) or any(c.tag == 'title' for c in n.children if isinstance(c, Node))):
                    problems.append(f'{n!r}: role="img" without a name')
        if hidden(n):
            continue
        if n.tag == 'a' and n.get('href') is not None and not name_of(n):
            problems.append(f'{n!r}: link without a name')
        if (n.tag == 'button' or n.get('role') == 'button') and not name_of(n):
            problems.append(f'{n!r}: button without a name')
        if n.tag == 'summary' and not name_of(n):
            problems.append(f'{n!r}: summary without a name')
        if n.tag in FIELDS and n.get('type') not in ('hidden', 'submit', 'reset', 'button') and not name_of(n):
            problems.append(f'{n!r}: form field without a label')
        if n.tag == 'table' and n.get('role') not in ('presentation', 'none'):
            if not (n.get('aria-label') or n.get('aria-labelledby') or any(c.tag == 'caption' for c in n.walk())):
                problems.append(f'{n!r}: table without a caption or label')
        if n.tag == 'th' and not n.get('scope') and not any(a.tag == 'thead' for a in n.ancestors()):
            problems.append(f'{n!r}: header cell outside <thead> without scope')
        if n.tag == 'fieldset' and not any(isinstance(c, Node) and c.tag == 'legend' for c in n.children):
            problems.append(f'{n!r}: fieldset without a legend')
        if n.get('role') in ('img', 'region', 'group', 'radiogroup', 'dialog') and n.tag != 'svg' and not name_of(n, False):
            if n.get('role') != 'group' or n.tag != 'details':
                problems.append(f'{n!r}: role="{n.get("role")}" without a name')

    # ---- landmarks: navigation landmarks need distinct names
    navs = [name_of(n, False) for n in nodes if n.tag == 'nav' and not any(a.tag == 'details' for a in n.ancestors())]
    for name in set(navs):
        if not name or navs.count(name) > 1:
            problems.append(f'navigation landmarks need distinct names: {navs}')
            break

    # ---- headings: one h1, no skipped levels
    levels = [int(n.tag[1]) for n in nodes if re.fullmatch(r'h[1-6]', n.tag) and not hidden(n)]
    if levels.count(1) != 1:
        problems.append(f'{levels.count(1)} <h1> elements')
    for before, after in zip(levels, levels[1:]):
        if after > before + 1:
            problems.append(f'heading level jumps from h{before} to h{after}')
            break
    for n in nodes:
        if re.fullmatch(r'h[1-6]', n.tag) and not n.text() and not hidden(n):
            problems.append(f'{n!r}: empty heading')
    return problems
