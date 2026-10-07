"""Pictures of the built pages for docs/design (ticket #17). Each page gets a full-page
picture and a picture of its first screen, at desktop width (1440 px) and phone width
(390 px):

    python3 site/build.py
    python3 site/tools/screens.py                  # every page in PAGES
    python3 site/tools/screens.py peers-en 404     # some of them

This writes docs/design/<name>-desktop.png, <name>-desktop-top.png, <name>-phone.png and
<name>-phone-top.png. The Hub shows whatever is in data/derived/hub. To use the live
snapshot, run .github/scripts/hub-snapshot.sh first, as CI does.

Full pages are taken at 1x, which keeps the repository small. The first screens are 1x on
desktop and 2x on phones, sharp enough for the previews in GitHub issues. Motion is off
(reduced motion), so every element is drawn in its final place. Uses only the standard
library and the installed Chrome, like perf.py.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import perf  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / 'docs' / 'design'
PAGES = {                      # name in docs/design: address in the built site
    'peers-en': '/en/index/peers/',
    'languages-en': '/en/index/languages/',
    'data-en': '/en/data/',
    'about-en': '/en/about/',
    'reports-en': '/en/reports/',
    'report-en': '/en/reports/2026-q1/',
    'trends-ar': '/ar/index/trends/',
    'hub-ar': '/ar/hub/',
    'methodology-ar': '/ar/methodology/',
    '404': '/404.html',
}
SIZES = {'desktop': (1440, 900, 1), 'phone': (390, 844, 2)}    # width, first screen, its scale


def capture(chrome: perf.Chrome, url: str, width: int, screen: int, scale: float) -> tuple:
    """The full page at 1x and the first screen at ``scale``, as PNG, and the page's height.

    The full page is taken with the window as tall as the page, not with Chrome's "capture
    beyond the viewport", which shifts right-to-left pages sideways."""
    context = chrome.call('Target.createBrowserContext')['browserContextId']
    target = chrome.call('Target.createTarget', url='about:blank', browserContextId=context)['targetId']
    session = chrome.call('Target.attachToTarget', targetId=target, flatten=True)['sessionId']

    def window(height: int, dpr: float):
        chrome.call('Emulation.setDeviceMetricsOverride', session, width=width, height=height,
                    deviceScaleFactor=dpr, mobile=width < 800)
        chrome.call('Runtime.evaluate', session, awaitPromise=True,
                    expression='document.fonts.ready.then(() => new Promise(r => setTimeout(r, 300)))')

    def shot(height: int) -> bytes:
        data = chrome.call('Page.captureScreenshot', session, format='png',
                           clip={'x': 0, 'y': 0, 'width': width, 'height': height, 'scale': 1})
        return base64.b64decode(data['data'])

    try:
        chrome.call('Page.enable', session)
        chrome.call('Emulation.setEmulatedMedia', session, features=[{'name': 'prefers-reduced-motion', 'value': 'reduce'}])
        chrome.call('Emulation.setDeviceMetricsOverride', session, width=width, height=screen,
                    deviceScaleFactor=scale, mobile=width < 800)
        chrome.call('Page.navigate', session, url=url)
        chrome.wait('Page.loadEventFired', session)
        window(screen, scale)
        top = shot(screen)
        height = chrome.call('Runtime.evaluate', session, returnByValue=True,
                             expression='document.documentElement.scrollHeight')['result']['value']
        window(height, 1)
        return shot(height), top, height
    finally:
        chrome.call('Target.closeTarget', targetId=target)
        chrome.call('Target.disposeBrowserContext', browserContextId=context)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('names', nargs='*', help=f'pages to take (default: all of {", ".join(PAGES)})')
    parser.add_argument('--out', type=Path, default=OUT, help='folder to write to (default: docs/design)')
    parser.add_argument('--dist', type=Path, default=perf.DIST, help='the built site (default: site/dist)')
    args = parser.parse_args(argv)
    unknown = set(args.names) - set(PAGES)
    if unknown:
        raise SystemExit(f'unknown page: {", ".join(sorted(unknown))}; pages: {", ".join(PAGES)}')
    if not (args.dist / 'index.html').exists():
        raise SystemExit(f'{args.dist} has no site: run python3 site/build.py first.')
    args.out.mkdir(parents=True, exist_ok=True)
    server = perf.serve(args.dist)
    origin = f'http://127.0.0.1:{server.server_address[1]}'
    chrome = perf.Chrome(perf.find_chrome())
    try:
        for name in args.names or PAGES:
            for size, (width, screen, scale) in SIZES.items():
                full, top, height = capture(chrome, origin + PAGES[name], width, screen, scale)
                (args.out / f'{name}-{size}.png').write_bytes(full)
                (args.out / f'{name}-{size}-top.png').write_bytes(top)
                print(f'{name}-{size}: {width} × {height} px', flush=True)
    finally:
        chrome.close()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
