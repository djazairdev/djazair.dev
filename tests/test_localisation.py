"""The Hub's localisation page (ticket #40, PRD HUB-08): the translation teams from
content/localisation.json in both languages, grouped by language, with the note that this work
doesn't show up in the Index (PRD §9.4); the list's checks; the weekly link check."""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(ROOT / 'site' / 'tools'))

import links  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.pages import localisation  # noqa: E402
from djsite.pages.localisation import LocalisationError, load  # noqa: E402

LIST = load()
LABELS = {'en': {'ar': 'Arabic team', 'kab': 'Kabyle team', 'zgh': 'Tifinagh team'},
          'ar': {'ar': 'فريق العربية', 'kab': 'فريق القبائلية', 'zgh': 'فريق تيفيناغ'}}


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class LocalisationPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.html = {lang: (cls.dist / lang / 'hub' / 'localisation' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def section(self, lang: str, id_: str) -> str:
        return re.search(rf'<section class="section section-\w" id="{id_}".*?</section>', self.html[lang], re.S).group(0)

    def test_every_team_link_in_its_language_group(self):
        for lang in ('en', 'ar'):
            groups = {key: self.section(lang, key) for key in ('arabic', 'tamazight')}
            for team in LIST['teams']:
                for code, url in team['links'].items():
                    with self.subTest(lang=lang, team=team['name'], code=code):
                        group = groups['arabic' if code == 'ar' else 'tamazight']
                        link = re.search(rf'<a class="pj-start lz-link" href="{re.escape(url)}" hreflang="{code}">(.*?)<span', group)
                        self.assertIsNotNone(link)
                        self.assertEqual(link.group(1), LABELS[lang][code])
            found = re.findall(r'class="pj-start lz-link" href="([^"]+)"', groups['arabic'] + groups['tamazight'])
            self.assertEqual(sorted(found), sorted(url for *_, url in localisation.links(LIST)), 'each link once')

    def test_cards_say_what_is_translated_in_both_languages(self):
        for lang in ('en', 'ar'):
            text = text_of(self.html[lang])
            for team in LIST['teams']:
                self.assertIn(team['name'], text)
                self.assertIn(text_of(team[lang]).strip(), text)
        self.assertIn('on Pontoon', text_of(self.section('en', 'arabic')))
        self.assertIn('على Pontoon', text_of(self.section('ar', 'arabic')))

    def test_the_index_doesnt_count_this_work(self):
        """PRD HUB-08: note that this work doesn't show up in the Index (§9.4)."""
        for lang, heading in (('en', 'This work doesn’t show up in the Index'), ('ar', 'هذا العمل لا يظهر في المؤشر')):
            note = re.search(r'<aside class="callout lz-note" role="note">.*?</aside>', self.html[lang], re.S).group(0)
            self.assertIn(heading, note)
            self.assertIn(f'href="/{lang}/data/#limitations"', note)
            methodology = (self.dist / lang / 'data' / 'index.html').read_text('utf-8')
            limits = re.search(r'id="limitations".*?</section>', methodology, re.S).group(0)
            self.assertIn('Crowdin', limits)

    def test_the_head_counts_what_the_list_holds(self):
        head = text_of(re.search(r'<section class="page-head.*?</section>', self.html['en'], re.S).group(0))
        self.assertIn(f'Projects {len(LIST["teams"])}', head)
        self.assertIn(f'Team links {len(localisation.links(LIST))}', head)
        self.assertRegex(head, r'Links checked \d{1,2} \w{3} 20\d\d')
        self.assertIn(f'<time datetime="{LIST["checked"]}">', self.html['ar'])

    def test_suggesting_a_team(self):
        for lang in ('en', 'ar'):
            suggest = self.section(lang, 'suggest')
            self.assertIn(f'href="{localisation.EDIT_URL}"', suggest)
            self.assertIn(f'href="{localisation.ISSUE_URL}"', suggest)
            self.assertIn('<code dir="ltr">content/localisation.json</code>', suggest)

    def test_reached_from_the_hub_the_footer_and_the_sitemap(self):
        sitemap = (self.dist / 'sitemap.xml').read_text()
        for lang in ('en', 'ar'):
            hub = (self.dist / lang / 'hub' / 'index.html').read_text('utf-8')
            teaser = re.search(r'<section class="section section-s" id="translate".*?</section>', hub, re.S).group(0)
            self.assertIn(f'href="/{lang}/hub/localisation/"', teaser)
            self.assertLess(hub.index('id="projects"'), hub.index('id="translate"'))
            self.assertLess(hub.index('id="translate"'), hub.index('id="list"'))
            self.assertIn(f'href="/{lang}/hub/localisation/"', re.search(r'<footer.*?</footer>', hub, re.S).group(0))
            self.assertIn(f'<loc>https://djazair.dev/{lang}/hub/localisation/</loc>', sitemap)
            self.assertRegex(self.html[lang], rf'<a href="/{lang}/hub/"[^>]*aria-current="true"')
        self.assertIn('<title>Translate software · Project Hub · djazair.dev</title>', self.html['en'])
        self.assertIn('<title>ترجمة البرمجيات · مركز المشاريع · djazair.dev</title>', self.html['ar'])


class TheList(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def write(self, change) -> Path:
        data = json.loads(json.dumps(LIST))
        change(data)
        path = self.tmp / 'localisation.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return path

    def test_the_list_is_sound(self):
        self.assertGreaterEqual(len(LIST['teams']), 5)
        for code in ('ar', 'kab'):
            self.assertTrue(any(code in t['links'] for t in LIST['teams']), code)
        hosts = {'pontoon': {'pontoon.mozilla.org'}, 'crowdin': {'crowdin.com'},
                 'weblate': {'hosted.weblate.org', 'translations.documentfoundation.org', 'translate.fedoraproject.org'}}
        for team in LIST['teams']:
            for url in team['links'].values():
                self.assertIn(url.split('/')[2], hosts[team['platform']], f'{team["name"]}: {url}')

    def test_mistakes_are_named(self):
        cases = [
            (lambda d: d['teams'].append(dict(d['teams'][0])), 'listed twice'),
            (lambda d: d['teams'][1].update(platform='transifex'), 'platform must be one of pontoon, weblate, crowdin'),
            (lambda d: d['teams'][2]['links'].update(fr='https://example.org/fr/'), 'links.fr isn’t a language'),
            (lambda d: d['teams'][3]['links'].update(ar='http://example.org/ar/'), 'links.ar must be an https address'),
            (lambda d: d['teams'][4].pop('ar'), r'teams\[4\] \(Mastodon\) has no ar'),
            (lambda d: d.update(teams=[]), 'lists no teams'),
        ]
        for change, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(LocalisationError, message):
                    load(self.write(change))
        with self.assertRaises(ValueError):
            load(self.write(lambda d: d.update(checked='7 October')))


class LinkCheck(unittest.TestCase):
    URL = 'https://crowdin.com/project/mastodon/kab'

    def test_verdicts(self):
        A = links.Answer
        cases = [
            (A(self.URL, 200, 'Translating Mastodon to Kabyle language - Crowdin'), 'ok'),
            (A(self.URL + '/', 200, 'Kabyle (kab)'), 'ok'),
            (A(self.URL, 404), 'broken'),
            (A(self.URL, 410), 'broken'),
            (A('https://accounts.crowdin.com/login', 200, 'Crowdin'), 'broken'),
            (A(self.URL, 200, 'Translating Mastodon to Arabic language - Crowdin'), 'broken'),
            (A(self.URL, 403), 'unchecked'),
            (A(self.URL, 429), 'unchecked'),
            (A(self.URL, 503), 'unchecked'),
            (A(self.URL, 0, error='timed out'), 'unchecked'),
        ]
        for answer, expected in cases:
            with self.subTest(answer=answer):
                self.assertEqual(links.verdict(self.URL, 'Kabyle', answer)[0], expected)

    def test_a_broken_link_fails_the_run_and_is_reported(self):
        def fake(url):
            if url.endswith('/obs-studio/kab'):
                return links.Answer(url, 404)
            if 'weblate' in url:
                return links.Answer(url, 429)
            if url.startswith('https://founders.coffee/'):
                return links.Answer(url, 200, 'Founders Coffee - Algeria')
            code = url.rstrip('/').rsplit('/', 1)[1]          # every team link ends with its language
            return links.Answer(url, 200, f'{links.LANGUAGES[code]} team')

        results = links.check(get=fake)
        verdicts = {(r.team, r.lang): r.verdict for r in results}
        self.assertEqual(verdicts[('OBS Studio', 'kab')], 'broken')
        self.assertEqual(verdicts[('Hosted Weblate', 'ar')], 'unchecked')
        self.assertEqual(verdicts[('Mozilla', 'ar')], 'ok')
        self.assertEqual(verdicts[('founders.coffee: host', 'ar')], 'ok')
        table = links.report(results)
        self.assertIn('1 of 23 links', table)
        self.assertIn('| [localisation](https://djazair.dev/en/hub/localisation/) | OBS Studio | `kab` | '
                      'https://crowdin.com/project/obs-studio/kab | not found (404) |', table)

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        original = links.fetch
        links.fetch = fake
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                self.assertEqual(links.main(['--report', str(tmp / 'links.md')]), 1)
                self.assertIn('OBS Studio', (tmp / 'links.md').read_text())
                links.fetch = lambda url: fake(url) if 'obs-studio/kab' not in url else links.Answer(url, 503)
                self.assertEqual(links.main(['--report', str(tmp / 'again.md')]), 0, 'not checked is not broken')
                self.assertFalse((tmp / 'again.md').exists())
        finally:
            links.fetch = original
        self.assertIn('23 links: 20 work, 1 broken, 2 not checked.', out.getvalue())
        self.assertIn('23 links: 20 work, 0 broken, 3 not checked.', out.getvalue())

    def test_the_title_is_read_from_the_page(self):
        self.assertEqual(links.title(b'<html><head><title>\n  Kabyle @ Hosted\n Weblate </title>'), 'Kabyle @ Hosted Weblate')
        self.assertEqual(links.title(b'<title>Arabic &amp; more</title>'), 'Arabic & more')
        self.assertEqual(links.title(b'no title here'), '')


if __name__ == '__main__':
    unittest.main()
