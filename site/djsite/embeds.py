"""Embeddable charts (ticket #42, PRD IDX-18).

Every chart on the Index pages and Home gets a page of its own, /<lang>/embed/<chart id>/,
made to sit in an iframe on another site. It shows the chart as the site draws it (the phone
drawing in a narrow frame), a key where the drawing needs one, and the source and licence with
a link back to the chart. It is dark like the site; /<lang>/embed/<chart id>/light/ is the same
page in the light palette of the downloads. Both are static, with no script. They always show
the latest release, search engines are asked not to index them, and _headers lets any site
frame these pages and no others.

Under each of those charts, *Share* opens the phone's share sheet or copies a link to the
chart, and *Embed* shows the iframe code to copy. Reports keep their downloads only.
"""
from __future__ import annotations

from . import charts
from .charts import SANS, BarChart, HBarChart, LineChart, _num, legend_items, loc
from .config import SITE_URL, STATIC_DIR
from .icons import icon
from .markup import Markup, esc, join
from .palette import THEMES

WIDTH = 720                       # the column the suggested iframe height is worked out for
CHROME = 150                      # title, key, credit and padding around the drawing, in pixels
KEY_ORDER = ('dz', 'hl', 'median', 'ref', 'peer')
LIGHT_PARAM = Markup('<code dir="ltr">light/</code>')


def embeddable(ctx, chart) -> bool:
    """Charts with a title on the Index pages and Home (Home's unit picture has none)."""
    return (isinstance(chart, (LineChart, BarChart, HBarChart)) and ctx.route.indexed
            and (ctx.route.section == 'index' or ctx.route.key == 'home'))


def path(lang: str, chart_id: str, theme: str = 'dark') -> str:
    return f'/{lang}/embed/{chart_id}/' + ('' if theme == 'dark' else f'{theme}/')


def height(chart, lang: str) -> int:
    """A height that fits the wide drawing in a column ``WIDTH`` wide; the page fits any other."""
    d = charts.drawing(chart, lang, 'wide')
    return int(round((d.height * WIDTH / d.width + CHROME) / 10) * 10)


def code(ctx, chart) -> str:
    """The iframe to paste, dark; the panel's switch adds light/ to the address."""
    title = f'{loc(chart.title, ctx.lang)} (djazair.dev)'
    return (f'<iframe src="{SITE_URL}{path(ctx.lang, chart.id)}" title="{esc(title)}" width="100%" '
            f'height="{height(chart, ctx.lang)}" style="border: 0; max-width: 960px" loading="lazy"></iframe>')


# ---------------------------------------------------------------- under the chart
def share(ctx, anchor: str) -> Markup:
    """A link to the chart. site.js opens the share sheet where there is one, and otherwise
    copies the link; without JavaScript it is a link to the figure."""
    return Markup(f'<a class="act" href="#{esc(anchor)}" data-share data-copied="{ctx.ta("dl.copied")}">'
                  f'{icon("share", 15)}<span>{ctx.t("dl.share_button")}</span></a>')


def panel(ctx, chart) -> Markup:
    """The Embed disclosure: what the code does, a dark or light switch, the code and a preview."""
    uid = f'emb-{chart.id}'
    themes = join(f'<label><input class="sr-only" type="radio" name="{uid}-t" value="{t}"{" checked" if t == "dark" else ""}>'
                  f'<span>{ctx.t(f"embed.{t}")}</span></label>' for t in ('dark', 'light'))
    return Markup(
        f'<details class="dl emb"><summary class="act">{icon("embed", 15)}{ctx.t("embed.button")}</summary>'
        f'<div class="dl-menu emb-panel" role="group" aria-label="{ctx.ta("embed.button")}">'
        f'<p class="emb-p">{ctx.t("embed.lede")}</p>'
        f'<div class="seg emb-ts" role="radiogroup" aria-label="{ctx.ta("embed.theme")}" hidden>{themes}</div>'
        f'<textarea class="emb-code" id="{uid}" readonly rows="5" dir="ltr" spellcheck="false" '
        f'aria-label="{ctx.ta("embed.code")}">{esc(code(ctx, chart))}</textarea>'
        f'<p class="emb-note">{ctx.t("embed.light_note", param=LIGHT_PARAM)}</p>'
        f'<div class="emb-acts"><button type="button" class="act" data-copy-from="{uid}" data-copied="{ctx.ta("code.copied")}" hidden>'
        f'{ctx.t("embed.copy")}</button><a class="act" href="{path(ctx.lang, chart.id)}" target="_blank" rel="noopener">'
        f'{ctx.t("embed.preview")}</a></div></div></details>')


# ---------------------------------------------------------------- the embed page
def _svg(chart, lang: str, size: str, theme: str) -> str:
    d = charts.drawing(chart, lang, size, THEMES[theme], uid=f'{chart.id}-{size[0]}')
    defs = f'<defs>{d.defs}</defs>' if d.defs else ''
    return (f'<svg class="{size}" viewBox="0 0 {_num(d.width)} {_num(d.height)}" role="img" '
            f'aria-label="{esc(loc(chart.title, lang))}" direction="ltr" font-family="{SANS}">{defs}{d.body}</svg>')


def _key(chart, lang: str, theme: str) -> str:
    """The lines' names (the phone drawing has no end labels), or what the bars' parts mean."""
    pal = THEMES[theme]
    if isinstance(chart, LineChart):
        items = []
        for ln in sorted(chart.lines, key=lambda ln: KEY_ORDER.index(ln.role)):
            if ln.role == 'peer' and chart.peers_label:
                continue
            colour, _, _, dash = charts.LINE_STYLE[ln.role]
            items.append((pal[colour], dash, loc(ln.name, lang)))
        if chart.peers_label and any(ln.role == 'peer' for ln in chart.lines):
            items.append((pal['peer'], None, loc(chart.peers_label, lang)))
        lis = join(f'<li><span class="sw" style="{f"border-top: 2px dashed {c}" if dash else f"background: {c}"}"></span>{esc(t)}</li>'
                   for c, dash, t in items)
        return f'<ul class="key narrow">{lis}</ul>'
    items = legend_items(chart, lang, pal)
    if not items:
        return ''
    lis = join(f'<li><span class="sq" style="background: {c}"></span>{esc(t)}</li>' if kind == 'square' else f'<li>{esc(t)}</li>'
               for kind, c, t in items)
    return f'<ul class="key">{lis}</ul>'


STYLE = """{fonts}
:root {{ color-scheme: {theme}; {tokens} }}
* {{ box-sizing: border-box; margin: 0; }}
html, body, main {{ height: 100%; }}
body {{ background: var(--paper); color: var(--ink); font-family: Tajawal, 'Segoe UI', Arial, sans-serif;
  -webkit-font-smoothing: antialiased; }}
main {{ display: flex; flex-direction: column; gap: 10px; padding: 14px 16px 12px; }}
h1 {{ font-size: 15.5px; line-height: 1.35; font-weight: 700; }}
.fig {{ flex: 1 1 auto; min-height: 120px; display: flex; }}
.fig svg {{ display: block; width: 100%; height: 100%; }}
.key {{ display: flex; flex-wrap: wrap; gap: 4px 16px; padding: 0; list-style: none; font-size: 12.5px; color: var(--ink2); }}
.key li {{ display: inline-flex; align-items: center; gap: 7px; }}
.sw {{ display: inline-block; width: 16px; height: 0; border-top: 3px solid transparent; }}
.sw[style^=background] {{ height: 3px; border: 0; border-radius: 2px; }}
.sq {{ display: inline-block; width: 11px; height: 11px; border-radius: 2px; }}
.credit {{ font-size: 11.5px; line-height: 1.5; color: var(--ink3); }}
.credit a {{ color: var(--ink2); }}
.credit a:hover {{ color: var(--ink); }}
@media (max-width: 559px) {{ .wide {{ display: none !important; }} }}
@media (min-width: 560px) {{ .narrow {{ display: none !important; }} }}
"""


def _tokens(pal: dict) -> str:
    return ' '.join(f'--{k}: {pal[k]};' for k in ('paper', 'ink', 'ink2', 'ink3'))


def register(ctx, chart, source, anchor: str) -> None:
    """Add the chart's embed pages, dark and light, to the build."""
    for theme in THEMES:
        ctx.site.add_file(f'{path(ctx.lang, chart.id, theme)}index.html', page(ctx, chart, source, anchor, theme))


def page(ctx, chart, source, anchor: str, theme: str = 'dark') -> bytes:
    """The page an iframe shows. ``source``: the chart's source line, as on its page."""
    lang = ctx.lang
    fonts = (STATIC_DIR / 'css' / '05-fonts.css').read_text('utf-8')
    fonts = '\n'.join(line for line in fonts.splitlines() if line.startswith('@font-face'))
    style = STYLE.format(fonts=fonts, theme=theme, tokens=_tokens(THEMES[theme]))
    title = esc(loc(chart.title, lang))
    back = f'{ctx.abs_url(ctx.route.key)}#{anchor}'
    figures = ''.join(_svg(chart, lang, size, theme) for size in ('wide', 'narrow'))
    credit = f'{source} · {ctx.t("embed.licence")} · <a href="{esc(back)}">{ctx.t("embed.view")}</a>'
    return f'''<!doctype html>
<html lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} · djazair.dev</title>
<link rel="canonical" href="{esc(back)}">
<base target="_blank">
<style>
{style}</style>
</head>
<body>
<main>
<h1>{title}</h1>
<div class="fig">{figures}</div>
{_key(chart, lang, theme)}
<p class="credit">{credit}</p>
</main>
</body>
</html>
'''.encode('utf-8')
