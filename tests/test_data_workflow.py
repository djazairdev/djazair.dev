"""The scheduled data update (ticket #14): .github/workflows/data.yml and its two scripts,
run against a throwaway git repository and a stand-in for the GitHub CLI."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / '.github' / 'workflows'
SCRIPTS = ROOT / '.github' / 'scripts'

FAKE_GH = """#!/usr/bin/env bash
echo "gh $*" >> "$SIM/gh.log"
case "$1 $2" in
  "pr list") echo "${SIM_PR_EXISTING:-}";;
  "pr create") [ -n "${SIM_PR_FAIL:-}" ] && { echo 'not permitted' >&2; exit 1; }; echo https://github.com/o/r/pull/77;;
  "run list") echo 12345;;
  "run watch") exit "${SIM_CI_EXIT:-0}";;
  "issue list") echo "${SIM_ISSUE_EXISTING:-}";;
esac
"""


def git(*args, cwd):
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)


@unittest.skipUnless(shutil.which('bash') and shutil.which('git'), 'needs bash and git')
class Scripts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        bin_ = self.tmp / 'bin'
        bin_.mkdir()
        (bin_ / 'gh').write_text(FAKE_GH)
        (bin_ / 'sleep').write_text('#!/bin/sh\nexit 0\n')
        for f in bin_.iterdir():
            f.chmod(0o755)
        remote, work = self.tmp / 'remote.git', self.tmp / 'work'
        git('init', '-q', '--bare', '-b', 'main', str(remote), cwd=self.tmp)
        git('init', '-q', '-b', 'main', str(work), cwd=self.tmp)
        (work / 'data').mkdir()
        (work / 'data' / 'README.md').write_text('data\n')
        git('add', '.', cwd=work)
        git('-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-q', '-m', 'start', cwd=work)
        git('remote', 'add', 'origin', str(remote), cwd=work)
        git('push', '-q', 'origin', 'main', cwd=work)
        self.work, self.remote = work, remote
        self.runner = self.tmp / 'runner'
        self.runner.mkdir()
        (self.runner / 'validation.md').write_text('Validation **passed**.\n')
        self.env = {**os.environ, 'PATH': f'{bin_}:{os.environ["PATH"]}', 'SIM': str(self.tmp), 'GH_TOKEN': 'x',
                    'GITHUB_SERVER_URL': 'https://github.com', 'GITHUB_REPOSITORY': 'o/r', 'GITHUB_RUN_ID': '42',
                    'RUNNER_TEMP': str(self.runner), 'QUARTER': '2026-Q2', 'COMMIT': '0123456789abcdef' * 2 + '01234567',
                    'REVISIONS': 'false'}

    def run_script(self, name, **env):
        return subprocess.run(['bash', str(SCRIPTS / name)], cwd=self.work, env={**self.env, **env}, capture_output=True,
                              text=True)

    def calls(self) -> list:
        log = self.tmp / 'gh.log'
        return [line.split(' --')[0] for line in log.read_text().splitlines()] if log.exists() else []

    def new_data(self):
        (self.work / 'data' / 'derived').mkdir()
        (self.work / 'data' / 'derived' / 'latest.json').write_text('{"quarter": "2026-Q2"}\n')

    def test_no_change_no_pull_request(self):
        result = self.run_script('data-pr.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('nothing to publish', result.stdout)
        self.assertEqual(self.calls(), [])

    def test_new_data_is_merged_then_deployed(self):
        self.new_data()
        result = self.run_script('data-pr.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ['gh pr list', 'gh pr create', 'gh workflow run ci.yml', 'gh run list', 'gh run watch 12345',
                                        'gh pr merge 77', 'gh workflow run ci.yml', 'gh run list', 'gh run watch 12345'])
        log = (self.tmp / 'gh.log').read_text()
        self.assertIn('workflow run ci.yml --ref data/2026-q2-0123456789ab', log, 'CI runs on the branch first')
        self.assertIn('workflow run ci.yml --ref main', log, 'then on main, which deploys')
        branches = subprocess.run(['git', 'branch', '--list'], cwd=self.remote, capture_output=True, text=True).stdout
        self.assertIn('data/2026-q2-0123456789ab', branches)
        body = (self.runner / 'pull-request.md').read_text()
        self.assertIn('2026-Q2', body)
        self.assertIn('Validation **passed**', body)
        self.assertIn('could not be drawn, so shared links show the site', body)

    def test_the_share_images_go_with_the_data(self):
        self.new_data()
        images = self.work / 'site' / 'static' / 'share' / '2026-q2'
        images.mkdir(parents=True)
        for lang in ('en', 'ar'):
            (images / f'{lang}.png').write_bytes(b'\x89PNG')
        result = self.run_script('data-pr.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        files = subprocess.run(['git', 'show', '--name-only', '--format=', 'data/2026-q2-0123456789ab'], cwd=self.remote,
                               capture_output=True, text=True).stdout.split()
        self.assertEqual(sorted(files), ['data/derived/latest.json', 'site/static/share/2026-q2/ar.png',
                                         'site/static/share/2026-q2/en.png'])
        self.assertIn('are in `site/static/share/2026-q2/`', (self.runner / 'pull-request.md').read_text())

    def test_revisions_wait_for_review(self):
        self.new_data()
        (self.runner / 'revisions.md').write_text('**3 past values changed**\n')
        result = self.run_script('data-pr.sh', REVISIONS='true')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('gh pr merge 77', self.calls())
        self.assertIn('gh pr comment 77', self.calls())
        self.assertIn('3 past values changed', (self.runner / 'pull-request.md').read_text())

    def test_failing_ci_stops_before_the_merge(self):
        self.new_data()
        result = self.run_script('data-pr.sh', SIM_CI_EXIT='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('gh pr merge 77', self.calls())

    def test_a_refused_pull_request_explains_the_setting(self):
        self.new_data()
        result = self.run_script('data-pr.sh', SIM_PR_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        notes = (self.runner / 'failure-notes.md').read_text()
        self.assertIn('Allow GitHub Actions to create and', notes)
        self.assertIn('compare/main...data/2026-q2-0123456789ab', notes)

    def test_a_failure_opens_one_issue(self):
        (self.runner / 'validation.md').write_text('Validation **failed** with 2 errors.\n')
        result = self.run_script('data-failed.sh', VALIDATION='failure')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ['gh issue list', 'gh issue create'])
        body = (self.runner / 'issue.md').read_text()
        self.assertIn('**failed** with 2 errors', body)
        self.assertIn('Nothing was merged', body)
        self.assertIn('last good data', body)

    def test_a_repeated_failure_comments_on_the_open_issue(self):
        result = self.run_script('data-failed.sh', VALIDATION='success', SIM_ISSUE_EXISTING='9')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ['gh issue list', 'gh issue comment 9'])
        self.assertNotIn('Validation', (self.runner / 'issue.md').read_text(), 'the report only when validation failed')


    # ---- the Hub snapshot (ticket #25)
    def hub_files(self, issues='[]'):
        hub = self.work / 'data' / 'derived' / 'hub'
        hub.mkdir(parents=True, exist_ok=True)
        (hub / 'issues.json').write_text(f'{{"generated_at": "2026-10-06T18:00:00Z", "issues": {issues}}}\n')
        (hub / 'projects.json').write_text('{"generated_at": "2026-10-06T18:00:00Z", "projects": []}\n')
        return hub

    def remote_git(self, *args) -> str:
        return subprocess.run(['git', *args], cwd=self.remote, capture_output=True, text=True, check=True).stdout.strip()

    def test_hub_snapshot_without_the_branch(self):
        result = self.run_script('hub-snapshot.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No hub-data branch yet', result.stdout)
        self.assertFalse((self.work / 'data' / 'derived' / 'hub').exists())

    def test_hub_snapshot_fails_when_the_remote_is_unreachable(self):
        git('remote', 'set-url', 'origin', str(self.tmp / 'gone.git'), cwd=self.work)
        result = self.run_script('hub-snapshot.sh')
        self.assertNotEqual(result.returncode, 0, 'a deploy must not drop the Hub because a fetch failed')

    def test_hub_publish_saves_the_snapshot_on_its_own_branch_then_deploys(self):
        main = self.remote_git('rev-parse', 'main')
        self.hub_files()
        result = self.run_script('hub-publish.sh', SUMMARY='Hub: 0 projects (0 shown), 0 open issues.')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ['gh workflow run ci.yml', 'gh run list', 'gh run watch 12345'])
        self.assertIn('workflow run ci.yml --ref main', (self.tmp / 'gh.log').read_text())
        self.assertEqual(self.remote_git('ls-tree', '--name-only', 'hub-data').split(), ['issues.json', 'projects.json'])
        self.assertIn('Hub: 0 projects', self.remote_git('log', '-1', '--format=%B', 'hub-data'))
        self.assertEqual(self.remote_git('rev-parse', 'main'), main, 'main never changes')
        self.assertEqual(subprocess.run(['git', 'status', '--porcelain'], cwd=self.work, capture_output=True, text=True).stdout,
                         '?? data/derived/\n', 'the checkout is left as it was')

        first = self.remote_git('rev-parse', 'hub-data')
        (self.tmp / 'gh.log').unlink()
        result = self.run_script('hub-publish.sh')
        self.assertIn("didn't change", result.stdout)
        self.assertEqual(self.calls(), [], 'no deploy when nothing changed')

        self.hub_files(issues='[{"number": 1}]')
        result = self.run_script('hub-publish.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.remote_git('rev-parse', 'hub-data^'), first, 'each sync adds a commit')

        shutil.rmtree(self.work / 'data' / 'derived' / 'hub')
        result = self.run_script('hub-snapshot.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"number": 1', (self.work / 'data' / 'derived' / 'hub' / 'issues.json').read_text())

    def test_hub_publish_stops_when_ci_fails(self):
        self.hub_files()
        result = self.run_script('hub-publish.sh', SIM_CI_EXIT='1')
        self.assertNotEqual(result.returncode, 0)


class Workflow(unittest.TestCase):
    def test_schedules_wait_for_the_switch(self):
        for path in WORKFLOWS.glob('*.yml'):
            text = path.read_text()
            if re.search(r'^\s+schedule:', text, re.M):
                self.assertIn("vars.SCHEDULES_ENABLED == 'true'", text, path.name)

    def test_the_merge_comes_after_validation_tests_and_build(self):
        text = (WORKFLOWS / 'data.yml').read_text()
        order = [text.index(s) for s in ('pipeline fetch', 'pipeline publish', 'pipeline revisions', 'unittest discover',
                                         'site/build.py', 'share.py --release', 'data-pr.sh', 'data-failed.sh')]
        self.assertEqual(order, sorted(order))
        self.assertIn('if: failure()', text)

    def test_the_hub_sync_builds_before_it_saves_and_deploys(self):
        text = (WORKFLOWS / 'hub.yml').read_text()
        order = [text.index(s) for s in ('hub-snapshot.sh', 'hub sync', 'site/build.py', 'hub-publish.sh')]
        self.assertEqual(order, sorted(order))
        self.assertIn("cron: '41 */6 * * *'", text, 'every 6 hours (AC-HUB-4)')
        self.assertIn('GITHUB_TOKEN: ${{ github.token }}', text, 'authenticated: the higher limit, and 304s are free')
        ci = (WORKFLOWS / 'ci.yml').read_text()
        self.assertLess(ci.index('hub-snapshot.sh'), ci.index('python site/build.py'), 'every build has the Hub snapshot')

    def test_ci_deploys_main_when_started_by_hand(self):
        text = (WORKFLOWS / 'ci.yml').read_text()
        self.assertIn('workflow_dispatch', text)
        self.assertIn("github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'", text)

    def test_scripts_are_strict_and_executable(self):
        for path in SCRIPTS.glob('*.sh'):
            self.assertIn('set -euo pipefail', path.read_text(), path.name)
            self.assertTrue(os.access(path, os.X_OK), f'{path.name} is executable')


if __name__ == '__main__':
    unittest.main()
