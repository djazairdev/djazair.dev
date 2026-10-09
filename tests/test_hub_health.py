"""Hub health checks (ticket #26): flags, the 14 days before a flagged project is hidden, a
removed topic hiding a project at once (AC-HUB-3), and the report."""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hub import health, sync  # noqa: E402
from hub.github import GitHub  # noqa: E402
from test_hub_sync import REGISTRY, FakeGitHub, commits, repository, routes  # noqa: E402

DAY0 = datetime(2026, 10, 6, 18, 41, tzinfo=timezone.utc)
DZ = 'djazairdev/djazair.dev'
EMPTY_HW = f'/repos/{DZ}/issues?state=open&labels=help%20wanted&per_page=100&page=1'
EMPTY_GFI = f'/repos/{DZ}/issues?state=open&labels=good%20first%20issue&per_page=100&page=1'


def project(**kw):
    p = {'repository': 'o/n', 'found': True, 'topic': True, 'archived': False, 'last_commit': '2026-10-01T00:00:00Z', 'issues': 3}
    p.update(kw)
    return p


class Rules(unittest.TestCase):
    def test_what_is_flagged(self):
        today = date(2026, 10, 6)
        self.assertEqual(health.problems(project(), today), {})
        self.assertEqual(set(health.problems(project(last_commit='2026-07-07T00:00:00Z', issues=0), today)), {'inactive'})
        self.assertEqual(health.problems(project(issues=0), today), {}, 'no open beginner issues is not a flag (D27)')
        self.assertEqual(health.problems(project(last_commit='2026-07-08T00:00:00Z'), today), {}, '90 days is still active')
        self.assertIn('91 days ago', health.problems(project(last_commit='2026-07-07T00:00:00Z'), today)['inactive'])
        self.assertEqual(set(health.problems(project(topic=False, archived=True), today)), {'topic', 'archived'})
        self.assertEqual(set(health.problems(project(found=False), today)), {'missing'})
        self.assertIn('No commits', health.problems(project(last_commit=None), today)['inactive'])

    def test_fourteen_days_then_hidden_and_back_when_fixed(self):
        start = date(2026, 10, 1)
        old = '2026-06-01T00:00:00Z'
        projects = [project(last_commit=old)]
        health.apply(projects, {}, start)
        self.assertEqual((projects[0]['status'], projects[0]['shown'], projects[0]['hide_on']), ('flagged', True, '2026-10-15'))
        for day, status in ((13, 'flagged'), (14, 'hidden'), (30, 'hidden')):
            again = [project(last_commit=old)]
            health.apply(again, {'o/n': projects[0]}, start + timedelta(days=day))
            with self.subTest(day=day):
                self.assertEqual(again[0]['status'], status)
                self.assertEqual(again[0]['flags'][0]['since'], '2026-10-01', 'the date first flagged is kept')
        fixed = [project(last_commit='2026-10-31T00:00:00Z')]
        health.apply(fixed, {'o/n': again[0]}, start + timedelta(days=31))
        self.assertEqual((fixed[0]['status'], fixed[0]['flags'], fixed[0]['shown']), ('healthy', [], True))

    def test_a_removed_topic_hides_at_once(self):
        projects = [project(topic=False)]
        health.apply(projects, {}, date(2026, 10, 6))
        self.assertEqual((projects[0]['status'], projects[0]['hide_on']), ('hidden', '2026-10-06'))


class InTheSync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.registry = self.tmp / 'projects.yml'
        self.registry.write_text(REGISTRY)
        self.out = self.tmp / 'hub'

    def sync(self, answers, when):
        return sync.run(self.registry, self.out, GitHub('t', FakeGitHub(answers)), when)

    def projects(self):
        return {p['repository']: p for p in json.loads((self.out / 'projects.json').read_text())['projects']}

    def test_no_open_beginner_issues_is_listed_not_flagged(self):
        self.sync(routes(**{EMPTY_GFI: [], EMPTY_HW: []}), DAY0)
        dz = self.projects()[DZ]
        self.assertEqual((dz['status'], dz['shown'], dz['issues']), ('healthy', True, 0))
        report = (self.out / 'HEALTH.md').read_text()
        self.assertIn(f'## No open beginner issues\n\nNot a flag', report)
        self.assertIn(f'[{DZ}](https://github.com/{DZ}).', report.split('## No open beginner issues')[1])

    def test_a_project_that_removes_the_topic_leaves_within_a_sync(self):
        self.sync(routes(), DAY0)
        self.assertIn(DZ, {i['repo'] for i in json.loads((self.out / 'issues.json').read_text())['issues']})
        line = self.sync(routes(**{f'/repos/{DZ}': repository(DZ, topics=['algeria'])}), DAY0 + timedelta(hours=6))
        self.assertEqual(self.projects()[DZ]['status'], 'hidden')
        self.assertNotIn(DZ, {i['repo'] for i in json.loads((self.out / 'issues.json').read_text())['issues']})
        self.assertIn('(1 healthy, 0 flagged, 1 hidden)', line)

    def test_flags_carry_over_and_the_report_lists_them(self):
        quiet = routes(**{EMPTY_GFI: [], EMPTY_HW: [], f'/repos/{DZ}/commits?sha=main&per_page=1': commits('2026-06-01T00:00:00Z')})
        self.sync(quiet, DAY0)
        self.assertEqual(self.projects()[DZ]['status'], 'flagged')
        self.sync(quiet, DAY0 + timedelta(days=14))
        dz = self.projects()[DZ]
        self.assertEqual((dz['status'], [f['since'] for f in dz['flags']]), ('hidden', ['2026-10-06']))
        report = (self.out / 'HEALTH.md').read_text()
        self.assertIn('Checked on 20 October 2026 at 18:41 UTC', report)
        self.assertIn('**2 projects: 1 healthy, 0 flagged, 1 hidden.**', report)
        self.assertIn(f'| [{DZ}](https://github.com/{DZ}) | No commit in 90 days | Last commit on 2026-06-01, 141 days ago. | '
                      '2026-10-06 | 2026-10-20 |', report)
        self.assertNotIn('No open `good first issue`', report, 'not a flag (D27)')
        self.assertIn('## Healthy\n\n[chargily/chargily-pay-python](https://github.com/chargily/chargily-pay-python).', report)


if __name__ == '__main__':
    unittest.main()
