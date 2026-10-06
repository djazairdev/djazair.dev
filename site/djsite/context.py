"""Routes, the build-wide ``Site`` and the per-page ``Ctx``."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .config import DIRS, SITE_URL
from .i18n import Catalog, fill
from .markup import Markup


@dataclass(frozen=True)
class Route:
    key: str                       # 'trends'
    path: str                      # under /<lang>/: '' for home, 'index/trends/'
    render: Callable               # (ctx) -> Page
    section: Optional[str] = None  # main-nav item this page belongs to
    sub: Optional[str] = None      # Index sub-nav item, if any
    ticket: Optional[int] = None   # GitHub issue that builds the page
    switchable: bool = True        # the language switcher keeps the reader on this page
    indexed: bool = True           # canonical and hreflang links; False adds noindex


@dataclass
class Page:
    """What a page renderer returns; the layout wraps it."""
    title: str                     # plain text, without the site name
    description: str               # plain text
    body: Markup
    scripts: tuple = ()            # extra script URLs, loaded with defer
    full_title: Optional[str] = None  # overrides "title · djazair.dev"
    head: Markup = Markup('')


@dataclass
class Site:
    catalog: Catalog
    routes: dict                   # key -> Route
    assets: object = None          # assets.Assets
    dev: bool = False
    data: dict = field(default_factory=dict)


class Ctx:
    """Everything a renderer needs for one page in one language."""

    def __init__(self, site: Site, lang: str, route: Route):
        self.site = site
        self.lang = lang
        self.dir = DIRS[lang]
        self.route = route
        self.fallbacks: set = set()

    @property
    def en(self) -> bool:
        return self.lang == 'en'

    # ---- links
    def url(self, key: str, lang: Optional[str] = None, hash: str = '') -> str:
        """Root-relative URL of a route: ``/en/index/trends/``."""
        path = f'/{lang or self.lang}/{self.site.routes[key].path}'
        return path + (f'#{hash}' if hash else '')

    def abs_url(self, key: str, lang: Optional[str] = None) -> str:
        return SITE_URL + self.url(key, lang)

    def has(self, key: str) -> bool:
        return key in self.site.routes

    # ---- strings
    def t(self, key: str, **values) -> Markup:
        """String for element content. English fallbacks are wrapped and counted."""
        value, fallback = self.site.catalog.lookup(self.lang, key)
        text = fill(value, values)
        if fallback:
            self.fallbacks.add(key)
            return Markup(f'<span lang="en" dir="ltr" class="untranslated">{text}</span>')
        return text

    def ta(self, key: str, **values) -> Markup:
        """String for an attribute value (no wrapper)."""
        value, fallback = self.site.catalog.lookup(self.lang, key)
        if fallback:
            self.fallbacks.add(key)
        return fill(value, values)

    def s(self, key: str) -> str:
        """Raw, unescaped string (for titles, JSON and measurements)."""
        value, fallback = self.site.catalog.lookup(self.lang, key)
        if fallback:
            self.fallbacks.add(key)
        return value

    def tl(self, key: str) -> list:
        """A list of strings (escaped)."""
        value, fallback = self.site.catalog.lookup(self.lang, key)
        if fallback:
            self.fallbacks.add(key)
        return [fill(v, {}) for v in value]
