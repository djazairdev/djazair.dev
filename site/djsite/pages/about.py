"""About (ticket #23): mission, who runs the project, licences, contact and partners, in the
Methodology layout. The words live in ``content/about/<lang>.md``."""
from __future__ import annotations

from .. import components as C
from ..context import Ctx, Page
from ..markup import Markup
from .methodology import document, toc


def render(ctx: Ctx) -> Page:
    secs, body = document(ctx, 'about')
    head = C.page_head(eyebrow_text=ctx.t('about.eyebrow'), title=ctx.t('about.title'), lede=ctx.t('about.lede'))
    page = Markup(f'{head}<div class="container doc">{toc(ctx, secs)}<div class="doc-main">{body}</div></div>')
    return Page(title=ctx.s('pages.about.title'), description=ctx.s('pages.about.description'), body=page)
