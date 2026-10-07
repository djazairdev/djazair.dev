"""404 page, one per language (Cloudflare serves the nearest 404.html: wrangler.jsonc)."""
from __future__ import annotations

from ..components import btn, page_head
from ..context import Ctx, Page


def render(ctx: Ctx) -> Page:
    actions = [btn(ctx.t('pages.notfound.home'), ctx.url('home')),
               btn(ctx.t('pages.notfound.index'), ctx.url('overview'), 'secondary', arrow=False)]
    body = page_head(eyebrow_text='404', title=ctx.t('pages.notfound.title'),
                     lede=ctx.t('pages.notfound.lede'), actions=actions)
    return Page(title=ctx.s('pages.notfound.title'), description=ctx.s('pages.notfound.lede'), body=body)
