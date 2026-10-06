"""The Hub sync (ticket #25), against a stand-in for the GitHub API that answers with ETags
the way GitHub does: no personal data kept, conditional requests, the quota checked first."""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'site'))

from hub import __main__ as cli  # noqa: E402
from hub import sync  # noqa: E402
from hub.github import GitHub, GitHubError  # noqa: E402

NOW = datetime(2026, 10, 6, 18, 0, tzinfo=timezone.utc)
PEOPLE = ('amina-dz', 'yacine', 'karim-b', 'Amina Benali', 'amina@example.com', 'avatars.githubusercontent.com')

REGISTRY = """projects:
  - repository: chargily/chargily-pay-python
    category: library
    tags: [payments]
    maintainer_pledge: true
    added: 2026-10-01
  - repository: djazairdev/djazair.dev
    category: tool
    tags: [open-data, arabic]
    maintainer_pledge: true
    added: 2026-10-06
"""


def person(login):
    return {'login': login, 'id': 1, 'avatar_url': f'https://avatars.githubusercontent.com/u/1?v=4&{login}',
            'html_url': f'https://github.com/{login}', 'type': 'User'}


def issue(n, title, labels, created, body='', pr=False):
    out = {'number': n, 'html_url': f'https://github.com/x/y/issues/{n}', 'title': title, 'state': 'open',
           'labels': [{'name': l, 'color': 'aaaaaa'} for l in labels], 'created_at': created, 'updated_at': created,
           'user': person('amina-dz'), 'assignee': person('yacine'), 'assignees': [person('yacine')], 'comments': 3,
           'body': body, 'author_association': 'CONTRIBUTOR'}
    if pr:
        out['pull_request'] = {'url': 'x'}
    return out


def repository(full_name, **changes):
    out = {'full_name': full_name, 'html_url': f'https://github.com/{full_name}', 'private': False, 'archived': False,
           'description': 'Accept Edahabia and CIB payments.\nFrom Python.', 'language': 'Python', 'default_branch': 'main',
           'topics': ['djazairdev', 'payments'], 'license': {'spdx_id': 'MIT', 'name': 'MIT License'}, 'has_issues': True,
           'owner': person('karim-b'), 'stargazers_count': 40}
    out.update(changes)
    return out


def commits(day):
    who = {'name': 'Amina Benali', 'email': 'amina@example.com', 'date': day}
    return [{'sha': 'abc', 'commit': {'author': who, 'committer': who, 'message': 'Fix'}, 'author': person('amina-dz'),
             'committer': person('amina-dz')}]


GFI, HW = 'labels=good%20first%20issue', 'labels=help%20wanted'


def routes(**changes) -> dict:
    pay, dz = 'chargily/chargily-pay-python', 'djazairdev/djazair.dev'
    out = {
        f'/repos/{pay}': repository(pay),
        f'/repos/{pay}/commits?sha=main&per_page=1': commits('2026-10-02T09:00:00Z'),
        f'/repos/{pay}/issues?state=open&{GFI}&per_page=100&page=1': [
            issue(4, 'Add type hints to the client', ['good first issue', 'python'], '2026-09-20T10:00:00Z',
                  "Reported by @karim-b.\n\n**You'll need:** Python, `mypy` (ask @yacine)"),
            issue(9, 'Bump the SDK', ['good first issue'], '2026-10-01T10:00:00Z', pr=True)],
        f'/repos/{pay}/issues?state=open&{HW}&per_page=100&page=1': [
            issue(4, 'Add type hints to the client', ['good first issue', 'help wanted'], '2026-09-20T10:00:00Z'),
            issue(7, 'Document webhooks in Arabic', ['help wanted', 'docs'], '2026-10-05T08:00:00Z',
                  "### You'll need\n\nFluent Arabic, Markdown\n")],
        f'/repos/{dz}': repository(dz, language='Python', description='The Algeria Developer Index.'),
        f'/repos/{dz}/commits?sha=main&per_page=1': commits('2026-10-06T12:00:00Z'),
        f'/repos/{dz}/issues?state=open&{GFI}&per_page=100&page=1': [
            issue(51, 'Proofread the Arabic methodology page', ['good first issue', 'translation'], '2026-10-04T10:00:00Z')],
        f'/repos/{dz}/issues?state=open&{HW}&per_page=100&page=1': [],
    }
    out.update(changes)
    return out


class FakeGitHub:
    """Answers paths from a dict, with an ETag per answer; 304 when If-None-Match matches."""

    def __init__(self, answers: dict, remaining=4990):
        self.answers = answers
        self.remaining = remaining
        self.calls = []

    def __call__(self, method, url, body, headers):
        path = url.replace('https://api.github.com', '')
        self.calls.append((path, headers.get('If-None-Match')))
        head = {'x-ratelimit-limit': '5000', 'x-ratelimit-remaining': str(self.remaining), 'x-ratelimit-reset': '1791295200'}
        if path == '/rate_limit':
            core = {'limit': 5000, 'remaining': self.remaining, 'reset': 1791295200, 'used': 5000 - self.remaining}
            return 200, head, json.dumps({'resources': {'core': core}}).encode()
        if path not in self.answers:
            return 404, head, b'{"message": "Not Found"}'
        data = self.answers[path]
        if isinstance(data, tuple):                                   # (status, body)
            return data[0], head, json.dumps(data[1]).encode()
        raw = json.dumps(data).encode()
        etag = f'W/"{abs(hash(raw)) % 10 ** 12}"'
        if headers.get('If-None-Match') == etag:
            return 304, {**head, 'ETag': etag}, b''
        self.remaining -= 1
        return 200, {**head, 'ETag': etag}, raw


class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.registry = self.tmp / 'projects.yml'
        self.registry.write_text(REGISTRY)
        self.out = self.tmp / 'hub'

    def sync(self, fake=None):
        fake = fake or FakeGitHub(routes())
        github = GitHub('t', fake)
        line = sync.run(self.registry, self.out, github, NOW)
        return line, fake, github

    def read(self, name):
        return json.loads((self.out / name).read_text('utf-8'))

    def test_the_snapshot(self):
        line, _, _ = self.sync()
        issues = self.read('issues.json')
        self.assertEqual(issues['generated_at'], '2026-10-06T18:00:00Z')
        self.assertEqual([(i['repo'], i['number']) for i in issues['issues']],
                         [('chargily/chargily-pay-python', 7), ('djazairdev/djazair.dev', 51), ('chargily/chargily-pay-python', 4)],
                         'newest first, both labels, each issue once, pull requests left out')
        first = issues['issues'][0]
        self.assertEqual(set(first), {'number', 'url', 'title', 'labels', 'created_at', 'needs', 'repo', 'language'})
        self.assertEqual((first['language'], first['needs']), ('Python', 'Fluent Arabic, Markdown'))
        self.assertEqual(issues['issues'][2]['needs'], 'Python, mypy', 'the aside that names someone is taken out')
        projects = self.read('projects.json')['projects']
        pay = projects[0]
        self.assertEqual({k: pay[k] for k in ('repository', 'category', 'tags', 'pledge', 'added', 'found', 'language', 'licence',
                                              'topic', 'archived', 'last_commit', 'issues', 'shown')},
                         {'repository': 'chargily/chargily-pay-python', 'category': 'library', 'tags': ['payments'],
                          'pledge': True, 'added': '2026-10-01', 'found': True, 'language': 'Python', 'licence': 'MIT',
                          'topic': True, 'archived': False, 'last_commit': '2026-10-02T09:00:00Z', 'issues': 2, 'shown': True})
        self.assertEqual(pay['description'], 'Accept Edahabia and CIB payments. From Python.')
        self.assertIn('Hub: 2 projects (2 healthy, 0 flagged, 0 hidden), 3 open issues.', line)
        self.assertRegex(line, r'GitHub API: 10 requests, 0 unchanged \(304, free\); 4,982 of 5,000 left, resets at \d\d:\d\d UTC')

    def test_no_personal_data_is_kept(self):
        self.sync()
        for name in ('projects.json', 'issues.json', 'cache.json'):
            text = (self.out / name).read_text('utf-8')
            with self.subTest(file=name):
                for who in PEOPLE:
                    self.assertNotIn(who, text)
                for key in ('"user"', '"assignee"', '"assignees"', '"body"', '"owner"', '"avatar_url"', '"author"', '"login"'):
                    self.assertNotIn(key, text)
                self.assertNotRegex(text, r'(?<![\w.])@[a-z]')

    def test_the_next_run_asks_with_etags_and_unchanged_answers_are_free(self):
        self.sync()
        first = {n: self.read(n) for n in ('projects.json', 'issues.json')}
        line, fake, github = self.sync()
        asked = [(p, tag) for p, tag in fake.calls if p != '/rate_limit']
        self.assertTrue(asked and all(tag for _, tag in asked), 'every request carries the last ETag')
        self.assertEqual(github.unchanged, len(asked))
        self.assertEqual(fake.remaining, 4990, 'nothing counted against the quota')
        self.assertIn(f'{len(asked)} unchanged (304, free)', line)
        for name, doc in first.items():
            self.assertEqual(self.read(name), doc, name)

    def test_a_changed_answer_is_fetched_again(self):
        self.sync()
        answers = routes()
        answers[f'/repos/djazairdev/djazair.dev/issues?state=open&{HW}&per_page=100&page=1'] = [
            issue(60, 'Test the Trends table with a screen reader', ['help wanted', 'accessibility'], '2026-10-06T09:00:00Z')]
        _, fake, github = self.sync(FakeGitHub(answers))
        self.assertEqual(github.unchanged, len([c for c in fake.calls if c[0] != '/rate_limit']) - 1)
        self.assertEqual(self.read('issues.json')['issues'][0]['number'], 60)

    def test_a_removed_topic_takes_the_project_off_at_once(self):
        answers = routes(**{'/repos/djazairdev/djazair.dev': repository('djazairdev/djazair.dev', topics=['algeria'])})
        self.sync(FakeGitHub(answers))
        projects = {p['repository']: p for p in self.read('projects.json')['projects']}
        self.assertEqual((projects['djazairdev/djazair.dev']['topic'], projects['djazairdev/djazair.dev']['shown']), (False, False))
        self.assertNotIn('djazairdev/djazair.dev', {i['repo'] for i in self.read('issues.json')['issues']})

    def test_missing_archived_and_renamed_repositories(self):
        pay = 'chargily/chargily-pay-python'
        answers = routes(**{f'/repos/{pay}': repository('chargily/pay-python', archived=True)})
        answers = {k.replace(f'{pay}/', 'chargily/pay-python/'): v for k, v in answers.items()}
        del answers['/repos/djazairdev/djazair.dev']
        self.sync(FakeGitHub(answers))
        projects = self.read('projects.json')['projects']
        self.assertEqual((projects[0]['name'], projects[0]['url']), ('chargily/pay-python', 'https://github.com/chargily/pay-python'))
        self.assertEqual((projects[0]['archived'], projects[0]['shown']), (True, False))
        self.assertEqual((projects[1]['found'], projects[1]['shown']), (False, False))
        self.assertEqual(self.read('issues.json')['issues'], [])

    def test_more_than_a_page_of_issues(self):
        dz = 'djazairdev/djazair.dev'
        page1 = [issue(n, f'Issue {n}', ['good first issue'], f'2026-09-01T{n % 24:02d}:00:00Z', pr=n % 10 == 0)
                 for n in range(1, 101)]
        answers = routes(**{f'/repos/{dz}/issues?state=open&{GFI}&per_page=100&page=1': page1,
                            f'/repos/{dz}/issues?state=open&{GFI}&per_page=100&page=2': [
                                issue(200, 'Last one', ['good first issue'], '2026-09-02T00:00:00Z')]})
        self.sync(FakeGitHub(answers))
        dz_project = self.read('projects.json')['projects'][1]
        self.assertEqual(dz_project['issues'], 91, '90 issues on page 1 (10 were pull requests) and 1 on page 2')

    def test_the_quota_is_checked_before_anything_is_asked(self):
        fake = FakeGitHub(routes(), remaining=9)
        with self.assertRaisesRegex(GitHubError, 'only 9 of 5000 API requests are left until .* needs up to 10'):
            sync.run(self.registry, self.out, GitHub('t', fake), NOW)
        self.assertEqual([p for p, _ in fake.calls], ['/rate_limit'])
        self.assertFalse(self.out.exists(), 'nothing written')

    def test_a_github_failure_writes_nothing(self):
        self.sync()
        before = (self.out / 'issues.json').read_text()
        answers = routes(**{'/repos/djazairdev/djazair.dev': (500, {'message': 'oops'})})
        with self.assertRaises(GitHubError):
            sync.run(self.registry, self.out, GitHub('t', FakeGitHub(answers), tries=1), NOW)
        self.assertEqual((self.out / 'issues.json').read_text(), before)

    def test_the_command(self):
        self.registry.write_text('projects:\n  - repository: nope\n')
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(cli.main(['sync', '--registry', str(self.registry), '--out', str(self.out)]), 1)
        self.assertIn('nothing was written', err.getvalue())
        self.assertFalse(self.out.exists())

    def test_the_site_reads_the_snapshot(self):
        from djsite import data
        self.sync()
        issues = data.hub_issues(self.out)
        self.assertEqual([i['days'] for i in issues], [1, 2, 16])


class Needs(unittest.TestCase):
    def test_formats(self):
        cases = {"You'll need: Python, pytest": 'Python, pytest',
                 '- **You’ll need:** TypeScript and `Intl.NumberFormat`.': 'TypeScript and Intl.NumberFormat',
                 '### Skills needed\n\n_No response_': '',
                 '## You will need\n\n[NVDA](https://nvaccess.org), JAWS or VoiceOver': 'NVDA, JAWS or VoiceOver',
                 'ستحتاج إلى: العربية، Markdown': 'العربية، Markdown',
                 'Skills: Python — pair with @maintainer-x': '',
                 'Nothing about skills here.': '',
                 'You’ll need: ' + 'Python, ' * 40: None}
        for body, expected in cases.items():
            with self.subTest(body=body[:30]):
                got = sync.needs(body)
                if expected is None:
                    self.assertLessEqual(len(got), sync.LIMITS['needs'])
                    self.assertTrue(got.endswith('…'))
                else:
                    self.assertEqual(got, expected)
                self.assertNotIn('@', got)


if __name__ == '__main__':
    unittest.main()
