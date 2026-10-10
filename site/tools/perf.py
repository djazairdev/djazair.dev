"""Lab performance check (ticket #30).

Loads pages in Chrome the way Lighthouse's mobile preset does (a Moto G Power screen, a CPU
four times slower, slow 4G) and reports Largest Contentful Paint, First Contentful Paint and
the bytes transferred, fonts apart. Exits 1 when a page is over 300 KB or the Overview's LCP
is over 2.5 s (PRD §11); slower LCPs elsewhere are reported.

    python3 site/tools/perf.py                        # Home, Overview, Trends and Hub, both languages
    python3 site/tools/perf.py /en/index/ --runs 5    # one page, median of five cold loads

It serves site/dist itself, gzipped like the live site, and drives the installed Chrome over
the DevTools protocol, with the standard library only. Set CHROME to Chrome's path if it isn't
found. The numbers are a lab estimate: a real phone on a real network will differ.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import shutil
import socket
import socketserver
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

DIST = Path(__file__).resolve().parent.parent / 'dist'
PAGES = ['/en/', '/en/index/', '/en/index/trends/', '/en/hub/', '/ar/', '/ar/index/', '/ar/index/trends/', '/ar/hub/']
LCP_BUDGET_MS = 2500           # PRD §11: fails for the Overview, a warning for other pages
LCP_BUDGET_PAGES = ('/en/index/', '/ar/index/')
BYTES_BUDGET = 300 * 1024      # compressed, per page, fonts apart (tests/test_performance.py too)

# Lighthouse's mobile preset (constants.js): Moto G Power, slow 4G as DevTools applies it.
SCREEN = {'width': 412, 'height': 823, 'deviceScaleFactor': 1.75, 'mobile': True}
NETWORK = {'latency': 150 * 3.75, 'downloadThroughput': 1.6 * 1024 * 1024 * 0.9 / 8,
           'uploadThroughput': 750 * 1024 * 0.9 / 8}
CPU_SLOWDOWN = 4

WATCH = """
window.__perf = { lcp: 0, element: '' };
new PerformanceObserver(function (list) {
  list.getEntries().forEach(function (e) {
    window.__perf.lcp = e.startTime;
    var el = e.element;
    window.__perf.element = el ? el.tagName.toLowerCase() + (el.className && el.className.baseVal === undefined
      ? '.' + String(el.className).trim().split(/\\s+/).join('.') : '') : e.url;
  });
}).observe({ type: 'largest-contentful-paint', buffered: true });
"""
READ = """JSON.stringify({ lcp: window.__perf.lcp, element: window.__perf.element,
  fcp: (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime || 0 })"""

CHROMES = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', 'google-chrome', 'google-chrome-stable',
           'chromium', 'chromium-browser']
GZIP = ('text/', 'application/javascript', 'application/json', 'image/svg+xml')


# ---------------------------------------------------------------- the site, gzipped
TYPES = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
         '.csv': 'text/csv', '.md': 'text/markdown', '.txt': 'text/plain', '.xml': 'application/xml',
         '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2', '.zip': 'application/zip'}


class Handler(SimpleHTTPRequestHandler):
    """site/dist with gzip and no caching, so every load is cold, as on a first visit."""

    def do_GET(self):
        # Only files under the folder: the address is resolved, and anything outside gets the 404.
        root = os.path.realpath(self.directory)
        found = os.path.realpath(os.path.join(root, unquote(urlparse(self.path).path).lstrip('/')))
        inside = found == root or found.startswith(root + os.sep)
        path = Path(found) if inside else Path(root) / '.outside'
        if path.is_dir():
            path = path / 'index.html'
        status = 200
        if not path.is_file():
            path, status = Path(root) / '404.html', 404
            if not path.is_file():
                self.send_error(404)
                return
        body = path.read_bytes()
        kind = TYPES.get(path.suffix.lower(), 'application/octet-stream')   # from the table, never the address
        self.send_response(status)
        self.send_header('Content-Type', kind + ('; charset=utf-8' if kind.startswith('text/') else ''))
        if kind.startswith(GZIP) and 'gzip' in self.headers.get('Accept-Encoding', ''):
            body = gzip.compress(body, 6)
            self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64        # site/tools/smoke.py makes several requests at once

    def server_bind(self):
        # HTTPServer.server_bind looks up the host's name, which can take half a minute offline.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def serve(root: Path) -> Server:
    """Serve ``root`` on a free local port, in the background; ``shutdown()`` stops it."""
    server = Server(('127.0.0.1', 0), partial(Handler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---------------------------------------------------------------- a small WebSocket client
class WebSocket:
    def __init__(self, url: str, timeout: float = 60):
        u = urlparse(url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n'
                           f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        self.file = self.sock.makefile('rb')
        status = self.file.readline()
        if b' 101 ' not in status:
            raise ConnectionError(f'DevTools refused the connection: {status!r}')
        while self.file.readline() not in (b'\r\n', b''):
            pass

    def send(self, text: str, opcode: int = 1):
        data = text.encode() if isinstance(text, str) else text
        n = len(data)
        head = bytes([0x80 | opcode])
        head += bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + n.to_bytes(2, 'big') if n < 65536 \
            else bytes([0x80 | 127]) + n.to_bytes(8, 'big')
        mask = os.urandom(4)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _exactly(self, n: int) -> bytes:
        data = self.file.read(n)
        if len(data) < n:
            raise ConnectionError('DevTools closed the connection')
        return data

    def recv(self) -> str:
        message = b''
        while True:
            b0, b1 = self._exactly(2)
            n = b1 & 0x7F
            if n == 126:
                n = int.from_bytes(self._exactly(2), 'big')
            elif n == 127:
                n = int.from_bytes(self._exactly(8), 'big')
            payload = self._exactly(n)
            opcode = b0 & 0x0F
            if opcode == 8:
                raise ConnectionError('DevTools closed the connection')
            if opcode == 9:                              # ping
                self.send(payload, opcode=10)
                continue
            message += payload
            if b0 & 0x80:
                return message.decode('utf-8')

    def close(self):
        self.sock.close()


# ---------------------------------------------------------------- Chrome over DevTools
class Chrome:
    START = 60          # seconds to wait for the DevTools port: a cold CI runner has taken more than 10
    TRIES = 2

    def __init__(self, binary: str):
        for attempt in range(1, self.TRIES + 1):
            try:
                port, path = self._start(binary)
                break
            except RuntimeError as e:
                if attempt == self.TRIES:
                    raise
                print(f'{e}\nStarting Chrome again.', file=sys.stderr)
        self.ws = WebSocket(f'ws://127.0.0.1:{port}{path}')
        self.n = 0
        self.events: list = []

    def _start(self, binary: str) -> tuple:
        """Start Chrome with a fresh profile and return its DevTools port and path."""
        self.profile = tempfile.mkdtemp(prefix='djazair-perf-')
        flags = ['--headless=new', '--remote-debugging-port=0', f'--user-data-dir={self.profile}', '--no-first-run',
                 '--no-default-browser-check', '--disable-extensions', '--disable-background-networking',
                 '--disable-component-update', '--disable-sync', '--mute-audio', '--hide-scrollbars', '--use-mock-keychain']
        flags += os.environ.get('CHROME_FLAGS', '').split()
        log = tempfile.TemporaryFile()
        self.process = subprocess.Popen([binary, *flags, 'about:blank'], stdout=subprocess.DEVNULL, stderr=log)
        port_file = Path(self.profile) / 'DevToolsActivePort'
        end = time.monotonic() + self.START
        while not (port_file.exists() and len(port_file.read_text().split()) == 2):
            if self.process.poll() is not None or time.monotonic() > end:
                problem = (f'Chrome exited with code {self.process.returncode}; try CHROME_FLAGS=--no-sandbox'
                           if self.process.poll() is not None else f'Chrome did not open its DevTools port in {self.START} s')
                self.process.kill()
                self.process.wait()
                shutil.rmtree(self.profile, ignore_errors=True)
                log.seek(0)
                tail = log.read().decode('utf-8', 'replace').strip().splitlines()[-5:]
                log.close()
                raise RuntimeError(problem + ''.join(f'\n  chrome: {line}' for line in tail))
            time.sleep(0.05)
        log.close()
        return port_file.read_text().split()

    def call(self, method: str, session: str = None, **params) -> dict:
        self.n += 1
        message = {'id': self.n, 'method': method, 'params': params}
        if session:
            message['sessionId'] = session
        self.ws.send(json.dumps(message))
        while True:
            reply = json.loads(self.ws.recv())
            if reply.get('id') == self.n:
                if 'error' in reply:
                    raise RuntimeError(f'{method}: {reply["error"].get("message")}')
                return reply.get('result', {})
            self.events.append(reply)

    def wait(self, method: str, session: str, timeout: float = 60) -> dict:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            for i, e in enumerate(self.events):
                if e.get('method') == method and e.get('sessionId') == session:
                    return self.events.pop(i)
            self.events.append(json.loads(self.ws.recv()))
        raise TimeoutError(f'no {method} within {timeout} s')

    def close(self):
        try:
            self.call('Browser.close')
        except (ConnectionError, OSError, RuntimeError):
            pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.ws.close()
        shutil.rmtree(self.profile, ignore_errors=True)


def find_chrome() -> str:
    for candidate in [os.environ.get('CHROME', ''), *CHROMES]:
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return shutil.which(candidate) or candidate
    raise SystemExit('Chrome not found: set CHROME to its path.')


def load(chrome: Chrome, url: str, settle: float, cpu: float = CPU_SLOWDOWN) -> dict:
    """One cold load of ``url`` in a fresh browser context, throttled like a mid-range phone."""
    context = chrome.call('Target.createBrowserContext')['browserContextId']
    target = chrome.call('Target.createTarget', url='about:blank', browserContextId=context)['targetId']
    session = chrome.call('Target.attachToTarget', targetId=target, flatten=True)['sessionId']
    try:
        for method, params in (('Page.enable', {}), ('Network.enable', {}),
                               ('Network.setCacheDisabled', {'cacheDisabled': True}),
                               ('Emulation.setDeviceMetricsOverride', SCREEN),
                               ('Emulation.setCPUThrottlingRate', {'rate': cpu}),
                               ('Page.addScriptToEvaluateOnNewDocument', {'source': WATCH})):
            chrome.call(method, session, **params)
        try:
            chrome.call('Network.emulateNetworkConditions', session, offline=False, **NETWORK)
        except RuntimeError:          # newer Chrome: the same throttling, as a rule for every URL
            chrome.call('Network.emulateNetworkConditionsByRule', session, offline=False,
                        matchedNetworkConditions=[{'urlPattern': '', **NETWORK}])
        chrome.events.clear()
        chrome.call('Page.navigate', session, url=url)
        chrome.wait('Page.loadEventFired', session)
        time.sleep(settle)            # late paints (animations) can still change the LCP element
        result = json.loads(chrome.call('Runtime.evaluate', session, expression=READ, returnByValue=True)['result']['value'])
        kinds = {e['params']['requestId']: e['params']['response'].get('mimeType', '') for e in chrome.events
                 if e.get('method') == 'Network.responseReceived' and e.get('sessionId') == session}
        sizes = [(kinds.get(e['params']['requestId'], ''), e['params']['encodedDataLength']) for e in chrome.events
                 if e.get('method') == 'Network.loadingFinished' and e.get('sessionId') == session]
        result['bytes'] = sum(n for kind, n in sizes if 'font' not in kind)
        result['fonts'] = sum(n for kind, n in sizes if 'font' in kind)
        result['requests'] = len(sizes)
        return result
    finally:
        chrome.call('Target.closeTarget', targetId=target)
        chrome.call('Target.disposeBrowserContext', browserContextId=context)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('pages', nargs='*', default=PAGES, help='paths to load (default: %(default)s)')
    parser.add_argument('--runs', type=int, default=3, help='cold loads per page; the median is reported')
    parser.add_argument('--settle', type=float, default=3.0, help='seconds to wait after the load event')
    parser.add_argument('--cpu', type=float, default=CPU_SLOWDOWN, help='CPU slowdown (default: %(default)s, as Lighthouse)')
    parser.add_argument('--dist', type=Path, default=DIST, help='the built site (default: site/dist)')
    parser.add_argument('--json', type=Path, help='also write the results to this file')
    args = parser.parse_args(argv)
    if not (args.dist / 'index.html').exists():
        raise SystemExit(f'{args.dist} has no site: run python3 site/build.py first.')

    server = serve(args.dist)
    origin = f'http://127.0.0.1:{server.server_address[1]}'
    chrome = Chrome(find_chrome())
    rows = []
    try:
        for page in args.pages:
            runs = [load(chrome, origin + page, args.settle, args.cpu) for _ in range(args.runs)]
            rows.append({'page': page, 'lcp': statistics.median(r['lcp'] for r in runs),
                         'fcp': statistics.median(r['fcp'] for r in runs), 'bytes': runs[0]['bytes'],
                         'fonts': runs[0]['fonts'], 'requests': runs[0]['requests'], 'element': runs[-1]['element'],
                         'runs': [round(r['lcp']) for r in runs]})
    finally:
        chrome.close()
        server.shutdown()
        server.server_close()

    failed = False
    setting = (f'Chrome, {SCREEN["width"]} px phone screen, CPU {args.cpu:g}x slower, slow 4G '
               f'({NETWORK["latency"]:.0f} ms, {NETWORK["downloadThroughput"] * 8 / 1e6:.2f} Mbit/s); median of {args.runs} cold loads.')
    lines = [setting, f'{"page":22} {"LCP":>8} {"FCP":>8} {"bytes":>9} {"fonts":>8}  LCP element']
    for r in rows:
        notes = []
        if r['bytes'] > BYTES_BUDGET:
            notes.append(f'over {BYTES_BUDGET // 1024} KB')
        if r['lcp'] > LCP_BUDGET_MS:
            notes.append(f'LCP over {LCP_BUDGET_MS / 1000:g} s')
        failed |= r['bytes'] > BYTES_BUDGET or (r['lcp'] > LCP_BUDGET_MS and r['page'] in LCP_BUDGET_PAGES)
        r['notes'] = notes
        lines.append(f'{r["page"]:22} {r["lcp"] / 1000:7.2f}s {r["fcp"] / 1000:7.2f}s {r["bytes"] / 1024:7.1f}KB '
                     f'{r["fonts"] / 1024:6.1f}KB  {r["element"]}' + (f'  ({", ".join(notes)})' if notes else ''))
    lines.append(f'Budgets: {BYTES_BUDGET // 1024} KB per page without fonts; LCP {LCP_BUDGET_MS / 1000:g} s, '
                 f'required for {" and ".join(LCP_BUDGET_PAGES)}.')
    print('\n'.join(lines))
    if os.environ.get('GITHUB_ACTIONS'):
        for r in rows:
            if r['notes']:
                level = 'error' if r['bytes'] > BYTES_BUDGET or r['page'] in LCP_BUDGET_PAGES else 'warning'
                print(f'::{level}::{r["page"]}: {", ".join(r["notes"])} (LCP {r["lcp"] / 1000:.2f} s)')
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
                summary.write('### Load times (lab)\n\n```\n' + '\n'.join(lines) + '\n```\n')
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2) + '\n', 'utf-8')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
