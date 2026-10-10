"""Index overview: six indicators with explanations, shared sources and downloads;
detailed comparisons and limitations have their own destinations."""
import io
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite import data  # noqa: E402
from djsite.build import build, csv_zip  # noqa: E402
from djsite.config import LANGS  # noqa: E402
from djsite.fmt import date_label, fint, quarter_label, rank_text  # noqa: E402
from htmlcheck import Doc  # noqa: E402

KEYS = ('accounts', 'pushes', 'repos', 'orgs', 'topics', 'permillion')


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class Overview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True, published=LANGS)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def cards(self, lang):
        return re.findall(r'<article class="card indicator reveal" id="ind-(\w+)"[^>]*>(.*?)</article>', self.html[lang], re.S)

    def test_six_indicators_each_with_explanation_and_quarter(self):
        for lang in ('en', 'ar'):
            cards = self.cards(lang)
            self.assertEqual([k for k, _ in cards], list(KEYS))
            for key, body in cards:
                with self.subTest(lang=lang, card=key):
                    self.assertIn(f'<span class="ind-q">{quarter_label(self.data.quarter, lang, "short")}</span>', body)
                    self.assertIn('class="ms"', body)                       # what it measures / doesn't
                    self.assertEqual(body.count('class="rank-row"'), 1 if key in ('topics', 'permillion') else 2)

    def test_shared_sources_and_downloads_are_present_once(self):
        folder = self.data.folder.name
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                html = self.html[lang]
                source = re.search(r'<p class="src-text">(.*?)</p>', html, re.S).group(1)
                self.assertIn('GitHub Innovation Graph', source)
                self.assertIn('CC0', source)
                self.assertIn('CC BY 4.0', source)
                self.assertIn(quarter_label(self.data.quarter, lang), text_of(source))
                self.assertIn(str(self.data.peers()['DZ']['population_year']), source)
                self.assertEqual(html.count('class="src-text"'), 1)
                for extension in ('csv', 'json'):
                    self.assertEqual(html.count(f'href="/data/{folder}/overview.{extension}"'), 1)

    def test_account_details_use_size_ranks_and_account_medians(self):
        row = self.data.overview()['accounts']
        for lang in ('en', 'ar'):
            body = dict(self.cards(lang))['accounts']
            ranks = re.findall(r'<span class="num rank-n[^\"]*"[^>]*>(.*?)</span>', body)
            self.assertEqual(ranks, [rank_text(row[g + '_rank'], row[g + '_ranked'], lang)
                                     for g in ('north_africa', 'africa')])
            for group in ('north_africa', 'core_peers', 'africa'):
                self.assertIn(fint(row[group + '_median'], lang), text_of(body))

    def test_page_head_names_the_quarter_and_release(self):
        doc = Doc(self.html['en'])
        self.assertEqual(len(doc.find('h1')), 1)
        text = text_of(self.html['en'])
        self.assertIn(f'Where Algeria stands, {quarter_label(self.data.quarter)}', text)
        self.assertIn(date_label(self.data.release_date, 'en', short=True), text)
        self.assertIn(date_label(self.data.release_date, 'ar'), text_of(self.html['ar']))

    def test_download_all_is_a_stable_zip_of_every_csv(self):
        url = f'/data/{self.data.folder.name}/{self.data.zip_name}'
        self.assertIn(f'href="{url}"', self.html['en'])
        blob = (self.dist / url.lstrip('/')).read_bytes()
        self.assertEqual(blob, csv_zip(self.data))
        names = zipfile.ZipFile(io.BytesIO(blob)).namelist()
        expected = sorted(n for n in self.data.files if n.endswith('.csv')) + ['README.md', 'manifest.json']
        self.assertEqual(names, [f'{self.data.folder.name}/{n}' for n in expected])
        for name in expected[:-2]:
            self.assertEqual(zipfile.ZipFile(io.BytesIO(blob)).read(f'{self.data.folder.name}/{name}'), self.data.read(name))

    def test_overview_links_to_details_without_repeating_their_sections(self):
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                doc = Doc(self.html[lang])
                self.assertFalse(doc.find('section', id='peers'))
                self.assertFalse(doc.find('section', id='limits'))
                links = {a['href'] for a in doc.anchors}
                self.assertIn(f'/{lang}/index/peers/', links)
                self.assertIn(f'/{lang}/index/trends/', links)
                self.assertIn(f'/{lang}/data/#limitations', links)
                self.assertNotIn('each compared with North Africa', text_of(self.html[lang]))

    def test_indicator_semantics_keep_names_charts_and_comparisons_connected(self):
        for lang in ('en', 'ar'):
            doc = Doc(self.html[lang])
            with self.subTest(lang=lang):
                self.assertEqual(len(doc.find('figure', class_='ind-chart')), 6)
                self.assertEqual(len(re.findall(r'<figure class="ind-chart"><figcaption>', self.html[lang])), 6)
                self.assertEqual(len(doc.find('dl', class_='meds')), 6)
                for key in KEYS:
                    card = doc.find('article', id=f'ind-{key}')[0]
                    self.assertEqual(card['aria-labelledby'], f'ind-{key}-h')
                    self.assertEqual(len(doc.find('h3', id=f'ind-{key}-h')), 1)


if __name__ == '__main__':
    unittest.main()
