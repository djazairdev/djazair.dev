"""The Hub page (ticket #27): the feed from the sync's snapshot, filters that work without
JavaScript showing the whole list, no personal data, health-checked projects, the empty
state, and the counted Arabic forms."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite.build import build  # noqa: E402
from djsite.config import LANGS  # noqa: E402
from djsite.fmt import plural  # noqa: E402

SYNCED = datetime(2026, 10, 6, 18, 41, tzinfo=timezone.utc)
DZ, PAY, GONE = 'djazairdev/djazair.dev', 'chargily/chargily-pay-python', 'someone/quiet-repo'


def stamp(days):
    return (SYNCED - timedelta(days=days, hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')


def issue(n, repo, title, labels, language, days, needs=''):
    return {'number': n, 'url': f'https://github.com/{repo}/issues/{n}', 'title': title, 'labels': labels,
            'created_at': stamp(days), 'needs': needs, 'repo': repo, 'language': language,
            # Not written by the sync; here to show the page never reads such fields.
            'user': {'login': 'amina-dz', 'avatar_url': 'https://avatars.githubusercontent.com/u/1'}, 'assignee': 'yacine'}


def project(repo, status='healthy', **kw):
    p = {'repository': repo, 'name': repo, 'url': f'https://github.com/{repo}', 'category': 'library', 'tags': ['payments'],
         'pledge': True, 'added': '2026-10-02', 'found': True, 'description': 'Accept Edahabia and CIB payments.',
         'language': 'Python', 'licence': 'MIT', 'topic': True, 'archived': False, 'last_commit': '2026-10-01T00:00:00Z',
         'issues': 2, 'flags': [], 'hide_on': None, 'status': status, 'shown': status != 'hidden'}
    p.update(kw)
    return p


def write_snapshot(folder: Path, projects, issues):
    folder.mkdir(parents=True, exist_ok=True)
    gen = SYNCED.strftime('%Y-%m-%dT%H:%M:%SZ')
    (folder / 'projects.json').write_text(json.dumps({'generated_at': gen, 'projects': projects}))
    (folder / 'issues.json').write_text(json.dumps({'generated_at': gen, 'issues': issues}))


ISSUES = [issue(51, DZ, 'Proofread the Arabic methodology page', ['good first issue', 'translation'], 'Python', 2, 'Fluent Arabic, Markdown'),
          issue(47, DZ, 'Test the year-on-year growth calculation', ['tests', 'Help Wanted'], 'Python', 8),
          issue(7, PAY, 'Document webhooks <in Arabic>', ['help wanted', 'good first issue', 'docs', 'a', 'b'], 'Python', 20),
          issue(3, PAY, 'Add type hints', ['good first issue'], None, 40)]
PROJECTS = [project(DZ, category='tool', tags=['open-data', 'arabic']),
            project(PAY, status='flagged', flags=[{'reason': 'inactive', 'since': '2026-10-01', 'found': 'x'}],
                    hide_on='2026-10-15'),
            project(GONE, status='hidden', flags=[{'reason': 'topic', 'since': '2026-10-06', 'found': 'x'}])]


class HubPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        write_snapshot(cls.tmp / 'hub', PROJECTS, ISSUES)
        cls.site = build(cls.tmp / 'dist', quiet=True, hub_dir=cls.tmp / 'hub')
        cls.html = {lang: (cls.tmp / 'dist' / lang / 'hub' / 'index.html').read_text('utf-8') for lang in LANGS}
        cls.home = (cls.tmp / 'dist' / 'en' / 'index.html').read_text('utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def cards(self, lang='en'):
        return re.findall(r'<a class="issue" href="([^"]+)"([^>]*)>', self.html[lang])

    def test_the_whole_feed_shows_without_javascript(self):
        for lang in LANGS:
            page = self.html[lang]
            with self.subTest(lang=lang):
                self.assertEqual([url for url, _ in self.cards(lang)], [i['url'] for i in ISSUES], 'newest first, each links to GitHub')
                self.assertNotRegex(page, r'<a class="issue"[^>]* hidden')
                self.assertIn('<div class="hub-tools" hidden>', page, 'the filters only appear with hub.js')
                self.assertIn('<fieldset class="seg hp-kind" hidden>', page)
                self.assertRegex(page, r'<script src="/assets/hub\.[0-9a-f]+\.js" defer>')
                for anchor in ('issues', 'contribute', 'projects', 'list'):
                    self.assertIn(f'id="{anchor}"', page)
                self.assertNotIn('class="untranslated"', page)

    def test_what_the_filters_need(self):
        attrs = dict(self.cards())
        self.assertIn('data-lang="Python" data-repo="djazairdev/djazair.dev" data-days="2" data-kind="gfi"', attrs[ISSUES[0]['url']])
        self.assertIn('data-kind="hw"', attrs[ISSUES[1]['url']], 'labels match whatever their case')
        self.assertIn('data-kind="gfi hw"', attrs[ISSUES[2]['url']])
        self.assertIn('data-lang="-"', attrs[ISSUES[3]['url']], 'no main language: Other')
        page = self.html['en']
        options = re.findall(r'name="(lang|repo|age)" value="([^"]*)"[^>]*>.*?<span class="hf-n num">(\d+)</span>', page)
        self.assertEqual(options, [('lang', '', '4'), ('lang', 'Python', '3'), ('lang', '-', '1'),
                                   ('repo', '', '4'), ('repo', PAY, '2'), ('repo', DZ, '2'),
                                   ('age', '', '4'), ('age', '7', '1'), ('age', '30', '3')])

    def test_cards_show_what_an_issue_needs_never_who_opened_it(self):
        page = self.html['en']
        self.assertIn('You’ll need: <span dir="auto">Fluent Arabic, Markdown</span>', page)
        self.assertIn('Document webhooks &lt;in Arabic&gt;', page, 'titles are escaped')
        for who in ('amina-dz', 'yacine', 'avatars.githubusercontent.com'):
            self.assertNotIn(who, page)
        card = re.search(rf'href="{ISSUES[2]["url"]}".*?class="ic-meta"', page, re.S).group(0)
        self.assertEqual(re.findall(r'<span class="lbl[^"]*" dir="auto">([^<]+)</span>', card),
                         ['good first issue', 'help wanted', 'docs', 'a'], 'beginner labels first, four at most')

    def test_projects_pass_their_health_checks(self):
        page = self.html['en']
        self.assertIn(f'href="https://github.com/{DZ}"', page)
        self.assertNotIn(GONE, page, 'a hidden project is not shown')
        pay = re.search(r'<li class="pj card">(?:(?!</li>\n</ul>).)*?chargily-pay-python.*?</p></div>\n</li>', page, re.S).group(0)
        self.assertIn('Health check: no commit in 90 days', pay)
        self.assertIn('?repo=chargily/chargily-pay-python#issues', pay)
        self.assertEqual(page.count('class="pj pj-wanted"'), 3)
        self.assertIn('Health check passing', page)
        self.assertIn('blob/hub-data/HEALTH.md', page)
        self.assertRegex(page, r'Projects</dt><dd><span class="num" dir="ltr">2</span>')

    def test_counts_in_both_languages(self):
        self.assertIn('<span class="hp-n" data-zero="{n} open issues" data-one="{n} open issue"', self.html['en'])
        self.assertIn('>4 open issues</span></p>', self.html['en'])
        self.assertIn('>4 مهام مفتوحة</span></p>', self.html['ar'])
        self.assertIn('data-two="مهمتان مفتوحتان"', self.html['ar'])
        self.assertEqual([plural(n, 'ar') for n in (0, 1, 2, 3, 11, 100)], ['zero', 'one', 'two', 'few', 'many', 'other'])

    def test_last_refreshed(self):
        self.assertIn('Last refreshed <time datetime="2026-10-06T18:41Z">6 Oct 2026, <span dir="ltr">18:41 UTC</span></time>.',
                      self.html['en'])
        self.assertIn('6 أكتوبر 2026، <span dir="ltr">18:41 UTC</span>', self.html['ar'])

    def test_home_reads_the_same_feed(self):
        teaser = re.search(r'id="hub-teaser".*?</section>', self.home, re.S).group(0)
        self.assertEqual(re.findall(r'<a class="issue" href="([^"]+)"', teaser), [i['url'] for i in ISSUES[:3]])


class EmptyHub(unittest.TestCase):
    def test_before_the_first_sync(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        build(tmp / 'dist', quiet=True, hub_dir=tmp / 'none')
        page = (tmp / 'dist' / 'en' / 'hub' / 'index.html').read_text('utf-8')
        self.assertIn('The first projects are being listed.', page)
        self.assertNotIn('class="hub-tools"', page)
        self.assertNotRegex(page, r'/assets/hub\.[0-9a-f]+\.js')
        self.assertEqual(page.count('class="pj pj-wanted"'), 3, 'the open slots still show')
        for anchor in ('issues', 'projects', 'list'):
            self.assertIn(f'id="{anchor}"', page)


class Ideas(unittest.TestCase):
    """Hub ideas (ticket #39): the Discussions form, and the Hub section once the switch is on."""

    def build(self, on: bool) -> dict:
        from djsite import config
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        was = config.HUB_IDEAS
        config.HUB_IDEAS = on
        try:
            build(tmp / 'dist', quiet=True, hub_dir=tmp / 'none')
        finally:
            config.HUB_IDEAS = was
        return {lang: (tmp / 'dist' / lang / 'hub' / 'index.html').read_text('utf-8') for lang in LANGS}

    def test_hidden_while_discussions_is_off(self):
        from djsite import config
        self.assertFalse(config.HUB_IDEAS, 'Discussions is off on djazairdev/djazair.dev: docs/hub-ideas.md')
        for page in self.build(False).values():
            self.assertNotIn('id="ideas"', page)
            self.assertNotIn('/discussions', page)

    def test_the_section_links_the_category_and_the_form(self):
        from djsite import config
        for lang, page in self.build(True).items():
            section = re.search(r'<section class="section section-m" id="ideas".*?</section>', page, re.S).group(0)
            self.assertIn(f'href="{config.NEW_IDEA_URL}"', section)
            self.assertIn(f'href="{config.IDEAS_URL}"', section)
            self.assertEqual(section.count('class="step card"'), 3)
            self.assertLess(page.index('id="projects"'), page.index('id="ideas"'))
            self.assertLess(page.index('id="ideas"'), page.index('id="list"'))

    def test_the_form_asks_what_the_prd_asks(self):
        """HUB-07: problem, who benefits, champion, skills needed; the file name is the category's slug."""
        sys.path.insert(0, str(ROOT))
        from hub import miniyaml
        from djsite import config
        path = ROOT / '.github' / 'DISCUSSION_TEMPLATE' / 'ideas.yml'
        form, _ = miniyaml.load(path.read_text())
        fields = {b['id']: b for b in form['body'] if 'id' in b}
        self.assertEqual(list(fields), ['problem', 'who', 'champion', 'skills', 'notes'])
        for key in ('problem', 'who', 'champion', 'skills'):
            self.assertTrue(fields[key]['validations']['required'], key)
        self.assertTrue(fields['skills']['attributes']['multiple'])
        self.assertTrue(config.NEW_IDEA_URL.endswith(f'category={path.stem}'))
        self.assertTrue(config.IDEAS_URL.endswith(f'/categories/{path.stem}'))


if __name__ == '__main__':
    unittest.main()
