"""First-party events: accepted dimensions, privacy choices, reports and optional builds."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
from djsite.build import build


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'site' / 'tools' / f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ActionTracking(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is needed only to exercise the Worker JavaScript')
    def test_worker_and_client_reject_private_fields_and_keep_distinct_actions(self):
        result = subprocess.run(['node', str(ROOT / 'tests/action_tracking.mjs')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_local_preview_accepts_only_the_same_anonymous_dimensions(self):
        preview = module('preview_actions')
        event = dict(event='task_open', page='hub', language='ar', section='other', source='facebook', medium='paid', campaign='week1')
        self.assertTrue(preview.valid_event(event))
        for bad in (dict(event, ip='private'), dict(event, campaign='person@example.com'), dict(event, event='attended'), dict(event, page='unknown'), [], None):
            self.assertFalse(preview.valid_event(bad))

    def test_report_uses_sample_weights_and_validates_date_range(self):
        report = module('action_report')
        sql = report.query(7)
        self.assertIn('SUM(_sample_interval * double1)', sql)
        self.assertIn("INTERVAL '7' DAY", sql)
        for days in (0, 91, "7; DROP TABLE"):
            with self.assertRaises(ValueError):
                report.query(days)

    def test_action_counts_are_explicitly_enabled_and_disclosed(self):
        with tempfile.TemporaryDirectory() as tmp:
            off = Path(tmp) / 'off'
            on = Path(tmp) / 'on'
            build(off, quiet=True, analytics='')
            build(on, quiet=True, analytics='', actions=True)
            for page in ('index.html', 'hub/index.html', 'meetups/index.html', 'index/index.html'):
                self.assertNotIn('src="/assets/actions.', (off / 'en' / page).read_text())
                self.assertIn('src="/assets/actions.', (on / 'en' / page).read_text())
            about = (on / 'en/about/index.html').read_text()
            self.assertIn('without visitor identifiers', about)
            self.assertIn('Do Not Track', about)
            self.assertNotIn('We don’t count visits.', about)
            home = (on / 'en/index.html').read_text()
            self.assertIn('data-community-share', home)
            self.assertNotIn(' data-share', home, 'the community button must not collide with the chart-sharing handler')
