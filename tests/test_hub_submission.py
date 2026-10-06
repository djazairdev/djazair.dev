"""Hub submissions and inclusion checks (ticket #16), against a stand-in for the GitHub API."""
import json
import re
import shutil
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hub import checks, miniyaml, submission  # noqa: E402
from hub.github import GitHub  # noqa: E402

TODAY = date(2026, 10, 6)
REPO = 'owner/name'


class FakeAPI:
    """Answers GitHub REST paths from a dict; records every call."""

    def __init__(self, routes: dict):
        self.routes = routes
        self.calls = []

    def __call__(self, method, url, body, headers):
        path = url.replace('https://api.github.com', '')
        self.calls.append((method, path, json.loads(body) if body else None))
        for (m, pattern), answer in self.routes.items():
            if m == method and re.fullmatch(pattern, path):
                status, data = answer(path, body) if callable(answer) else answer
                head = {'X-RateLimit-Remaining': '0'} if status == 403 else {}
                return status, head, json.dumps(data).encode() if data is not None else b''
        return 404, {}, b'{"message": "Not Found"}'


def healthy(**changes) -> dict:
    """Routes for a repository that passes every automatic check."""
    repo = {'full_name': REPO, 'private': False, 'archived': False, 'default_branch': 'main', 'has_issues': True,
            'topics': ['djazairdev', 'algeria'], 'license': {'spdx_id': 'MIT', 'name': 'MIT License'}}
    repo.update(changes.pop('repo', {}))
    issue = lambda n, pr=False: {'number': n, **({'pull_request': {}} if pr else {})}
    routes = {
        ('GET', f'/repos/{REPO}'): (200, repo),
        ('GET', rf'/repos/{REPO}/commits\?sha=main&per_page=1'): (200, [{'commit': {'committer': {'date': '2026-09-30T10:00:00Z'}}}]),
        ('GET', rf'/repos/{REPO}/community/profile'): (200, {'files': {'readme': {}, 'contributing': {}, 'code_of_conduct': {}}}),
        ('GET', rf'/repos/{REPO}/issues\?state=open&labels=good%20first%20issue&per_page=100&page=1'): (200, [issue(1), issue(2), issue(9, pr=True)]),
        ('GET', rf'/repos/{REPO}/issues\?state=open&labels=help%20wanted&per_page=100&page=1'): (200, [issue(2), issue(3)]),
    }
    routes.update(changes.pop('routes', {}))
    return routes


def run(routes=None, entry=None, **kw) -> checks.Report:
    entry = entry or {'category': 'library', 'tags': ['payments'], 'maintainer_pledge': True}
    return checks.run(REPO, entry, GitHub('t', FakeAPI(healthy() if routes is None else routes)), TODAY, **kw)


def status(report) -> dict:
    return {r.key: r.status for r in report.results}


class Checks(unittest.TestCase):
    def test_a_healthy_repository(self):
        report = run()
        self.assertEqual(status(report), {'licence': 'pass', 'activity': 'pass', 'docs': 'pass', 'issues': 'pass',
                                          'pledge': 'pass', 'topic': 'pass', 'relevance': 'review'})
        self.assertTrue(report.ok)
        self.assertEqual(report.summary(), '6 of 7 passed, 1 waits for a reviewer')
        self.assertIn('3 open issues', report.results[3].found, 'issues de-duplicated, pull requests left out')
        self.assertEqual(report.notes, [])

    def test_a_listed_project_passes_all_seven(self):
        report = run(reviewed=True)
        self.assertEqual(report.summary(), '7 of 7 passed')

    def test_licences(self):
        cases = [({'license': None}, 'library', 'fail', 'No licence'),
                 ({'license': {'spdx_id': 'NOASSERTION', 'name': 'Other'}}, 'library', 'fail', 'can’t tell'),
                 ({'license': {'spdx_id': 'CC-BY-NC-4.0', 'name': 'CC BY-NC 4.0'}}, 'library', 'fail', 'isn’t OSI-approved'),
                 ({'license': {'spdx_id': 'CC-BY-4.0', 'name': 'CC BY 4.0'}}, 'library', 'fail', 'isn’t OSI-approved'),
                 ({'license': {'spdx_id': 'CC-BY-4.0', 'name': 'CC BY 4.0'}}, 'dataset', 'pass', 'open data licence'),
                 ({'license': {'spdx_id': 'GPL-3.0', 'name': 'GNU GPL v3'}}, 'app', 'pass', 'approved by the OSI')]
        for repo, category, expected, words in cases:
            with self.subTest(repo=repo, category=category):
                result = run(healthy(repo=repo), {'category': category, 'tags': ['maps'], 'maintainer_pledge': True}).results[0]
                self.assertEqual(result.status, expected)
                self.assertIn(words, result.found)
                self.assertEqual(bool(result.fix), expected == 'fail', 'every failure says how to fix it')

    def test_activity(self):
        commit = lambda day: {('GET', rf'/repos/{REPO}/commits\?sha=main&per_page=1'): (200, [{'commit': {'committer': {'date': day}}}])}
        self.assertEqual(status(run(healthy(routes=commit('2026-07-08T00:00:00Z'))))['activity'], 'pass', '90 days ago')
        late = run(healthy(routes=commit('2026-07-07T00:00:00Z'))).results[1]
        self.assertEqual((late.status, '91 days ago' in late.found), ('fail', True))
        self.assertEqual(status(run(healthy(repo={'archived': True})))['activity'], 'fail')
        empty = {('GET', rf'/repos/{REPO}/commits\?sha=main&per_page=1'): (409, {'message': 'Git Repository is empty.'})}
        self.assertIn('No commits', run(healthy(routes=empty)).results[1].found)

    def test_docs_and_code_of_conduct(self):
        profile = {('GET', rf'/repos/{REPO}/community/profile'): (200, {'files': {'readme': {}, 'contributing': None}})}
        report = run(healthy(routes=profile))
        self.assertEqual((report.results[2].status, report.results[2].found), ('fail', 'No CONTRIBUTING file found.'))
        self.assertIn('CONTRIBUTING.md', report.results[2].fix)
        self.assertEqual(report.notes, ['A code of conduct is recommended, not required: none found.'])
        self.assertTrue(all(r.status != 'fail' or r.key == 'docs' for r in report.results))

    def test_beginner_issues(self):
        few = {('GET', rf'/repos/{REPO}/issues\?state=open&labels=help%20wanted&per_page=100&page=1'): (200, [])}
        result = run(healthy(routes=few)).results[3]
        self.assertEqual((result.status, result.found), ('fail', '2 open issues labelled `good first issue` or `help wanted`.'))
        self.assertEqual(run(healthy(repo={'has_issues': False})).results[3].found, 'Issues are turned off.')

    def test_topic_and_pledge(self):
        report = run(healthy(repo={'topics': ['algeria']}), {'category': 'tool', 'tags': ['maps'], 'maintainer_pledge': False})
        self.assertEqual((status(report)['topic'], status(report)['pledge']), ('fail', 'fail'))
        self.assertIn('About → Topics', report.results[5].fix)

    def test_a_missing_repository(self):
        report = run({})
        self.assertEqual(report.results[0].found, '`owner/name` isn’t a public repository on GitHub.')
        self.assertEqual(report.count('fail'), 6)
        self.assertFalse(report.ok)

    def test_github_trouble_is_not_a_failure_of_the_project(self):
        report = run({('GET', f'/repos/{REPO}'): (403, {'message': 'API rate limit exceeded'})})
        self.assertEqual(set(status(report).values()), {'error'})
        self.assertFalse(report.ok)
        self.assertIn('could not run', report.summary())

    def test_a_renamed_repository_is_noted(self):
        report = run(healthy(repo={'full_name': 'owner/new-name'}))
        self.assertIn('owner/new-name', report.notes[0])


BASE = 'projects:\n  - repository: other/listed\n    category: tool\n    tags: [maps]\n    maintainer_pledge: true\n    added: 2026-10-01\n'
NEW = BASE + '  - repository: owner/name\n    category: library\n    tags: [payments]\n    maintainer_pledge: true\n    added: 2026-10-06\n'


class PullRequests(unittest.TestCase):
    def test_only_new_or_changed_entries_are_checked(self):
        api = FakeAPI(healthy())
        outcome = submission.check_pull_request(NEW, BASE, GitHub('t', api), TODAY)
        self.assertTrue(outcome.ok)
        self.assertEqual([r.repository for r in outcome.reports], ['owner/name'])
        self.assertNotIn('other/listed', ' '.join(path for _, path, _ in api.calls))
        self.assertTrue(outcome.body.startswith(submission.MARKER))
        self.assertIn('### listing-check · all automatic checks passed', outcome.body)
        self.assertIn('#### `owner/name` · 6 of 7 passed, 1 waits for a reviewer', outcome.body)
        self.assertIn('| ✅ | `licence` | MIT License (`MIT`), approved by the OSI. |', outcome.body)

    def test_a_failure_says_how_to_fix_it(self):
        outcome = submission.check_pull_request(NEW, BASE, GitHub('t', FakeAPI(healthy(repo={'topics': []}))), TODAY)
        self.assertFalse(outcome.ok)
        self.assertIn('some checks need a fix', outcome.body)
        self.assertRegex(outcome.body, r'\| ❌ \| `topic` \| The topic `djazairdev` is missing\. \*\*Fix:\*\* Add `djazairdev`')

    def test_an_invalid_file_lists_its_problems(self):
        outcome = submission.check_pull_request(NEW.replace('category: library', 'category: framework'), BASE,
                                                GitHub('t', FakeAPI({})), TODAY)
        self.assertFalse(outcome.ok)
        self.assertIn('- line 8: projects[1] (owner/name).category: "framework" is not one of', outcome.body)

    def test_removing_or_reformatting(self):
        removed = submission.check_pull_request('projects: []\n', BASE, GitHub('t', FakeAPI({})), TODAY)
        self.assertTrue(removed.ok)
        self.assertIn('Removes `other/listed`', removed.body)
        same = submission.check_pull_request('# a comment\n' + BASE, BASE, GitHub('t', FakeAPI({})), TODAY)
        self.assertIn('No entry was added or changed', same.body)

    def test_submitted_text_is_inert(self):
        self.assertEqual(submission.safe('<img src=x> @org/team | a'), '&lt;img src=x&gt; @​org/team \\| a')


ISSUE = """### Repository

https://github.com/owner/name.git

### Category

library

### Tags

payments, arabic

### How does the project relate to Algeria?

We maintain it in Algiers.
It wraps a local payment gateway.

### Maintainer pledge

- [X] I maintain this repository, and its maintainers will reply to newcomer pull requests within 7 days.

### GitHub topic

- [X] The repository has the topic djazairdev (About → Topics on the repository page).
"""


class Issues(unittest.TestCase):
    def test_the_form_answers(self):
        answers = submission.parse_issue(ISSUE)
        self.assertEqual(answers['repository'], 'https://github.com/owner/name.git')
        self.assertEqual(answers['relevance'], 'We maintain it in Algiers.\nIt wraps a local payment gateway.')
        self.assertEqual(submission.parse_issue('### Repository\n\n_No response_\n')['repository'], '')
        for given in ('owner/name', 'https://github.com/owner/name', 'github.com/owner/name/', '`owner/name`', 'http://www.github.com/owner/name.git'):
            self.assertEqual(submission.normalise_repository(given), 'owner/name', given)

    def test_a_good_request(self):
        outcome = submission.check_issue(ISSUE, GitHub('t', FakeAPI(healthy())), TODAY)
        self.assertTrue(outcome.ok)
        self.assertIn('tags: [payments, arabic]', outcome.body, 'a ready-to-paste entry')
        self.assertIn('added: 2026-10-06', outcome.body)

    def test_an_unreadable_form(self):
        outcome = submission.check_issue(ISSUE.replace('\nlibrary\n', '\nframework\n'), GitHub('t', FakeAPI({})), TODAY)
        self.assertFalse(outcome.ok)
        self.assertIn('**Category**: "framework" is not one of', outcome.body)

    def test_an_unticked_pledge_fails_its_check(self):
        outcome = submission.check_issue(ISSUE.replace('- [X] I maintain', '- [ ] I maintain'), GitHub('t', FakeAPI(healthy())), TODAY)
        self.assertEqual(status(outcome.reports[0])['pledge'], 'fail')


class Comments(unittest.TestCase):
    def routes(self, comments):
        return {('GET', r'/repos/o/r/issues/5/comments\?per_page=100&page=1'): (200, comments),
                ('PATCH', r'/repos/o/r/issues/comments/\d+'): (200, {}), ('POST', r'/repos/o/r/issues/5/comments'): (201, {})}

    def test_created_once_then_updated(self):
        api = FakeAPI(self.routes([{'id': 1, 'body': f'{submission.MARKER} by a person', 'user': {'type': 'User'}}]))
        self.assertEqual(GitHub('t', api).upsert_comment('o/r', 5, submission.MARKER, 'new'), 'created')
        api = FakeAPI(self.routes([{'id': 7, 'body': f'{submission.MARKER} old', 'user': {'type': 'Bot'}}]))
        self.assertEqual(GitHub('t', api).upsert_comment('o/r', 5, submission.MARKER, 'new'), 'updated')
        self.assertEqual(api.calls[-1], ('PATCH', '/repos/o/r/issues/comments/7', {'body': 'new'}))


class Files(unittest.TestCase):
    def test_the_issue_form_matches_the_schema(self):
        form, _ = miniyaml.load((ROOT / '.github' / 'ISSUE_TEMPLATE' / 'hub-listing.yml').read_text())
        fields = {item.get('id'): item for item in form['body'] if item.get('id')}
        self.assertEqual({k: fields[k]['attributes']['label'] for k in submission.FORM}, submission.FORM)
        schema = json.loads((ROOT / 'hub' / 'projects.schema.json').read_text())
        self.assertEqual(fields['category']['attributes']['options'], schema['$defs']['project']['properties']['category']['enum'])
        self.assertEqual(fields['tags']['attributes']['options'], schema['$defs']['tag']['enum'])
        self.assertTrue(fields['tags']['attributes']['multiple'])
        self.assertEqual(form['labels'], ['hub listing'])
        self.assertTrue(all(item.get('validations', {}).get('required', True) or item['type'] == 'markdown' for item in form['body']))

    def test_the_workflow_never_runs_pull_request_code(self):
        text = (ROOT / '.github' / 'workflows' / 'hub-listing.yml').read_text()
        self.assertIn('pull_request_target', text)
        self.assertNotIn('ref: ${{ github.event.pull_request', text, 'checkout stays on the base branch')
        self.assertIn("contains(github.event.issue.labels.*.name, 'hub listing')", text)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not line.strip().startswith('run:'):
                continue
            indent = len(line) - len(line.lstrip())
            script = [line]
            for follow in lines[i + 1:]:
                if follow.strip() and len(follow) - len(follow.lstrip()) <= indent:
                    break
                script.append(follow)
            for part in script:
                self.assertNotIn('${{', part, f'values reach scripts through env, never inline: {part.strip()}')

    def test_the_pull_request_template_lists_the_seven_checks(self):
        text = (ROOT / '.github' / 'pull_request_template.md').read_text()
        for n, (_, title) in enumerate(checks.CHECKS, 1):
            self.assertIn(f'- [ ] {n}. ', text)
        self.assertIn('djazairdev', text)

    @unittest.skipUnless(shutil.which('ruby'), 'needs ruby for a full YAML parser')
    def test_miniyaml_agrees_with_a_full_yaml_parser(self):
        for path in [ROOT / 'projects.yml', ROOT / '.github' / 'ISSUE_TEMPLATE' / 'hub-listing.yml',
                     ROOT / '.github' / 'ISSUE_TEMPLATE' / 'config.yml', ROOT / '.github' / 'dependabot.yml']:
            ruby = subprocess.run(['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.generate(YAML.load_file(ARGV[0]))', str(path)],
                                  capture_output=True, text=True, check=True)
            self.assertEqual(miniyaml.load(path.read_text())[0], json.loads(ruby.stdout), path.name)


if __name__ == '__main__':
    unittest.main()
