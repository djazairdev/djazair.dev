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



class Numbers(unittest.TestCase):
    """Contributor counts (ticket #41): shown only once the metrics job has written them."""
    METRICS = {'generated_at': '2026-10-07T06:41:00Z', 'projects': 2, 'pledge_days': 7, 'quarters': [
        {'quarter': '2026-Q1', 'complete': True, 'new_contributors': 1, 'opened': 3, 'answered': 3, 'within_pledge': 2,
         'waiting': 0, 'median_hours': 96.0},
        {'quarter': '2026-Q2', 'complete': True, 'new_contributors': 4, 'opened': 2, 'answered': 2, 'within_pledge': 2,
         'waiting': 0, 'median_hours': 26.5},
        {'quarter': '2026-Q3', 'complete': False, 'new_contributors': 0, 'opened': 0, 'answered': 0, 'within_pledge': 0,
         'waiting': 0, 'median_hours': None}]}

    def test_the_table_once_there_are_counts(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        write_snapshot(tmp / 'hub', PROJECTS, ISSUES)
        (tmp / 'hub' / 'metrics.json').write_text(json.dumps(self.METRICS))
        build(tmp / 'dist', quiet=True, hub_dir=tmp / 'hub')
        for lang, cells in (('en', ['1', '2 of 3', '4.0 days']), ('ar', ['1', '2 من 3', '4,0 يوم'])):
            page = (tmp / 'dist' / lang / 'hub' / 'index.html').read_text('utf-8')
            section = re.search(r'<section class="section section-m" id="numbers".*?</section>', page, re.S).group(0)
            rows = re.findall(r'<tr data-key="([^"]+)">(.*?)</tr>', section, re.S)
            self.assertEqual([k for k, _ in rows], ['2026-Q3', '2026-Q2', '2026-Q1'], 'newest first')
            first = [re.sub(r'<[^>]+>', '', c) for c in re.findall(r'<td[^>]*>(.*?)</td>', rows[2][1])]
            self.assertEqual(first, cells)
            self.assertIn('26' + ('.' if lang == 'en' else ',') + '5', rows[1][1], 'under two days, in hours')
            self.assertIn('hn-part', rows[0][1], 'the current quarter says it is not over')
            self.assertLess(page.index('id="projects"'), page.index('id="numbers"'))
        about = (tmp / 'dist' / 'en' / 'about' / 'index.html').read_text('utf-8')
        self.assertIn('usernames are read during the count and never kept', about, 'the privacy section says so')

    def test_no_section_without_counts(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        write_snapshot(tmp / 'hub', PROJECTS, ISSUES)
        build(tmp / 'dist', quiet=True, hub_dir=tmp / 'hub')
        page = (tmp / 'dist' / 'en' / 'hub' / 'index.html').read_text('utf-8')
        self.assertNotIn('id="numbers"', page)
        about = (tmp / 'dist' / 'en' / 'about' / 'index.html').read_text('utf-8')
        self.assertNotIn('during the count', about)


DISCUSSIONS = 'https://github.com/djazairdev/djazair.dev/discussions/'


def idea(n, title, votes, created, champion=True, skills=('data',), status='open', comments=3):
    return {'number': n, 'url': f'{DISCUSSIONS}{n}', 'title': title, 'created_at': created, 'votes': votes,
            'comments': comments, 'champion': champion, 'skills': list(skills), 'status': status}


# As hub/ideas.py writes them: open ideas by votes, then the adopted ones.
IDEAS = {'generated_at': '2026-10-17T06:41:00Z', 'category': f'{DISCUSSIONS}categories/ideas', 'rounds': [],
         'ideas': [idea(12, 'Open data for the 69 wilayas', 34, '2026-10-08T09:00:00Z', skills=('data', 'web')),
                   idea(15, 'Darija speech-to-text', 11, '2026-10-09T09:00:00Z', champion=False, skills=('ml', 'language')),
                   idea(9, 'Card payments <library>', 9, '2026-10-03T09:00:00Z', skills=()),
                   idea(21, 'تطبيق لمواقيت النقل', 2, '2026-10-12T09:00:00Z'),
                   idea(18, 'Tamazight keyboards', 1, '2026-10-10T09:00:00Z', comments=1),
                   idea(23, 'Pharmacy on duty', 0, '2026-10-14T09:00:00Z', comments=0),
                   idea(5, 'School calendar API', 41, '2026-07-02T09:00:00Z', status='adopted')]}


class Ideas(unittest.TestCase):
    """Hub ideas (ticket #39): the Discussions form, and the Hub section once the switch is on,
    with the round's top ideas from the Hub sync (hub/ideas.py)."""

    def build(self, on: bool, ideas=None) -> dict:
        from djsite import config
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        hub_dir = tmp / 'none'
        if ideas is not None:
            hub_dir = tmp / 'hub'
            hub_dir.mkdir()
            (hub_dir / 'ideas.json').write_text(json.dumps(ideas, ensure_ascii=False), 'utf-8')
        was = config.HUB_IDEAS
        config.HUB_IDEAS = on
        try:
            build(tmp / 'dist', quiet=True, hub_dir=hub_dir)
        finally:
            config.HUB_IDEAS = was
        self.about = {lang: (tmp / 'dist' / lang / 'about' / 'index.html').read_text('utf-8') for lang in LANGS}
        self.home = {lang: (tmp / 'dist' / lang / 'index.html').read_text('utf-8') for lang in LANGS}
        return {lang: (tmp / 'dist' / lang / 'hub' / 'index.html').read_text('utf-8') for lang in LANGS}

    @staticmethod
    def section(page: str) -> str:
        return re.search(r'<section class="section section-m" id="ideas".*?</section>', page, re.S).group(0)

    def test_hidden_while_discussions_is_off(self):
        for page in self.build(False, IDEAS).values():
            self.assertNotIn('id="ideas"', page)
            self.assertNotIn('/discussions', page)
        for about in self.about.values():
            self.assertNotIn('Discussions', about, 'the privacy section mentions ideas only once they show')
        for page in self.home.values():
            section = re.search(r'id="hub-teaser".*?</section>', page, re.S).group(0)
            self.assertNotIn('/discussions', section, 'unavailable participation paths do not link to GitHub')
            self.assertEqual(section.count('class="hub-path-status"'), 2)

    def test_the_section_links_the_category_and_the_form(self):
        from djsite import config
        for lang, page in self.build(True).items():
            section = self.section(page)
            self.assertIn(f'href="{config.NEW_IDEA_URL}"', section)
            self.assertIn(f'href="{config.IDEAS_BY_VOTES_URL}"', section)
            self.assertIn(f'href="{config.IDEAS_RESULTS_URL}"', section)
            self.assertEqual(section.count('class="step card"'), 3)
            self.assertNotIn('class="ib"', section, 'no round before the first sync')
            self.assertLess(page.index('id="projects"'), page.index('id="ideas"'))
            self.assertLess(page.index('id="ideas"'), page.index('id="list"'))
        self.assertIn('never who proposed or voted for them', self.about['en'], 'the privacy section says so')
        self.assertIn('من اقترحها أو صوّت لها', self.about['ar'])
        for lang, page in self.home.items():
            section = re.search(r'id="hub-teaser".*?</section>', page, re.S).group(0)
            self.assertEqual(section.count('class="card hub-path"'), 3)
            for url in (config.NEW_IDEA_URL, config.IDEAS_BY_VOTES_URL,
                        f'/{lang}/hub/?kind=gfi#issues', f'/{lang}/hub/#list'):
                self.assertIn(f'href="{url}"', section)
            self.assertNotIn('class="hub-path-status"', section)

    def test_the_round_and_its_top_ideas(self):
        from djsite import config
        pages = self.build(True, IDEAS)
        for lang, page in pages.items():
            section = self.section(page)
            rows = re.findall(r'<a class="idea" href="([^"]+)">(.*?)</a></li>', section, re.S)
            self.assertEqual([url for url, _ in rows], [f'{DISCUSSIONS}{n}' for n in (12, 15, 9, 21, 18)],
                             f'the {config.IDEAS_SHOWN} open ideas with the most votes, in order')
            self.assertEqual([re.search(r'class="idea-v num">(\d+)<', row).group(1) for _, row in rows], ['34', '11', '9', '2', '1'])
            self.assertIn('<time datetime="2026-12-31">', section, 'the round of the last sync closes with its quarter')
            self.assertIn('Card payments &lt;library&gt;', section)
            self.assertNotIn('<library>', section)
            self.assertLess(section.index('class="ib"'), section.index('class="steps-row"'))
            self.assertEqual(sum('badge-warn' in row for _, row in rows), 1, 'one idea wants a champion')
            adopted = re.search(r'<p class="ib-foot">.*?</p>', section, re.S).group(0)
            self.assertIn(f'href="{DISCUSSIONS}5"', adopted)
            self.assertNotIn(f'href="{DISCUSSIONS}5"', section.replace(adopted, ''), 'adopted ideas leave the vote')
        en, ar = self.section(pages['en']), self.section(pages['ar'])
        plain = {lang: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)) for lang, html in (('en', en), ('ar', ar))}
        for text in ('Q4 2026 round', 'Voting closes at the end of 31 December 2026, UTC.', 'Data and open data',
                     'Champion wanted', '3 comments', '6 ideas · 57 votes', 'Adopted so far: School calendar API.'):
            self.assertIn(text, plain['en'])
        self.assertRegex(plain['en'], r'(?<!\d)1 comment(?!s)')
        self.assertEqual(re.findall(r'class="idea-vl">([^<]+)<', en), ['votes', 'votes', 'votes', 'votes', 'vote'])
        # Arabic counts take their plural forms: 34 and 11 votes, then 9, 2 and 1.
        self.assertEqual(re.findall(r'class="idea-vl">([^<]+)<', ar), ['صوتًا', 'صوتًا', 'أصوات', 'صوتان', 'صوت'])
        for text in ('جولة الربع الرابع 2026', 'يُغلق التصويت في نهاية يوم 31 ديسمبر 2026', 'البيانات والبيانات المفتوحة',
                     'تبحث عن قائد', 'تعليق واحد', '3 تعليقات', '6 أفكار · 57 صوتًا', 'اعتُمدت حتى الآن: School calendar API.'):
            self.assertIn(text, plain['ar'])

    def test_the_rules_name_the_votes_needed(self):
        from djsite import config
        en, ar = (self.section(p) for p in self.build(True, IDEAS).values())
        n = config.IDEAS_MIN_VOTES
        self.assertIn(f'at least <span class="num" dir="ltr">{n}</span> votes', en)
        self.assertIn(f'<span class="num" dir="ltr">{n}</span> أصوات على الأقل', ar)

    def test_an_empty_round(self):
        pages = self.build(True, dict(IDEAS, ideas=[]))
        for lang, text in (('en', 'No ideas yet'), ('ar', 'لا أفكار بعد')):
            section = self.section(pages[lang])
            self.assertIn(text, section)
            self.assertNotIn('class="idea"', section)
            self.assertNotIn('class="ib-total"', section)

    def test_no_round_while_the_snapshot_says_discussions_is_off(self):
        for page in self.build(True, dict(IDEAS, category=None, ideas=[])).values():
            self.assertNotIn('class="ib"', self.section(page))

    def test_the_section_passes_the_accessibility_checks(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        import a11y
        for lang, page in self.build(True, IDEAS).items():
            self.assertEqual(a11y.check(page, lang), [], lang)

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
        intro = form['body'][0]['attributes']['value']
        self.assertIn(f'at least {config.IDEAS_MIN_VOTES} votes', intro, 'the form and the Hub give the same rule')
        self.assertTrue(config.NEW_IDEA_URL.endswith(f'category={path.stem}'))
        self.assertTrue(config.IDEAS_URL.endswith(f'/categories/{path.stem}'))


if __name__ == '__main__':
    unittest.main()
