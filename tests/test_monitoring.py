"""Monitoring and alerts (ticket #32): one open issue per failing scheduled workflow, updated
instead of duplicated and closed when the next run works; the uptime check; the forced
failure that tests each alert; analytics without cookies."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(ROOT / 'site' / 'tools'))

import perf  # noqa: E402
from djsite.build import analytics_token, build  # noqa: E402

WORKFLOWS = ROOT / '.github' / 'workflows'
SCRIPTS = ROOT / '.github' / 'scripts'
TOKEN = '0123456789abcdef0123456789abcdef'

FAKE_GH = """#!/usr/bin/env bash
printf 'gh' >> "$SIM/gh.log"; printf ' [%s]' "$@" >> "$SIM/gh.log"; echo >> "$SIM/gh.log"
case "$1 $2" in
  "issue list") echo "${SIM_ISSUE_EXISTING:-}";;
esac
"""


@unittest.skipUnless(shutil.which('bash') and shutil.which('curl'), 'needs bash and curl')
class Alerts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        bin_ = self.tmp / 'bin'
        bin_.mkdir()
        (bin_ / 'gh').write_text(FAKE_GH)
        (bin_ / 'sleep').write_text('#!/bin/sh\nexit 0\n')
        for f in bin_.iterdir():
            f.chmod(0o755)
        self.runner = self.tmp / 'runner'
        self.runner.mkdir()
        self.env = {**os.environ, 'PATH': f'{bin_}:{os.environ["PATH"]}', 'SIM': str(self.tmp), 'GH_TOKEN': 'x',
                    'GITHUB_SERVER_URL': 'https://github.com', 'GITHUB_REPOSITORY': 'o/r', 'GITHUB_RUN_ID': '42',
                    'RUNNER_TEMP': str(self.runner), 'ALERT_ASSIGNEES': ''}

    def run_script(self, *args, **env):
        return subprocess.run(['bash', str(SCRIPTS / args[0]), *args[1:]], cwd=self.tmp, env={**self.env, **env},
                              capture_output=True, text=True)

    def calls(self) -> list:
        log = self.tmp / 'gh.log'
        return log.read_text().splitlines() if log.exists() else []

    def test_a_first_failure_opens_an_issue_for_the_admins(self):
        (self.runner / 'body.md').write_text('It broke.\n')
        result = self.run_script('alert.sh', 'open', 'Hub sync failed', 'area: hub', str(self.runner / 'body.md'),
                                 ALERT_ASSIGNEES='founder,second-admin')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls()), 2)
        self.assertIn('[issue] [list] [--state] [open] [--search] ["Hub sync failed" in:title]', self.calls()[0])
        self.assertIn('[issue] [create] [--title] [Hub sync failed]', self.calls()[1])
        self.assertIn('[--label] [area: hub] [--assignee] [founder,second-admin]', self.calls()[1])

    def test_a_repeated_failure_comments_instead(self):
        (self.runner / 'body.md').write_text('Still broken.\n')
        result = self.run_script('alert.sh', 'open', 'Site down', 'area: infra', str(self.runner / 'body.md'),
                                 SIM_ISSUE_EXISTING='12')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('[issue] [comment] [12]', self.calls()[1])
        self.assertNotIn('create', ' '.join(self.calls()))

    def test_the_next_run_that_works_closes_it(self):
        result = self.run_script('alert.sh', 'close', 'Site down', 'Back up.', SIM_ISSUE_EXISTING='12')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[1], 'gh [issue] [close] [12] [--comment] [Back up.]')
        self.tmp.joinpath('gh.log').unlink()
        self.run_script('alert.sh', 'close', 'Site down', 'Back up.')
        self.assertEqual(len(self.calls()), 1, 'nothing open, nothing to close')

    def test_hub_failure_report(self):
        (self.runner / 'hub-sync-errors.txt').write_text('Hub sync stopped, nothing was written: GitHub API rate limit\n')
        (self.runner / 'failure-notes.md').write_text('This run failed on purpose.\n')
        result = self.run_script('hub-failed.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        body = (self.runner / 'issue.md').read_text()
        self.assertIn('[run 42](https://github.com/o/r/actions/runs/42)', body)
        self.assertIn('keeps the last snapshot', body)
        self.assertIn('rate limit', body)
        self.assertIn('failed on purpose', body)
        self.assertIn('[Hub sync failed]', self.calls()[1])

    def test_uptime_up_and_down(self):
        site = self.tmp / 'site'
        site.mkdir()
        (site / 'index.html').write_text('<!doctype html><title>djazair.dev</title>')
        (site / '404.html').write_text('<!doctype html><title>not found</title>')
        server = perf.serve(site)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_address[1]}'
        result = self.run_script('uptime.sh', UPTIME_URLS=f'{base}/')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'- {base}/: up', (self.runner / 'uptime.md').read_text())

        result = self.run_script('uptime.sh', UPTIME_URLS=f'{base}/ {base}/gone/ http://127.0.0.1:9/')
        self.assertEqual(result.returncode, 1)
        report = (self.runner / 'uptime.md').read_text()
        self.assertIn(f'- {base}/: up', report)
        self.assertIn(f'- {base}/gone/: **down** (HTTP 404 after 3 tries)', report)
        self.assertIn('- http://127.0.0.1:9/: **down** (HTTP 000 after 3 tries)', report)

        result = self.run_script('uptime-failed.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('**down**', (self.runner / 'issue.md').read_text())
        self.assertIn('[Site down] [--body-file]', self.calls()[1])


class Workflows(unittest.TestCase):
    ALERTS = {'data.yml': ('data-failed.sh', 'Data update failed'), 'hub.yml': ('hub-failed.sh', 'Hub sync failed'),
              'uptime.yml': ('uptime-failed.sh', 'Site down')}

    def test_every_scheduled_workflow_reports_failures_and_closes_them(self):
        scheduled = {p.name for p in WORKFLOWS.glob('*.yml') if re.search(r'^\s+schedule:', p.read_text(), re.M)}
        self.assertEqual(scheduled, set(self.ALERTS))
        for name, (script, title) in self.ALERTS.items():
            text = (WORKFLOWS / name).read_text()
            with self.subTest(workflow=name):
                self.assertIn('issues: write', text)
                report = text.index(f'run: .github/scripts/{script}')
                self.assertIn('if: failure()', text[text.rindex('- name:', 0, report):report])
                self.assertIn('ALERT_ASSIGNEES: ${{ vars.ALERT_ASSIGNEES }}', text[text.rindex('- name:', 0, report):report])
                close = text.index(f".github/scripts/alert.sh close '{title}'")
                self.assertIn('if: success()', text[text.rindex('- name:', 0, close):close])
                self.assertGreater(close, report)

    def test_a_forced_failure_tests_each_alert(self):
        for name in self.ALERTS:
            text = (WORKFLOWS / name).read_text()
            with self.subTest(workflow=name):
                self.assertRegex(text, r'workflow_dispatch:\n    inputs:\n(?:.*\n)*?      fail:\n        description: Fail on purpose')
                step = text.index('- name: Fail on purpose')
                self.assertIn('if: inputs.fail', text[step:step + 120])
                first = min(text.index(s) for s in ('- name: Fetch', '- name: Get the last snapshot', '- name: Check\n')
                            if s in text)
                self.assertLess(step, first, 'it fails before doing anything')

    def test_uptime_every_30_minutes_from_github(self):
        text = (WORKFLOWS / 'uptime.yml').read_text()
        self.assertIn("cron: '7,37 * * * *'", text)
        self.assertIn("UPTIME_URLS: ${{ vars.UPTIME_URLS || 'https://djazair.dev/' }}", text)


class Analytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        build(cls.tmp / 'off', quiet=True, analytics='')
        build(cls.tmp / 'on', quiet=True, analytics=TOKEN)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_no_cookies(self):
        for path in sorted((ROOT / 'site' / 'static' / 'js').glob('*.js')):
            self.assertNotIn('cookie', path.read_text('utf-8').lower(), path.name)
        self.assertNotIn('Set-Cookie', (self.tmp / 'on' / '_headers').read_text())

    def test_the_beacon_only_with_a_token(self):
        beacon = f'<script src="https://static.cloudflareinsights.com/beacon.min.js" defer data-cf-beacon=\'{{"token": "{TOKEN}"}}\'></script>'
        for lang in ('en', 'ar'):
            for page in ('index.html', 'index/trends/index.html', 'hub/index.html', '404.html'):
                with self.subTest(lang=lang, page=page):
                    self.assertIn(beacon, (self.tmp / 'on' / lang / page).read_text('utf-8'))
                    self.assertNotIn('cloudflareinsights', (self.tmp / 'off' / lang / page).read_text('utf-8'))

    def test_the_privacy_section_says_whether_visits_are_counted(self):
        on = (self.tmp / 'on' / 'en' / 'about' / 'index.html').read_text('utf-8')
        off = (self.tmp / 'off' / 'en' / 'about' / 'index.html').read_text('utf-8')
        self.assertIn('id="privacy"', on)
        self.assertIn('sets no cookies', on)
        self.assertIn('We count visits with Cloudflare Web Analytics', on)
        self.assertIn('We don’t count visits.', off)
        self.assertIn('لا نُحصي الزيارات.', (self.tmp / 'off' / 'ar' / 'about' / 'index.html').read_text('utf-8'))

    def test_a_malformed_token_stops_the_build(self):
        self.assertEqual(analytics_token(f' {TOKEN}\n'), TOKEN)
        for bad in ('x"><script>alert(1)</script>', TOKEN[:-1], TOKEN.upper()):
            with self.subTest(token=bad), self.assertRaises(SystemExit):
                analytics_token(bad)


if __name__ == '__main__':
    unittest.main()
