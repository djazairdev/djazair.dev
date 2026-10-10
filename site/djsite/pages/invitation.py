"""The invitation to translate (#61): what every address in a language that isn't published
(``config.PUBLISHED``) shows instead of its draft translation.

The build writes it at every page's address in that language, the 404 page and the chart
embeds included, so an unknown address gets it too (Cloudflare serves the nearest 404.html).
It says, in that language first and then in English, that the site isn't translated yet,
links to the issue that lists the work, and links to the same page in English. It keeps the
site's header and footer, carries ``noindex`` and stays out of the sitemap.

Its strings are ``invite.*`` in both catalogs, read in each language whatever the page's.
"""
from __future__ import annotations

from ..components import btn, page_head, section
from ..config import ISSUES_URL
from ..context import Ctx, Page
from ..markup import Markup, join

ISSUE = 62          # Translate djazair.dev into Arabic: the pages and how to help


def addresses(site) -> list:
    """(path under /<lang>/, route, English address) of every page and chart embed."""
    out = [(r.path, r, f'/en/{r.path}' if r.switchable else '/en/') for r in site.routes.values()]
    for path in sorted(site.files):
        if path.startswith('/en/embed/') and path.endswith('/index.html'):
            chart = path.split('/')[3]
            route = site.routes.get(site.charts.get(chart, {}).get('route'), site.routes['home'])
            out.append((path.removeprefix('/en/'), route, path.removesuffix('index.html')))
    return out


def block(ctx: Ctx, english: str, first: bool) -> Markup:
    """The invitation in ``ctx.lang``: the page's heading in its own language, a section in English."""
    link = Markup(f'<a class="lnk" href="{ISSUES_URL}/{ISSUE}" dir="ltr">#{ISSUE}</a>')
    actions = [btn(ctx.t('invite.issue'), f'{ISSUES_URL}/{ISSUE}', out=True),
               btn(ctx.t('invite.english'), english, 'secondary', arrow=False, attrs=' hreflang="en"')]
    lede = Markup(f'{ctx.t("invite.text")} {ctx.t("invite.help", issue=link)}')
    if first:
        return page_head(eyebrow_text=ctx.t('invite.eyebrow'), title=ctx.t('invite.title'), lede=lede, actions=actions)
    return Markup(f'<div lang="{ctx.lang}" dir="{ctx.dir}">'
                  + section('invite-en', ctx.t('invite.eyebrow'), ctx.t('invite.title'),
                            Markup(f'<div class="page-actions">{join(actions)}</div>'), lede=lede, size='s')
                  + '</div>')


def render(ctx: Ctx, english: str) -> Page:
    """``english``: the same page's address in English."""
    en = Ctx(ctx.site, 'en', ctx.route)
    body = block(ctx, english, True) + block(en, english, False)
    return Page(title=ctx.s('invite.title'), description=ctx.s('invite.text'), body=Markup(body),
                full_title=f'{ctx.s("invite.title")} · {en.s("invite.title")}', indexed=False, style='invitation')
