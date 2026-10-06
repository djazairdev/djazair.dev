"""Share images (ticket #31): one 1200 × 630 PNG per language, shown when a page is shared
(Open Graph and X cards). Drawn as an HTML card with the site's fonts, colours and emblem, and
captured in Chrome:

    python3 site/tools/share.py

writes site/static/share/en.png and ar.png. Run it after changing the tagline, the emblem or
the colours, and commit the images: the build only copies them. Standard library only; it
uses the installed Chrome, like site/tools/perf.py.
"""
from __future__ import annotations

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
from djsite.config import I18N_DIR, STATIC_DIR  # noqa: E402
from djsite.icons import mark  # noqa: E402

OUT = STATIC_DIR / 'share'
WIDTH, HEIGHT = 1200, 630

CARD = """<!doctype html>
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
</style>
</head>
<body>
<div class="grid"></div>
<div class="card">
  <div class="text">
    <div class="eyebrow">{eyebrow}</div>
    <h1>{title}</h1>
    <p>{lede}</p>
    <div class="foot">{small_mark}<span class="wordmark" lang="en" dir="ltr">djazair<span>.dev</span></span></div>
  </div>
  <div class="emblem">{big_mark}</div>
</div>
</body>
</html>
"""


def strings(lang: str) -> dict:
    catalog = json.loads((I18N_DIR / f'{lang}.json').read_text('utf-8'))
    return {'eyebrow': catalog['share']['eyebrow'], 'title': catalog['site']['tagline'], 'lede': catalog['share']['lede']}


def card(lang: str) -> str:
    css = (STATIC_DIR / 'css' / '00-tokens.css').read_text('utf-8')
    tokens = ' '.join(f'{name}: {value};' for name, value in
                      re.findall(r'(--(?:bg|ink|ink2|ink3|mint|hero-grid|sans|mono)):\s*([^;]+);', css))
    fonts = (STATIC_DIR / 'css' / '05-fonts.css').read_text('utf-8')
    s = strings(lang)
    return CARD.format(lang=lang, dir='rtl' if lang == 'ar' else 'ltr', fonts=fonts, tokens=tokens, width=WIDTH,
                       height=HEIGHT, small_mark=mark(40), big_mark=mark(340), **s)


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


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix='djazair-share-'))
    shutil.copytree(STATIC_DIR / 'fonts', tmp / 'assets' / 'fonts')     # the card's @font-face URLs
    for lang in ('en', 'ar'):
        (tmp / f'{lang}.html').write_text(card(lang), 'utf-8')
    server = perf.serve(tmp)
    chrome = perf.Chrome(perf.find_chrome())
    try:
        OUT.mkdir(exist_ok=True)
        for lang in ('en', 'ar'):
            png = capture(chrome, f'http://127.0.0.1:{server.server_address[1]}/{lang}.html')
            (OUT / f'{lang}.png').write_bytes(png)
            print(f'{OUT / f"{lang}.png"}: {len(png) / 1024:.0f} KB')
    finally:
        chrome.close()
        server.shutdown()
        server.server_close()
        shutil.rmtree(tmp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
