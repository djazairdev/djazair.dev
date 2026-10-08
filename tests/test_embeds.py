"""Embeddable charts and share images (ticket #42, PRD IDX-18 and IDX-19): titled charts have
an embed page in each language; Index figures display Share and Embed, while Home omits its footer.
Dark and light embeds credit their source and link back; downloads carry the credit;
Home and the Index pages show the quarter's share image once it is drawn."""
import dataclasses
import html
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(ROOT / 'site' / 'tools'))

import share  # noqa: E402
from djsite import embeds, layout  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import LANGS, SITE_URL  # noqa: E402
from djsite.context import Ctx  # noqa: E402
from djsite.palette import THEMES  # noqa: E402
from djsite.pages import home  # noqa: E402

PAGES = {'home': '', 'overview': 'index/', 'peers': 'index/peers/', 'trends': 'index/trends/', 'languages': 'index/languages/',
         'topics': 'index/topics/', 'collaboration': 'index/collaboration/', 'rankings': 'index/rankings/'}


class Embeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, quiet=True)
        cls.html = {(key, lang): (cls.dist / lang / path / 'index.html').read_text('utf-8')
                    for key, path in PAGES.items() for lang in LANGS}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def panels(self, key: str, lang: str) -> list:
        """The chart ids with an Embed panel on a page."""
        return re.findall(r'data-copy-from="emb-([a-z0-9-]+)"', self.html[key, lang])

    def embed(self, lang: str, chart_id: str, theme: str = 'dark') -> str:
        return (self.dist / embeds.path(lang, chart_id, theme).lstrip('/') / 'index.html').read_text('utf-8')

    def test_every_titled_chart_on_the_index_and_home_can_be_embedded(self):
        found = {key: self.panels(key, 'en') for key in PAGES}
        self.assertEqual(found['home'], [], "Home's trend footer is omitted")
        self.assertEqual(len(found['trends']), 9, 'eight views and the quarterly growth bars')
        self.assertIn('trends-q-growth', found['trends'])
        for key in ('languages', 'topics', 'collaboration', 'rankings'):
            self.assertTrue(found[key], key)
        ids = sorted(i for ids in found.values() for i in ids)
        self.assertEqual(len(ids), len(set(ids)))
        for lang in LANGS:
            self.assertEqual(sorted(i for key in PAGES for i in self.panels(key, lang)), ids)
            folders = sorted(p.name for p in (self.dist / lang / 'embed').iterdir())
            self.assertEqual(folders, sorted(ids + ['home-yoy']), 'Home keeps its embed available without a panel')
            for chart_id in ids + ['home-yoy']:
                for theme in THEMES:
                    self.assertTrue((self.dist / embeds.path(lang, chart_id, theme).lstrip('/') / 'index.html').is_file())

    def test_reports_and_other_pages_keep_their_downloads_only(self):
        pages = [p for p in self.dist.rglob('index.html') if '/embed/' not in p.as_posix()]
        for page in pages:
            route = page.relative_to(self.dist).parent.as_posix()
            if re.fullmatch(r'(en|ar)(/index(/[a-z]+)?)?', route):
                continue
            with self.subTest(page=route):
                body = page.read_text('utf-8').split('</head>', 1)[1]          # the stylesheet in the head styles them
                self.assertNotIn('class="dl-menu emb-panel"', body)
                self.assertNotIn('data-share', body)
        self.assertTrue(any('/reports/' in p.as_posix() and 'class="dl"' in p.read_text('utf-8') for p in pages))
        self.assertFalse(any(p.name.startswith('report-') for p in (self.dist / 'en' / 'embed').iterdir()))

    def test_the_embed_page_credits_and_links_back(self):
        for lang in LANGS:
            for key in ('trends', 'languages', 'home'):
                for chart_id in (['home-yoy'] if key == 'home' else self.panels(key, lang)):
                    for theme in THEMES:
                        with self.subTest(lang=lang, chart=chart_id, theme=theme):
                            page = self.embed(lang, chart_id, theme)
                            self.assertIn(f'<html lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}">', page)
                            self.assertIn('<meta name="robots" content="noindex">', page)
                            self.assertIn('<base target="_blank">', page)
                            self.assertNotIn('<script', page)
                            self.assertEqual(page.count('<main>'), 1)
                            back = re.search(r'<link rel="canonical" href="([^"]+)">', page).group(1)
                            self.assertTrue(back.startswith(f'{SITE_URL}/{lang}/{PAGES[key]}#fig-'), back)
                            self.assertIn(f'id="{back.split("#")[1]}"', self.html[key, lang], 'the link lands on the chart')
                            credit = re.search(r'<p class="credit">(.*?)</p>', page, re.S).group(1)
                            self.assertIn('GitHub Innovation Graph', credit)
                            self.assertIn('djazair.dev', credit)
                            self.assertIn('(CC BY 4.0)', credit)
                            self.assertIn(f'<a href="{back}">', credit)
                            self.assertEqual(len(re.findall(r'<svg class="(wide|narrow)"', page)), 2)
                            self.assertIn(f'color-scheme: {theme}; --paper: {THEMES[theme]["paper"]};', page)
        self.assertIn('View on djazair.dev', self.embed('en', 'languages-top'))
        self.assertIn('اعرضه على djazair.dev', self.embed('ar', 'languages-top', 'light'))

    def test_the_code_to_paste(self):
        for lang in LANGS:
            for key in PAGES:
                for chart_id in self.panels(key, lang):
                    with self.subTest(lang=lang, chart=chart_id):
                        panel = re.search(rf'<details class="dl emb">(?:(?!</details>).)*data-copy-from="emb-{chart_id}".*?</details>',
                                          self.html[key, lang], re.S).group(0)
                        code = html.unescape(re.search(r'<textarea class="emb-code" id="emb-[^"]+" readonly rows="5" dir="ltr"[^>]*>(.*?)</textarea>',
                                                       panel, re.S).group(1))
                        frame = re.fullmatch(r'<iframe src="([^"]+)" title="([^"]+)" width="100%" height="(\d+)" '
                                             r'style="border: 0; max-width: 960px" loading="lazy"></iframe>', code)
                        self.assertIsNotNone(frame, code)
                        self.assertEqual(frame.group(1), f'{SITE_URL}/{lang}/embed/{chart_id}/')
                        self.assertTrue(frame.group(2).endswith(' (djazair.dev)'))
                        self.assertTrue(250 <= int(frame.group(3)) <= 800, frame.group(3))
                        self.assertIn(f'href="/{lang}/embed/{chart_id}/" target="_blank"', panel, 'a preview')
                        self.assertIn('<code dir="ltr">light/</code>', panel, 'without JavaScript, how to get the light page')
                        self.assertEqual(panel.count('type="radio"'), 2)

    def test_share_links_point_at_their_chart(self):
        for (key, lang), text in self.html.items():
            with self.subTest(page=key, lang=lang):
                targets = re.findall(r'<a class="act" href="#([^"]+)" data-share', text)
                self.assertEqual(len(targets), len(set(targets)))
                for target in targets:
                    self.assertIn(f'id="{target}"', text)
                expected = {'home': 0, 'trends': 2, 'overview': 0, 'peers': 0}.get(key)
                if expected is not None:
                    self.assertEqual(len(targets), expected, 'the eight Trends views share one link')

    def test_downloads_carry_the_credit(self):
        """The Trends views' SVG files once went out without it."""
        svgs = sorted((self.dist / 'charts').rglob('*.svg'))
        self.assertGreaterEqual(len(svgs), 80)
        for svg in svgs:
            with self.subTest(svg=svg.name):
                self.assertRegex(svg.read_text('utf-8'), r'djazair\.dev ‏?\(CC BY 4\.0\)')


class ShareImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.site = build(cls.tmp / 'dist', quiet=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def ctx(self, key: str, lang: str, release: dict) -> Ctx:
        site = dataclasses.replace(self.site, assets=dataclasses.replace(self.site.assets, release_share=release))
        return Ctx(site, lang, site.routes[key])

    def test_home_and_the_index_show_the_quarter_once_it_is_drawn(self):
        drawn = {'en': '/assets/share-q-en.png', 'ar': '/assets/share-q-ar.png'}
        for lang in LANGS:
            for key in ('home', 'overview', 'trends', 'rankings'):
                image, alt = layout.share_image(self.ctx(key, lang, drawn))
                self.assertEqual(image, drawn[lang])
                self.assertIn(home.figures(self.ctx(key, lang, drawn))[0][0], alt, 'the growth figure')
            for key in ('hub', 'about', 'methodology', 'reports'):
                self.assertEqual(layout.share_image(self.ctx(key, lang, drawn)), ('', self.site.catalog.lookup(lang, 'share.alt')[0]))
            self.assertEqual(layout.share_image(self.ctx('home', lang, {}))[0], '', "until it is drawn: the site's card")

    def test_the_release_card_says_what_home_says(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                ctx = share.release_context(lang)
                card = share.release_card(ctx)
                data = ctx.site.data
                self.assertIn(f'<html lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}">', card)
                self.assertIn(str(ctx.t('home.eyebrow', quarter=share.quarter_label(data.quarter, lang))), card)
                sep = f'<span class="ts">{home.GROUP[lang]}</span>'
                self.assertIn(sep.join(home._groups(int(data.overview()['accounts']['value']))), card)
                for value, label in home.figures(ctx):
                    self.assertIn(html.escape(value, quote=False), card)
                    self.assertIn(str(label), card)
                self.assertIn('<div class="map"><svg viewBox=', card)
        ar = share.release_card(share.release_context('ar'))
        self.assertRegex(ar, r'<b class="nums" dir="rtl">\d+ من \d+</b>', 'the rank reads right to left')
        self.assertIn('<b dir="ltr">▲ ', ar, 'figures stay left to right')


if __name__ == '__main__':
    unittest.main()
