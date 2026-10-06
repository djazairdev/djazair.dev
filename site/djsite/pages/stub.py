"""Placeholder for a page whose ticket isn't done yet: the shell plus a link to the ticket."""
from __future__ import annotations

from ..components import page_head
from ..config import ISSUES_URL
from ..context import Ctx, Page
from ..markup import Markup


def render(ctx: Ctx) -> Page:
    key = ctx.route.key
    n = ctx.route.ticket
    link = Markup(f'<a class="lnk" href="{ISSUES_URL}/{n}" dir="ltr">#{n}</a>')
    body = page_head(eyebrow_text=ctx.t('stub.eyebrow'), title=ctx.t(f'pages.{key}.title'),
                     lede=ctx.t('stub.lede', issue=link))
    return Page(title=ctx.s(f'pages.{key}.title'), description=ctx.s(f'pages.{key}.description'), body=body,
                indexed=False)
