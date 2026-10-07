"""Project ideas and the vote on them (ticket #39, PRD HUB-07), against a stand-in for GitHub's
GraphQL API: ideas ranked by votes, closed ones left out, adopted ones kept apart, each quarter's
count saved once when the round closes, no personal data, and an empty list while Discussions
is off."""
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
sys.path.insert(0, str(ROOT / 'site'))

from hub import __main__ as cli  # noqa: E402
from hub import ideas, miniyaml  # noqa: E402
from hub.github import GitHub, GitHubError  # noqa: E402

NOW = datetime(2026, 10, 7, 6, 41, tzinfo=timezone.utc)
PEOPLE = ('amina-dz', 'yacine', 'karim-b', 'sara', 'Amina Benali', 'amina@example.com')
URL = 'https://github.com/djazairdev/djazair.dev/discussions/'


def body(champion='@amina-dz', skills='Web front end, Data and open data', problem='Bus times are only on paper.'):
    """A discussion made with the form, as GitHub writes it."""
    return (f'### The problem\n\n{problem} Ask amina@example.com or @yacine.\n\n### Who benefits\n\nCommuters in Algiers\n\n'
            f'### Champion\n\n{champion}\n\n### Skills needed\n\n{skills}\n\n### Anything else\n\n_No response_')


def node(n, title, votes, created, closed=False, labels=(), comments=0, **form):
    return {'number': n, 'url': f'{URL}{n}', 'title': title, 'body': body(**form), 'createdAt': created, 'closed': closed,
            'upvoteCount': votes, 'comments': {'totalCount': comments}, 'labels': {'nodes': [{'name': l} for l in labels]},
            # Not asked for by the query; here to show nothing about the author is ever kept.
            'author': {'login': 'karim-b'}}


# Two pages of ideas, oldest first, as the query asks for them.
PAGES = [
    [node(3, 'Idea: Bus times for Algiers', 12, '2026-07-02T10:00:00Z', comments=4),
     node(4, 'Idea: Open data for the 69 wilayas, with @sara', 30, '2026-07-05T10:00:00Z', comments=9, champion='wanted',
          skills='Data and open data, Arabic, Tamazight or Darija language work'),
     node(5, 'Idea: A spam idea', 50, '2026-07-06T10:00:00Z', closed=True),
     node(6, 'Idea: School calendar API', 41, '2026-07-07T10:00:00Z', closed=True, labels=('adopted', 'backend'))],
    [node(7, 'فكرة: تطبيق لمواقيت الصيدليات المناوبة', 12, '2026-07-08T10:00:00Z', champion='_No response_', skills=''),
     node(8, 'Idea: Tamazight keyboards', 2, '2026-08-01T10:00:00Z', champion='**@yacine**', skills='Hardware, Mobile apps')],
]


class FakeGraphQL:
    """Answers the category query and the ideas query, a page at a time."""

    def __init__(self, enabled=True, category=True, pages=PAGES, status=200):
        self.enabled, self.category, self.pages, self.status = enabled, category, pages, status
        self.queries = []

    def __call__(self, method, url, body, headers):
        assert (method, url) == ('POST', 'https://api.github.com/graphql')
        assert headers.get('Authorization') == 'Bearer test-token'
        if self.status != 200:
            return self.status, {}, json.dumps({'message': 'Bad credentials'}).encode()
        q = json.loads(body)
        text, v = q['query'], q['variables']
        assert (v['owner'], v['name']) == ('djazairdev', 'djazair.dev')
        data = {'rateLimit': {'remaining': 4000}}
        if 'discussionCategory' in text:
            self.queries.append('category')
            assert v['slug'] == 'ideas'
            if not (self.enabled and self.category):
                return 200, {}, json.dumps({'data': {**data, 'repository': {'hasDiscussionsEnabled': self.enabled,
                                                                             'discussionCategory': None}},
                                            'errors': [{'type': 'NOT_FOUND', 'message': 'Could not resolve to a DiscussionCategory'}]}).encode()
            return 200, {}, json.dumps({'data': {**data, 'repository': {'hasDiscussionsEnabled': True,
                                                                         'discussionCategory': {'id': 'DIC_ideas'}}}}).encode()
        assert v['category'] == 'DIC_ideas'
        n = int(v['cursor']) if v.get('cursor') else 0
        self.queries.append(f'page {n}')
        page = {'pageInfo': {'hasNextPage': n + 1 < len(self.pages), 'endCursor': str(n + 1)}, 'nodes': self.pages[n]}
        return 200, {}, json.dumps({'data': {**data, 'repository': {'discussions': page}}}).encode()


class Ideas(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_ideas(self, now=NOW, **fake):
        self.api = FakeGraphQL(**fake)
        return ideas.run(self.tmp, GitHub(token='test-token', transport=self.api), now)

    def read(self) -> dict:
        return json.loads((self.tmp / 'ideas.json').read_text('utf-8'))

    def test_ranked_by_votes(self):
        line = self.run_ideas()
        doc = self.read()
        self.assertEqual(doc['category'], URL + 'categories/ideas')
        self.assertEqual(doc['generated_at'], '2026-10-07T06:41:00Z')
        # Open ideas by votes, the earlier idea first on a tie; the adopted one after them; the
        # closed one that wasn't adopted is gone.
        self.assertEqual([(i['number'], i['votes'], i['status']) for i in doc['ideas']],
                         [(4, 30, 'open'), (3, 12, 'open'), (7, 12, 'open'), (8, 2, 'open'), (6, 41, 'adopted')])
        first = doc['ideas'][0]
        self.assertEqual(first, {'number': 4, 'url': URL + '4', 'title': 'Open data for the 69 wilayas, with',
                                 'created_at': '2026-07-05T10:00:00Z', 'votes': 30, 'comments': 9, 'champion': False,
                                 'skills': ['data', 'language'], 'status': 'open'})
        by = {i['number']: i for i in doc['ideas']}
        self.assertEqual(by[7]['title'], 'تطبيق لمواقيت الصيدليات المناوبة')
        self.assertEqual((by[3]['champion'], by[7]['champion'], by[8]['champion']), (True, False, True))
        self.assertEqual(by[8]['skills'], ['mobile', 'hardware'], 'in the form’s order')
        self.assertEqual(by[7]['skills'], [])
        self.assertEqual(doc['rounds'], [])
        self.assertEqual(self.api.queries, ['category', 'page 0', 'page 1'])
        self.assertEqual(line, 'Hub ideas: 4 open ideas (56 votes), 1 adopted. GitHub API: 3 requests.')

    def test_no_personal_data(self):
        line = self.run_ideas()
        text = (self.tmp / 'ideas.json').read_text('utf-8')
        for who in PEOPLE:
            self.assertNotIn(who, text)
            self.assertNotIn(who, line)
        for words in ('Bus times are only on paper', 'Commuters', 'body', 'author'):
            self.assertNotIn(words, text, 'only titles and counts are kept')

    def test_an_empty_list_while_discussions_is_off(self):
        for fake in ({'enabled': False}, {'category': False}):
            with self.subTest(**fake):
                line = self.run_ideas(**fake)
                doc = self.read()
                self.assertIsNone(doc['category'])
                self.assertEqual((doc['ideas'], doc['rounds']), ([], []))
                self.assertEqual(self.api.queries, ['category'])
                self.assertIn('has Discussions off or no "ideas" category; wrote an empty list', line)

    def test_each_round_is_counted_once_when_its_quarter_ends(self):
        self.run_ideas(now=datetime(2026, 9, 30, 18, 41, tzinfo=timezone.utc))
        self.assertEqual(self.read()['rounds'], [], 'Q3 is still open')
        line = self.run_ideas(now=datetime(2026, 10, 1, 0, 41, tzinfo=timezone.utc))
        rounds = self.read()['rounds']
        self.assertEqual([r['quarter'] for r in rounds], ['2026-Q3'])
        self.assertEqual(rounds[0]['counted_at'], '2026-10-01T00:41:00Z')
        self.assertEqual([(r['number'], r['votes'], r['champion']) for r in rounds[0]['ranking']],
                         [(4, 30, False), (3, 12, True), (7, 12, False), (8, 2, True)], 'open ideas only')
        self.assertEqual(set(rounds[0]['ranking'][0]), {'number', 'url', 'title', 'votes', 'champion'})
        self.assertIn('Round 2026-Q3 counted: #4 leads with 30 votes.', line)
        line = self.run_ideas(now=datetime(2026, 10, 1, 6, 41, tzinfo=timezone.utc))
        self.assertEqual([r['quarter'] for r in self.read()['rounds']], ['2026-Q3'], 'counted once')
        self.assertNotIn('Round', line)
        self.run_ideas(now=datetime(2027, 1, 1, 0, 41, tzinfo=timezone.utc))
        self.assertEqual([r['quarter'] for r in self.read()['rounds']], ['2026-Q3', '2026-Q4'])

    def test_no_round_is_counted_before_there_was_a_category(self):
        self.run_ideas(now=datetime(2026, 9, 30, 18, 41, tzinfo=timezone.utc), enabled=False)
        self.run_ideas(now=datetime(2026, 10, 1, 0, 41, tzinfo=timezone.utc))
        self.assertEqual(self.read()['rounds'], [], 'Discussions was off during Q3: there was no vote')

    def test_a_round_keeps_ten_ideas(self):
        pages = [[node(n, f'Idea: number {n}', n, f'2026-07-{n:02d}T10:00:00Z') for n in range(1, 15)]]
        self.run_ideas(now=datetime(2026, 9, 30, 18, 41, tzinfo=timezone.utc), pages=pages)
        self.run_ideas(now=datetime(2026, 10, 1, 0, 41, tzinfo=timezone.utc), pages=pages)
        self.assertEqual([r['number'] for r in self.read()['rounds'][0]['ranking']], list(range(14, 4, -1)))

    def test_a_github_failure_writes_nothing(self):
        self.run_ideas()
        before = (self.tmp / 'ideas.json').read_text('utf-8')
        with self.assertRaisesRegex(GitHubError, 'needs a token'):
            self.run_ideas(now=datetime(2027, 1, 1, 0, 41, tzinfo=timezone.utc), status=401)
        self.assertEqual((self.tmp / 'ideas.json').read_text('utf-8'), before)

    def test_command_line(self):
        original = ideas.GitHub
        ideas.GitHub = lambda: GitHub(token='test-token', transport=FakeGraphQL())
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(['ideas', '--out', str(self.tmp)]), 0)
            ideas.GitHub = lambda: GitHub(token='test-token', transport=FakeGraphQL(status=401))
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(['ideas', '--out', str(self.tmp)]), 1)
        finally:
            ideas.GitHub = original
        self.assertIn('Hub ideas: 4 open ideas', out.getvalue())
        self.assertIn('Hub ideas stopped, nothing was written', err.getvalue())


class Reading(unittest.TestCase):
    def test_the_champion(self):
        for answer, found in (('@amina-dz', True), ('**@amina-dz**', True), ('Amina, with her students', True),
                              ('wanted', False), ('Wanted.', False), ('wanted, I can help later', False),
                              ('_No response_', False), ('', False), (None, False), ('مطلوب', False)):
            with self.subTest(answer=answer):
                self.assertIs(ideas.has_champion(answer), found)

    def test_the_title(self):
        self.assertEqual(ideas.title('Idea: Bus times'), 'Bus times')
        self.assertEqual(ideas.title('idea - Bus times'), 'Bus times')
        self.assertEqual(ideas.title('فكرة: مواقيت الحافلات'), 'مواقيت الحافلات')
        self.assertEqual(ideas.title('Ask @karim-b about bus times'), 'Ask about bus times')
        self.assertEqual(ideas.title('Use npx shadcn@latest'), 'Use npx shadcn@latest', 'not a mention')
        self.assertEqual(ideas.title('Idea: '), 'Idea:', 'nothing left: the title as it was')

    def test_the_form_fields(self):
        fields = ideas.form_fields(body())
        self.assertEqual(list(fields), ['the problem', 'who benefits', 'champion', 'skills needed', 'anything else'])
        self.assertEqual(fields['champion'], '@amina-dz')


class Form(unittest.TestCase):
    """The form, the reader and the page agree on the skills and the category."""

    def test_the_skills_are_the_forms_options(self):
        form, _ = miniyaml.load((ROOT / '.github' / 'DISCUSSION_TEMPLATE' / 'ideas.yml').read_text())
        options = next(b for b in form['body'] if b.get('id') == 'skills')['attributes']['options']
        self.assertEqual(options, list(ideas.SKILLS))
        labels = {b['id']: b['attributes']['label'].lower() for b in form['body'] if 'id' in b}
        self.assertEqual((labels['champion'], labels['skills']), ('champion', 'skills needed'), 'the answers keep() reads')
        from djsite.pages import hub
        self.assertEqual(hub.SKILLS, tuple(ideas.SKILLS.values()))
        for lang in ('en', 'ar'):
            strings = json.loads((ROOT / 'site' / 'i18n' / f'{lang}.json').read_text('utf-8'))['hub']['skill']
            self.assertEqual(set(strings), set(hub.SKILLS), lang)

    def test_the_category_and_its_addresses(self):
        from djsite import config
        self.assertEqual(f'{config.REPO}', ideas.REPO)
        self.assertTrue(config.IDEAS_URL.endswith(f'/discussions/categories/{ideas.CATEGORY}'))
        self.assertTrue(config.IDEAS_BY_VOTES_URL.startswith(config.IDEAS_URL + '?'))
        self.assertIn('sort%3Atop', config.IDEAS_BY_VOTES_URL)
        self.assertTrue(config.IDEAS_RESULTS_URL.endswith('/blob/hub-data/ideas.json'))


class Workflow(unittest.TestCase):
    def test_the_sync_reads_the_ideas(self):
        text = (ROOT / '.github' / 'workflows' / 'hub.yml').read_text()
        self.assertIn('  discussions: read ', text)
        step = text[text.index('- name: Read the ideas'):text.index('- name: Count contributors')]
        self.assertIn('python -m hub ideas', step)
        self.assertNotIn('continue-on-error', step, 'a failure opens the "Hub sync failed" issue')
        self.assertIn('hub-sync-errors.txt', step, 'and the issue quotes the error')
        self.assertLess(text.index('- name: Sync from GitHub'), text.index('- name: Read the ideas'))
        self.assertLess(text.index('- name: Read the ideas'), text.index('- name: Save the snapshot and deploy'))
        self.assertIn('"$RUNNER_TEMP/hub-ideas.txt")" .github/scripts/hub-publish.sh', text, 'its line goes in the snapshot’s commit')


if __name__ == '__main__':
    unittest.main()
