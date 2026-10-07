"""Hub contributor metrics (ticket #41, PRD HUB-10), against a stand-in for GitHub's GraphQL
API: counts only, no usernames written or logged, bots and maintainers left out, each person
new once across the listed projects, and off until the HUB_METRICS variable is set."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hub import __main__ as cli  # noqa: E402
from hub import metrics  # noqa: E402
from hub.github import GitHub, GitHubError  # noqa: E402

NOW = datetime(2026, 10, 7, 6, 41, tzinfo=timezone.utc)
PEOPLE = ('amina-dz', 'yacine', 'karim-b', 'sara', 'nadir', 'lina', 'owner-a', 'owner-b', 'dependabot')


def who(login, kind='User'):
    return {'__typename': kind, 'login': login} if login else None


def pr(merged, login, assoc='CONTRIBUTOR', kind='User'):
    return {'mergedAt': merged, 'authorAssociation': assoc, 'author': who(login, kind)}


def reply(at, login, assoc, kind='User', stamp='createdAt'):
    return {stamp: at, 'authorAssociation': assoc, 'author': who(login, kind)}


def item(created, login, assoc='CONTRIBUTOR', comments=(), reviews=(), merged=None, kind='User'):
    node = {'createdAt': created, 'authorAssociation': assoc, 'author': who(login, kind),
            'comments': {'nodes': list(comments)}}
    if reviews is not None:
        node['reviews'] = {'nodes': list(reviews)}
        node['mergedAt'] = merged
    return node


# Two listed repositories. Merged pull requests, oldest first, as GitHub's history query sends them:
HISTORY = {
    'dz/a': [[pr('2025-11-10T09:00:00Z', 'amina-dz'),                    # first merge before 2026: not new in 2026
              pr('2026-02-01T09:00:00Z', 'yacine'),                       # new in Q1
              pr('2026-02-02T09:00:00Z', 'owner-a', 'OWNER')],            # a maintainer
             [pr('2026-02-03T09:00:00Z', 'dependabot[bot]', 'NONE', 'Bot'),
              pr('2026-02-04T09:00:00Z', None),                           # a deleted account
              pr('2026-03-01T09:00:00Z', 'amina-dz'),                     # merged again: still not new
              pr('2026-05-05T09:00:00Z', 'karim-b', 'FIRST_TIME_CONTRIBUTOR')]],
    'dz/b': [[pr('2026-04-01T09:00:00Z', 'karim-b', 'FIRST_TIME_CONTRIBUTOR'),   # karim's first anywhere: Q2, once
              pr('2026-07-10T09:00:00Z', 'sara'),                                  # new in Q3
              pr('2026-08-01T09:00:00Z', 'owner-b', 'MEMBER')]],
}
# Pull requests and issues, newest first, as the recent queries ask for them:
PULLS = {
    'dz/a': [item('2026-01-30T10:00:00Z', 'yacine', comments=[reply('2026-01-31T10:00:00Z', 'owner-a', 'OWNER')],
                  merged='2026-02-01T09:00:00Z'),                                                  # answered in 24 h
             item('2025-12-30T10:00:00Z', 'nadir')],                                               # before 2026: stops here
    'dz/b': [item('2026-03-28T09:00:00Z', 'karim-b', 'FIRST_TIME_CONTRIBUTOR', merged='2026-04-01T09:00:00Z',
                  reviews=[reply(None, 'owner-b', 'MEMBER', stamp='submittedAt')])],             # answered by the merge, 96 h
}
ISSUES = {
    'dz/a': [item('2026-02-10T08:00:00Z', 'lina', reviews=None,
                  comments=[reply('2026-02-10T09:00:00Z', 'lina', 'CONTRIBUTOR'),                 # her own comment
                            reply('2026-02-11T08:00:00Z', 'dependabot[bot]', 'MEMBER', 'Bot'),    # a bot
                            reply('2026-02-20T08:00:00Z', 'owner-a', 'OWNER')]),                  # answered in 240 h
             item('2026-02-05T08:00:00Z', 'owner-a', 'OWNER', reviews=None),                       # a maintainer's own
             item('2026-02-04T08:00:00Z', 'dependabot[bot]', 'NONE', reviews=None, kind='Bot')],
    'dz/b': [item('2026-04-02T08:00:00Z', 'nadir', reviews=None,
                  comments=[reply('2026-04-03T08:00:00Z', 'sara', 'CONTRIBUTOR')])],              # nobody with a say: waiting
}


class FakeGraphQL:
    """Answers the three queries from the tables above, a page at a time."""

    def __init__(self, remaining=4000, missing=()):
        self.remaining, self.missing = remaining, set(missing)
        self.queries = []

    def __call__(self, method, url, body, headers):
        assert (method, url) == ('POST', 'https://api.github.com/graphql')
        assert headers.get('Authorization') == 'Bearer test-token'
        q = json.loads(body)
        text, v = q['query'], q['variables']
        repo = f'{v["owner"]}/{v["name"]}'
        self.queries.append((text.split('(')[2].split()[0] if 'states: MERGED' not in text else 'history', repo, v.get('cursor')))
        data = {'rateLimit': {'remaining': self.remaining}}
        if repo in self.missing:
            return 200, {}, json.dumps({'data': {**data, 'repository': None},
                                        'errors': [{'type': 'NOT_FOUND', 'message': f'Could not resolve {repo}'}]}).encode()
        if 'states: MERGED' in text:
            pages, key = HISTORY.get(repo, [[]]), 'pullRequests'
        elif 'issues(' in text:
            assert v['since'] == '2026-01-01T00:00:00Z'
            pages, key = [ISSUES.get(repo, [])], 'issues'
        else:
            pages, key = [PULLS.get(repo, [])], 'pullRequests'
        n = int(v['cursor']) if v.get('cursor') else 0
        page = {'pageInfo': {'hasNextPage': n + 1 < len(pages), 'endCursor': str(n + 1)}, 'nodes': pages[n]}
        return 200, {}, json.dumps({'data': {**data, 'repository': {key: page}}}).encode()


def snapshot(folder: Path, names=('dz/a', 'dz/b', 'dz/hidden')):
    folder.mkdir(parents=True, exist_ok=True)
    projects = [{'repository': n, 'name': n, 'shown': n != 'dz/hidden'} for n in names]
    (folder / 'projects.json').write_text(json.dumps({'generated_at': 'x', 'projects': projects}))


class Counts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        snapshot(self.tmp)
        self.api = FakeGraphQL()
        self.github = GitHub(token='test-token', transport=self.api)

    def run_metrics(self, **kw):
        return metrics.run(self.tmp, self.github, NOW, **kw)

    def rows(self) -> dict:
        return {r['quarter']: r for r in json.loads((self.tmp / 'metrics.json').read_text())['quarters']}

    def test_counts_by_quarter(self):
        line = self.run_metrics()
        rows = self.rows()
        self.assertEqual(list(rows), ['2026-Q1', '2026-Q2', '2026-Q3', '2026-Q4'])
        self.assertEqual([rows[q]['new_contributors'] for q in rows], [1, 1, 1, 0])
        self.assertEqual({k: rows['2026-Q1'][k] for k in ('opened', 'answered', 'within_pledge', 'waiting', 'median_hours')},
                         {'opened': 3, 'answered': 3, 'within_pledge': 2, 'waiting': 0, 'median_hours': 96.0})
        self.assertEqual({k: rows['2026-Q2'][k] for k in ('opened', 'answered', 'waiting', 'median_hours')},
                         {'opened': 1, 'answered': 0, 'waiting': 1, 'median_hours': None})
        self.assertEqual([rows[q]['complete'] for q in rows], [True, True, True, False])
        self.assertIn('2 projects, 2026-Q1 to 2026-Q4: 3 new contributors; 4 issues and pull requests from newcomers, 3 answered', line)
        self.assertNotIn('dz/hidden', ' '.join(r for _, r, _ in self.api.queries), 'only the projects the Hub shows')

    def test_no_usernames_anywhere(self):
        line = self.run_metrics()
        written = (self.tmp / 'metrics.json').read_text()
        for name in PEOPLE:
            self.assertNotIn(name, written)
            self.assertNotIn(name, line)
        self.assertEqual(sorted(json.loads(written)), ['about', 'generated_at', 'pledge_days', 'projects', 'quarters'])

    def test_every_page_is_read_and_old_items_stop_the_reading(self):
        self.run_metrics()
        history = [(r, c) for kind, r, c in self.api.queries if kind == 'history']
        self.assertEqual(history, [('dz/a', None), ('dz/a', '1'), ('dz/b', None)])
        self.assertEqual(len(self.api.queries), 7, 'two pages of history for dz/a, then one page of each kind')

    def test_once_a_day_with_daily(self):
        self.run_metrics()
        calls = len(self.api.queries)
        self.assertEqual(self.run_metrics(daily=True), 'Hub metrics: already counted today.')
        self.assertEqual(len(self.api.queries), calls)
        metrics.run(self.tmp, self.github, NOW.replace(day=8), daily=True)
        self.assertGreater(len(self.api.queries), calls, 'the next day counts again')

    def test_a_repository_github_cant_find_is_skipped(self):
        self.api.missing = {'dz/b'}
        self.run_metrics()
        self.assertEqual([r['new_contributors'] for r in self.rows().values()], [1, 1, 0, 0], 'karim from dz/a, in Q2')

    def test_nothing_is_written_when_github_fails(self):
        for api, message in ((FakeGraphQL(remaining=40), 'GraphQL points'),
                             (lambda *a: (401, {}, b'{"message": "Bad credentials"}'), 'needs a token'),
                             (lambda *a: (200, {}, b'{"errors": [{"type": "FORBIDDEN", "message": "no"}]}'), 'GraphQL API: no')):
            with self.subTest(message=message):
                with self.assertRaisesRegex(GitHubError, message):
                    metrics.run(self.tmp, GitHub(token='test-token', transport=api, tries=1), NOW)
                self.assertFalse((self.tmp / 'metrics.json').exists())

    def test_needs_a_snapshot(self):
        with self.assertRaisesRegex(ValueError, 'run python -m hub sync first'):
            metrics.run(self.tmp / 'nothing', self.github, NOW)

    def test_command_line(self):
        original = metrics.GitHub
        metrics.GitHub = lambda: GitHub(token='test-token', transport=FakeGraphQL())
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(['metrics', '--out', str(self.tmp)]), 0)
                self.assertEqual(cli.main(['metrics', '--out', str(self.tmp / 'nothing')]), 1)
        finally:
            metrics.GitHub = original
        self.assertIn('Hub metrics: 2 projects', out.getvalue())
        self.assertIn('Hub metrics stopped, nothing was written', err.getvalue())


class Helpers(unittest.TestCase):
    def test_quarters(self):
        self.assertEqual(metrics.quarters((2026, 1), NOW), ['2026-Q1', '2026-Q2', '2026-Q3', '2026-Q4'])
        self.assertEqual(metrics.quarters((2026, 3), datetime(2027, 1, 2, tzinfo=timezone.utc)), ['2026-Q3', '2026-Q4', '2027-Q1'])

    def test_bots_and_deleted_accounts_are_nobody(self):
        self.assertIsNone(metrics.person({'author': None}))
        self.assertIsNone(metrics.person({'author': who('renovate', 'Bot')}))
        self.assertIsNone(metrics.person({'author': who('github-actions[bot]')}))
        self.assertEqual(metrics.person({'author': who('sara')}), 'sara')
        self.assertIsNone(metrics.newcomer({'author': who('sara'), 'authorAssociation': 'COLLABORATOR'}))


class Workflow(unittest.TestCase):
    def test_off_until_the_variable_is_set(self):
        text = (ROOT / '.github' / 'workflows' / 'hub.yml').read_text()
        step = text[text.index('- name: Count contributors'):text.index('- name: Build the site with it')]
        self.assertIn("if: vars.HUB_METRICS == 'true'", step)
        self.assertIn('continue-on-error: true', step, 'the sync goes on without the counts')
        self.assertIn('python -m hub metrics --daily', step)
        self.assertLess(text.index('- name: Sync from GitHub'), text.index('- name: Count contributors'))


if __name__ == '__main__':
    unittest.main()
