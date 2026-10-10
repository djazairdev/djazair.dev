"""The built site: routes, languages, page shell and links (ticket #2)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite.build import build, output_path  # noqa: E402
from djsite.config import LANGS, PUBLISHED  # noqa: E402
from djsite.context import Ctx, Route, Site  # noqa: E402
from djsite.i18n import Catalog, MissingString  # noqa: E402
from djsite.pages import stub  # noqa: E402
from djsite.reports import all_reports  # noqa: E402
from djsite.routes import ROUTES  # noqa: E402
from htmlcheck import Doc, resolve  # noqa: E402

DIRS = {'en': 'ltr', 'ar': 'rtl'}
DRAFTS = {r.key for r in all_reports() if r.draft}


class BuiltSite(unittest.TestCase):
    """The site as it ships: Arabic shows the invitation to translate until it is reviewed (#61)."""
    PUBLISHED = PUBLISHED

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, quiet=True, published=cls.PUBLISHED)
        cls.docs = {}
        for path in cls.dist.rglob('*.html'):
            cls.docs[path] = Doc(path.read_text('utf-8'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def doc(self, lang, route):
        return self.docs[output_path(self.dist, lang, route.path)]

    def test_every_route_exists_in_both_languages(self):
        for route in ROUTES:
            for lang in LANGS:
                with self.subTest(route=route.key, lang=lang):
                    doc = self.doc(lang, route)
                    self.assertEqual(doc.html.get('lang'), lang)
                    self.assertEqual(doc.html.get('dir'), DIRS[lang])
                    self.assertTrue(doc.title.strip().endswith('djazair.dev') or doc.title.startswith('djazair.dev'))

    def test_hreflang_and_canonical(self):
        for route in ROUTES:
            for lang in LANGS:
                doc = self.doc(lang, route)
                alternates = {l['hreflang']: l['href'] for l in doc.links if l.get('rel') == 'alternate' and 'hreflang' in l}
                canonical = [l['href'] for l in doc.links if l.get('rel') == 'canonical']
                with self.subTest(route=route.key, lang=lang):
                    # Placeholders, drafts and invitations to translate stay out of search.
                    if (not route.indexed or route.render is stub.render or route.key in DRAFTS
                            or lang not in self.PUBLISHED):
                        self.assertEqual(alternates, {})
                        self.assertEqual(canonical, [])
                        continue
                    self.assertEqual(set(alternates), {*self.PUBLISHED, 'x-default'})
                    for other in self.PUBLISHED:
                        self.assertEqual(alternates[other], f'https://djazair.dev/{other}/{route.path}')
                    self.assertEqual(canonical, [f'https://djazair.dev/{lang}/{route.path}'])

    def test_skip_link_comes_first(self):
        for route in ROUTES:
            for lang in LANGS:
                doc = self.doc(lang, route)
                tag, attrs = doc.body_first
                with self.subTest(route=route.key, lang=lang):
                    self.assertEqual((tag, attrs.get('class'), attrs.get('href')), ('a', 'skip', '#main'))
                    self.assertIn('main', doc.ids)

    def test_language_switcher_keeps_the_page(self):
        for route in ROUTES:
            for lang in LANGS:
                doc = self.doc(lang, route)
                links = {a['data-lang']: a['href'] for a in doc.find('a') if 'data-lang' in a}
                with self.subTest(route=route.key, lang=lang):
                    for other in LANGS:
                        expected = f'/{other}/{route.path}' if route.switchable else f'/{other}/'
                        self.assertEqual(links[other], expected)

    def test_current_section_is_marked(self):
        doc = self.doc('en', self.site.routes['trends'])
        # The footer's current language can share the current page URL.
        nav = [a for a in doc.find('a') if a.get('aria-current') and 'data-lang' not in a]
        hrefs = {a['href']: a['aria-current'] for a in nav}
        self.assertEqual(hrefs.get('/en/index/'), 'true')            # main nav: Index section
        self.assertEqual(hrefs.get('/en/index/trends/'), 'page')     # sub-nav: this page

    def test_internal_links_resolve(self):
        # Links into a section of a page whose ticket isn't done yet can't be checked until it is,
        # nor those into a page that shows the invitation to translate: the header's and footer's.
        stubs = {output_path(self.dist, lang, r.path) for r in ROUTES if r.render is stub.render for lang in LANGS}
        stubs |= {p for lang in LANGS if lang not in self.PUBLISHED for p in (self.dist / lang).rglob('*.html')}
        for path, doc in self.docs.items():
            refs = [a.get('href', '') for a in doc.anchors] + [l.get('href', '') for l in doc.links]
            for href in refs:
                with self.subTest(page=str(path.relative_to(self.dist)), href=href):
                    self.assertNotIn(href, ('', '#'))
                    target = resolve(self.dist, href)
                    if target is not None:
                        self.assertTrue(target.exists(), f'{href} → {target} is missing')
                        fragment = href.partition('#')[2]
                        if fragment and target.suffix == '.html' and target not in stubs:
                            self.assertIn(fragment, self.docs[target].ids, f'{href}: no element with that id')
                    elif href.startswith('#'):
                        self.assertIn(href[1:], doc.ids)

    def test_root_page_redirects_to_the_published_languages(self):
        doc = self.docs[self.dist / 'index.html']
        hrefs = {a['href'] for a in doc.anchors}
        self.assertEqual(hrefs, {f'/{lang}/' for lang in self.PUBLISHED})
        self.assertEqual(doc.html.get('data-langs'), ' '.join(self.PUBLISHED))
        text = (self.dist / 'index.html').read_text('utf-8')
        self.assertIn("localStorage.getItem('djz-lang')", text)
        self.assertIn("location.replace('/'+l+'/'+location.search)", text, 'the query string is kept')
        refresh = [m for t, m in doc.elements if t == 'meta' and m.get('http-equiv') == 'refresh']
        # One language: everyone goes there, with or without JavaScript.
        self.assertEqual(refresh, [{'http-equiv': 'refresh', 'content': '0; url=/en/'}] if self.PUBLISHED == ('en',) else [])

    def test_404_pages_are_not_indexed(self):
        for path in (self.dist / '404.html', self.dist / 'en' / '404.html', self.dist / 'ar' / '404.html'):
            doc = self.docs[path]
            self.assertTrue(any(m for t, m in doc.elements if t == 'meta' and m.get('name') == 'robots'))

    def test_arabic_shows_the_draft_notice_until_reviewed(self):
        """On its pages once published; the invitation to translate has nothing to warn about."""
        doc = self.doc('ar', self.site.routes['home'])
        self.assertEqual(bool(doc.find('div', class_='notice')), 'ar' in self.PUBLISHED)
        self.assertFalse(self.doc('en', self.site.routes['home']).find('div', class_='notice'))


class BuiltSiteWithArabic(BuiltSite):
    """The same checks with the Arabic pages built, as they will be once reviewed."""
    PUBLISHED = LANGS


class Strings(unittest.TestCase):
    def make_catalog(self, en, ar):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        (folder / 'en.json').write_text(json.dumps(en), 'utf-8')
        (folder / 'ar.json').write_text(json.dumps(ar), 'utf-8')
        return Catalog(folder)

    def test_a_key_missing_from_english_fails(self):
        cat = self.make_catalog({'a': 'A'}, {'a': 'أ'})
        with self.assertRaises(MissingString):
            cat.lookup('en', 'b')

    def test_a_key_missing_from_arabic_falls_back_with_a_marker(self):
        cat = self.make_catalog({'a': 'A', 'b': 'Bee'}, {'_meta': {'reviewed': True}, 'a': 'أ'})
        site = Site(catalog=cat, routes={'home': Route('home', '', lambda c: None)})
        ctx = Ctx(site, 'ar', site.routes['home'])
        self.assertEqual(ctx.t('a'), 'أ')
        self.assertEqual(ctx.t('b'), '<span lang="en" dir="ltr" class="untranslated">Bee</span>')
        self.assertEqual(ctx.fallbacks, {'b'})
        self.assertEqual(cat.missing('ar'), ['b'])

    def test_strings_are_escaped_and_placeholders_filled(self):
        cat = self.make_catalog({'a': 'Fish & chips in {place}'}, {})
        site = Site(catalog=cat, routes={'home': Route('home', '', lambda c: None)})
        ctx = Ctx(site, 'en', site.routes['home'])
        self.assertEqual(ctx.t('a', place='<Oran>'), 'Fish &amp; chips in &lt;Oran&gt;')

    def test_shipped_catalogs_are_consistent(self):
        cat = Catalog(ROOT / 'site' / 'i18n')
        self.assertEqual(cat.stale('ar'), [], 'ar.json has keys that en.json no longer has')


if __name__ == '__main__':
    unittest.main()
