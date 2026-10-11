"""Local static preview with an in-memory action counter; binds only to loopback.

python3 site/tools/preview_actions.py --port 4322
GET /_review/events shows aggregate counts. Nothing is sent to Cloudflare or saved to disk.
"""
import argparse
from collections import Counter
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from threading import Lock
from urllib.parse import urlsplit

EVENTS = {'landing_view', 'hub_view', 'meetups_view', 'task_browse', 'task_open', 'meetup_find',
          'meetup_host', 'share_open', 'share_complete', 'share_copy'}
KEYS = ('event', 'page', 'language', 'section', 'source', 'medium', 'campaign')
SECTIONS = {'hero', 'contribution-start', 'local-team', 'hub-teaser', 'other'}


def valid_event(body):
    return (isinstance(body, dict) and set(body) == set(KEYS)
            and all(isinstance(body[k], str) for k in KEYS)
            and body['event'] in EVENTS and body['page'] in {'home', 'hub', 'meetups'}
            and body['language'] in {'en', 'ar'} and body['section'] in SECTIONS
            and all(re.fullmatch(r'[a-z0-9_-]{1,64}', body[k]) for k in ('source', 'medium', 'campaign')))


class Preview(SimpleHTTPRequestHandler):
    counts = Counter()
    lock = Lock()

    def log_message(self, *args):
        pass  # Campaign query strings and request headers are never logged.

    def do_GET(self):
        if urlsplit(self.path).path == '/_review/events':
            with self.lock:
                rows = [dict(zip(KEYS, key), count=count) for key, count in sorted(self.counts.items())]
            data = json.dumps(rows).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)
        elif urlsplit(self.path).path == '/api/events':
            self.send_error(405)
        else:
            super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != '/api/events':
            self.send_error(404)
            return
        origin = f'http://127.0.0.1:{self.server.server_port}'
        status = 204
        if self.headers.get('Origin') != origin:
            status = 403
        elif self.headers.get('DNT') == '1' or self.headers.get('Sec-GPC') == '1':
            pass
        elif self.headers.get('Content-Type') != 'application/json':
            status = 415
        else:
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 1024:
                    status = 413
                else:
                    body = json.loads(self.rfile.read(length))
                    if not valid_event(body):
                        status = 400
                    else:
                        with self.lock:
                            self.counts[tuple(body[k] for k in KEYS)] += 1
            except (ValueError, UnicodeDecodeError):
                status = 400
        self.send_response(status)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4322)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Preview, directory=str(args.directory)))
    print(f'Local preview: http://127.0.0.1:{args.port}/en/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
