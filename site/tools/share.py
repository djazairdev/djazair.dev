"""Share images (tickets #31 and #42): 1200 × 630 PNGs, one per language, shown when a page
is shared (Open Graph and X cards). Each is an HTML card with the site's fonts, colours and
emblem, captured in Chrome:

    python3 site/tools/share.py             # the site's card, with the tagline
    python3 site/tools/share.py --release   # the latest quarter's card, with its headline figures

The first writes site/static/share/en.png and ar.png: run it after changing the tagline, the
emblem or the colours. The second writes site/static/share/<quarter>/en.png and ar.png
(2026-q1/en.png …) with the figures at the top of Home and its unit map; the data workflow runs
it for each new release. Home and the Index pages show the card of the quarter they show, or
the site's card while there is none; other pages show the site's card. Commit the images: the
build only copies them. Standard library only; it uses the installed Chrome, like
site/tools/perf.py.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

import perf  # noqa: E402
from djsite import charts  # noqa: E402
from djsite.charts import SANS, _num  # noqa: E402
from djsite.config import I18N_DIR, LANGS, STATIC_DIR  # noqa: E402
from djsite.context import Ctx, Site  # noqa: E402
from djsite.data import DERIVED_DIR, load as load_data  # noqa: E402
from djsite.fmt import has_arabic, quarter_label  # noqa: E402
from djsite.i18n import Catalog  # noqa: E402
from djsite.icons import mark  # noqa: E402
from djsite.markup import esc  # noqa: E402
from djsite.pages import home  # noqa: E402
from djsite.routes import ROUTES  # noqa: E402

OUT = STATIC_DIR / 'share'
WIDTH, HEIGHT = 1200, 630

PAGE = """<!doctype html>
<html lang="{lang}" dir="{dir}">
<head>
<meta charset="utf-8">
<style>
{fonts}
:root {{ {tokens} }}
* {{ margin: 0; box-sizing: border-box; }}
html, body {{ width: {width}px; height: {height}px; overflow: hidden; background: var(--bg); }}
body {{ position: relative; font-family: var(--sans); color: var(--ink); -webkit-font-smoothing: antialiased; }}
.grid {{ position: absolute; inset: 0; background-image: linear-gradient(var(--hero-grid) 1px, transparent 1px),
  linear-gradient(90deg, var(--hero-grid) 1px, transparent 1px); background-size: 48px 48px;
  mask-image: radial-gradient(circle at 76% 50%, #000 0, transparent 70%); }}
.card {{ position: absolute; inset: 0; display: grid; grid-template-columns: 1fr 380px; gap: 56px; align-items: center;
  padding: 72px 80px; }}
.text {{ display: flex; flex-direction: column; gap: 28px; min-width: 0; }}
.eyebrow {{ display: flex; align-items: center; gap: 12px; font-family: var(--mono); font-size: 19px; font-weight: 500;
  letter-spacing: .14em; text-transform: uppercase; color: var(--ink3); }}
.eyebrow::before {{ content: ''; width: 10px; height: 10px; border-radius: 2px; background: var(--mint); }}
[lang=ar] .eyebrow {{ font-family: var(--sans); font-size: 24px; font-weight: 700; letter-spacing: 0; }}
h1 {{ font-size: 68px; line-height: 1.08; font-weight: 800; letter-spacing: -0.025em; text-wrap: balance; }}
[lang=ar] h1 {{ font-size: 64px; line-height: 1.3; letter-spacing: 0; }}
p {{ font-size: 27px; line-height: 1.45; color: var(--ink2); text-wrap: pretty; }}
[lang=ar] p {{ font-size: 27px; line-height: 1.7; }}
.foot {{ display: flex; align-items: center; gap: 14px; margin-top: 8px; }}
.wordmark {{ font-weight: 800; font-size: 30px; letter-spacing: -0.02em; }}
.wordmark span {{ color: var(--mint); }}
.emblem {{ display: grid; place-items: center; }}
.emblem svg {{ filter: drop-shadow(0 0 60px rgba(61, 190, 132, .28)); }}
{extra}</style>
</head>
<body>
<div class="grid"></div>
{body}
</body>
</html>
"""
FOOT = '<div class="foot">{mark}<span class="wordmark" lang="en" dir="ltr">djazair<span>.dev</span></span></div>'

BRAND = """<div class="card">
  <div class="text">
    <div class="eyebrow">{eyebrow}</div>
    <h1>{title}</h1>
    <p>{lede}</p>
    {foot}
  </div>
  <div class="emblem">{big_mark}</div>
</div>"""

# The release card: the quarter, the number of accounts and the three figures under it on
# Home, and Home's unit map, where the bright squares are the accounts added in a year.
RELEASE_STYLE = """.release { grid-template-columns: 1fr 440px; gap: 48px; padding: 64px 72px 64px 80px; }
.release .text { gap: 26px; }
.release h1 { display: flex; flex-direction: column; gap: 16px; font-size: inherit; line-height: normal; letter-spacing: 0; }
.n { align-self: flex-start; font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: 112px; line-height: .86;
  font-weight: 600; letter-spacing: -0.055em; white-space: nowrap; }
.n .ts { margin-inline: -.16em; }
.tail { font-size: 36px; line-height: 1.15; font-weight: 700; letter-spacing: -0.015em; }
[lang=ar] .tail { line-height: 1.35; letter-spacing: 0; }
.figs { display: grid; grid-template-columns: auto 1fr; gap: 10px 26px; align-items: baseline; padding-block: 18px;
  border-block: 1px solid var(--line); }
.fig { display: contents; }
.fig b { font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: 28px; line-height: 1.15; font-weight: 600;
  letter-spacing: -0.02em; white-space: nowrap; }
.fig b.nums { font-family: var(--sans); font-weight: 700; letter-spacing: 0; }
[lang=ar] .fig b { text-align: right; }
.fig.up b { color: var(--mint); }
.fig span { font-size: 21px; line-height: 1.3; color: var(--ink3); white-space: nowrap; }
.map svg { display: block; width: 100%; height: auto; }
"""

RELEASE = """<div class="card release">
  <div class="text">
    <div class="eyebrow">{eyebrow}</div>
    <h1><span class="n" lang="en" dir="ltr">{number}</span><span class="tail">{tail}</span></h1>
    <div class="figs">{figs}</div>
    {foot}
  </div>
  <div class="map">{map}</div>
</div>"""


def strings(lang: str) -> dict:
    catalog = json.loads((I18N_DIR / f'{lang}.json').read_text('utf-8'))
    return {'eyebrow': catalog['share']['eyebrow'], 'title': catalog['site']['tagline'], 'lede': catalog['share']['lede']}


def page(lang: str, body: str, extra: str = '', names: str = 'bg|ink|ink2|ink3|mint|hero-grid|sans|mono') -> str:
    css = (STATIC_DIR / 'css' / '00-tokens.css').read_text('utf-8')
    tokens = ' '.join(f'{name}: {value};' for name, value in re.findall(rf'(--(?:{names})):\s*([^;]+);', css))
    fonts = (STATIC_DIR / 'css' / '05-fonts.css').read_text('utf-8')
    return PAGE.format(lang=lang, dir='rtl' if lang == 'ar' else 'ltr', fonts=fonts, tokens=tokens, width=WIDTH,
                       height=HEIGHT, extra=extra, body=body)


def card(lang: str) -> str:
    """The site's card: the tagline and the emblem."""
    body = BRAND.format(foot=FOOT.format(mark=mark(40)), big_mark=mark(340), **{k: v for k, v in strings(lang).items()})
    return page(lang, body)


def release_context(lang: str, derived_dir: Path = DERIVED_DIR) -> Ctx:
    """Home's context for the latest quarter, to say the figures as Home does."""
    site = Site(catalog=Catalog(I18N_DIR), routes={r.key: r for r in ROUTES}, data=load_data(derived_dir))
    return Ctx(site, lang, site.routes['home'])


def figure(text: str) -> str:
    """As fmt.num: figures left to right in mono; '3 من 7' right to left in the sans face."""
    return f'<b class="nums" dir="rtl">{esc(text)}</b>' if has_arabic(text) else f'<b dir="ltr">{esc(text)}</b>'


def release_card(ctx: Ctx) -> str:
    """The latest quarter's card, from the derived data: as the top of Home."""
    data, lang = ctx.site.data, ctx.lang
    accounts = int(data.overview()['accounts']['value'])
    number = f'<span class="ts">{home.GROUP[lang]}</span>'.join(home._groups(accounts))
    figs = ''.join(f'<div class="fig{" up" if i == 0 else ""}">{figure(("▲ " if i == 0 else "") + value)}<span>{label}</span></div>'
                   for i, (value, label) in enumerate(home.figures(ctx)))
    d = charts.drawing(home.units_chart(ctx), lang, 'wide', charts.DARK, uid='share')
    defs = f'<defs>{d.defs}</defs>' if d.defs else ''
    unit_map = (f'<svg viewBox="0 0 {_num(d.width)} {_num(d.height)}" direction="ltr" font-family="{SANS}" '
                f'aria-hidden="true">{defs}{d.body}</svg>')
    body = RELEASE.format(eyebrow=ctx.t('home.eyebrow', quarter=quarter_label(data.quarter, lang)), number=number,
                          tail=ctx.t('home.h1_tail'), figs=figs, foot=FOOT.format(mark=mark(40)), map=unit_map)
    return page(lang, body, RELEASE_STYLE, names='bg|ink|ink2|ink3|mint|hero-grid|line|sans|mono')


def capture(chrome: perf.Chrome, url: str) -> bytes:
    context = chrome.call('Target.createBrowserContext')['browserContextId']
    target = chrome.call('Target.createTarget', url='about:blank', browserContextId=context)['targetId']
    session = chrome.call('Target.attachToTarget', targetId=target, flatten=True)['sessionId']
    try:
        chrome.call('Page.enable', session)
        chrome.call('Emulation.setDeviceMetricsOverride', session, width=WIDTH, height=HEIGHT, deviceScaleFactor=1, mobile=False)
        chrome.call('Page.navigate', session, url=url)
        chrome.wait('Page.loadEventFired', session)
        chrome.call('Runtime.evaluate', session, expression='document.fonts.ready.then(() => document.fonts.size)', awaitPromise=True)
        shot = chrome.call('Page.captureScreenshot', session, format='png',
                           clip={'x': 0, 'y': 0, 'width': WIDTH, 'height': HEIGHT, 'scale': 1})
        return base64.b64decode(shot['data'])
    finally:
        chrome.call('Target.closeTarget', targetId=target)
        chrome.call('Target.disposeBrowserContext', browserContextId=context)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--release', action='store_true', help="draw the latest quarter's card instead of the site's")
    parser.add_argument('--html', action='store_true', help='write the cards as HTML next to the images, to look at them')
    args = parser.parse_args(argv)
    if args.release:
        contexts = {lang: release_context(lang) for lang in LANGS}
        out = OUT / contexts['en'].site.data.folder.name
        cards = {lang: release_card(ctx) for lang, ctx in contexts.items()}
    else:
        out, cards = OUT, {lang: card(lang) for lang in LANGS}
    tmp = Path(tempfile.mkdtemp(prefix='djazair-share-'))
    shutil.copytree(STATIC_DIR / 'fonts', tmp / 'assets' / 'fonts')     # the card's @font-face URLs
    for lang, html in cards.items():
        (tmp / f'{lang}.html').write_text(html, 'utf-8')
    server = perf.serve(tmp)
    chrome = perf.Chrome(perf.find_chrome())
    try:
        out.mkdir(parents=True, exist_ok=True)
        for lang in cards:
            png = capture(chrome, f'http://127.0.0.1:{server.server_address[1]}/{lang}.html')
            (out / f'{lang}.png').write_bytes(png)
            if args.html:
                (out / f'{lang}.html').write_text(cards[lang], 'utf-8')
            print(f'{out / f"{lang}.png"}: {len(png) / 1024:.0f} KB')
    finally:
        chrome.close()
        server.shutdown()
        server.server_close()
        shutil.rmtree(tmp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
