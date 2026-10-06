"""Index overview (ticket #19): six indicators with their explanations, source and quarter;
Algeria and six peers with the group medians; the CSV download."""
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
from djsite.fmt import date_label, fdec, fint, fpct, quarter_label  # noqa: E402
from djsite.scorecard import CORE_PEERS  # noqa: E402
from htmlcheck import Doc  # noqa: E402

KEYS = ('accounts', 'pushes', 'repos', 'orgs', 'topics', 'permillion')


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class Overview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def cards(self, lang):
        return re.findall(r'<article class="card indicator reveal" id="ind-(\w+)">(.*?)</article>', self.html[lang], re.S)

    def test_six_indicators_each_with_explanation_source_and_quarter(self):
        for lang in ('en', 'ar'):
            cards = self.cards(lang)
            self.assertEqual([k for k, _ in cards], list(KEYS))
            for key, body in cards:
                with self.subTest(lang=lang, card=key):
                    self.assertIn(f'<span class="ind-q">{quarter_label(self.data.quarter, lang, "short")}</span>', body)
                    self.assertIn('class="ms"', body)                       # what it measures / doesn't
                    self.assertRegex(body, r'<p class="ind-src">[^<]*GitHub Innovation Graph')
                    self.assertIn(quarter_label(self.data.quarter, lang), text_of(body))
                    self.assertEqual(body.count('class="rank-row"'), 1 if key in ('topics', 'permillion') else 2)

    def test_peers_table(self):
        peers, ov = self.data.peers(), self.data.overview()
        for lang in ('en', 'ar'):
            html = self.html[lang]
            table = re.search(r'<table class="dt" data-sortable>.*?</table>', html, re.S).group(0)
            body, foot = table.split('<tfoot>')
            self.assertEqual(re.findall(r'<tr[^>]*data-key="(\w+)"', body), ['DZ', *CORE_PEERS])
            self.assertEqual(re.findall(r'data-key="(median_\w+)"', foot),
                             ['median_north_africa', 'median_core_peers', 'median_africa'])
            with self.subTest(lang=lang):
                for code in ('DZ', *CORE_PEERS):
                    row = re.search(rf'data-key="{code}">(.*?)</tr>', body).group(1)
                    for value in (fint(peers[code]['accounts'], lang), fpct(peers[code]['yoy'], 1, lang),
                                  fdec(peers[code]['orgs_per_account'], 4, lang), fint(peers[code]['accounts_per_million'], lang)):
                        self.assertIn(value, row)
                self.assertIn(fpct(ov['yoy']['africa_median'], 1, lang), foot)
                self.assertIn('class="is-dz"', body)

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

    def test_limits_name_the_release(self):
        text = text_of(self.html['en'])
        self.assertIn('Four things these numbers can’t tell you', text)
        self.assertIn(f'{quarter_label(self.data.quarter)} data was published on {date_label(self.data.release_date)}.', text)


if __name__ == '__main__':
    unittest.main()
