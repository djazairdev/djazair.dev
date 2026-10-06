"""Peers (ticket #21): Algeria, the six core peers and the medians, then rank tables for North
Africa and Africa from the derived ranks table, each sortable with an announced order."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import config  # noqa: E402
from djsite import data, scorecard  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.fmt import fdec, fint, fpct  # noqa: E402
from djsite.pages import peers  # noqa: E402
from htmlcheck import Doc  # noqa: E402

BASELINE = '2026-Q1'           # the quarter the hand-checked expectations below describe


def text_of(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class PeersPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, quiet=True)
        cls.data = data.load()
        cls.html = {lang: (cls.dist / lang / 'index' / 'peers' / 'index.html').read_text('utf-8') for lang in ('en', 'ar')}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def section(self, lang: str, id_: str) -> str:
        return re.search(rf'<section class="section section-s" id="{id_}".*?</section>', self.html[lang], re.S).group(0)

    def rows(self, lang: str, id_: str) -> dict:
        body = self.section(lang, id_).split('<tbody>')[1].split('</tbody>')[0]
        return dict(re.findall(r'<tr[^>]*data-key="(\w+)">(.*?)</tr>', body, re.S))

    def test_three_tables_each_sortable_with_an_announcement(self):
        for lang in ('en', 'ar'):
            with self.subTest(lang=lang):
                html = self.html[lang]
                self.assertEqual(html.count('<table class="dt" data-sortable>'), 3)
                self.assertEqual(len(re.findall(r'<p class="sr-only sort-status" role="status" data-desc="[^"]*\{col\}', html)), 3)
                self.assertEqual(html.count('aria-sort="descending"'), 2)        # the rank tables, by accounts

    def test_the_core_table_matches_the_overview(self):
        for lang in ('en', 'ar'):
            self.assertEqual(list(self.rows(lang, 'peers')), ['DZ', *scorecard.CORE_PEERS])
        self.assertNotIn('Open the peers page', self.section('en', 'peers'))     # no link to itself
        overview = (self.dist / 'en' / 'index' / 'index.html').read_text('utf-8')
        self.assertIn('Open the peers page', overview)

    def test_rank_tables_list_every_member_by_accounts(self):
        for group, id_ in (('north_africa', 'north-africa'), ('africa', 'africa')):
            members = peers.group_row(self.data, group)['economies'].split()
            by = peers.ranks(self.data, group)
            expected = sorted(members, key=lambda c: by[c]['accounts']['rank'])
            for lang in ('en', 'ar'):
                with self.subTest(group=group, lang=lang):
                    rows = self.rows(lang, id_)
                    self.assertEqual(list(rows), expected)
                    self.assertIn('class="is-dz"', self.section(lang, id_))

    def test_each_figure_carries_its_rank(self):
        by = peers.ranks(self.data, 'africa')
        dz = by['DZ']
        for lang in ('en', 'ar'):
            row = self.rows(lang, 'africa')['DZ']
            with self.subTest(lang=lang):
                self.assertIn(fint(dz['accounts']['value'], lang), row)
                self.assertIn(fpct(dz['yoy']['value'], 1, lang), row)
                self.assertIn(fdec(dz['orgs_per_account']['value'], 4, lang), row)
                for key in ('accounts', 'yoy', 'pushes_per_account', 'topics'):
                    r = dz[key]
                    self.assertIn(f'<span class="rk" aria-hidden="true">{r["rank"]}</span>', row)
                rank_sr = 'rank {} of {}' if lang == 'en' else 'المرتبة {} من {}'
                self.assertIn(rank_sr.format(dz['yoy']['rank'], dz['yoy']['ranked']), row)

    def test_medians_come_from_the_groups_table(self):
        for group, id_ in (('north_africa', 'north-africa'), ('africa', 'africa')):
            g = peers.group_row(self.data, group)
            for lang in ('en', 'ar'):
                foot = self.section(lang, id_).split('<tfoot>')[1]
                with self.subTest(group=group, lang=lang):
                    self.assertIn(fint(g['median_accounts'], lang), foot)
                    self.assertIn(fpct(g['median_yoy'], 1, lang), foot)
                    self.assertIn(f'({g["members"]})', text_of(foot))

    def test_baseline_ranks(self):
        """AC-IDX-2: in Q1 2026 Algeria's growth is 3rd of 7 in North Africa and 19th of 29 in Africa."""
        if self.data.quarter != BASELINE:
            self.skipTest(f'the expectations describe {BASELINE}')
        self.assertIn('rank 3 of 7', self.rows('en', 'north-africa')['DZ'])
        self.assertIn('rank 19 of 29', self.rows('en', 'africa')['DZ'])
        self.assertIn('Africa’s 29 largest developer communities', text_of(self.html['en']))

    def test_page_head(self):
        doc = Doc(self.html['en'])
        self.assertEqual(len(doc.find('h1')), 1)
        self.assertIn(f'/data/{self.data.folder.name}/ranks.csv', self.html['en'])
        self.assertIn('/en/methodology/#peer-groups', self.html['en'])

    def test_no_placeholders_left(self):
        for lang, html in self.html.items():
            with self.subTest(lang=lang):
                self.assertNotRegex(text_of(html), r'\{[a-z_]+\}')


class Names(unittest.TestCase):
    def test_every_african_economy_has_a_name_in_both_languages(self):
        for lang in ('en', 'ar'):
            names = json.loads((ROOT / 'site' / 'i18n' / f'{lang}.json').read_text('utf-8'))['economy']
            with self.subTest(lang=lang):
                self.assertEqual([c for c in config.AFRICA if not names.get(c)], [])

    def test_the_africa_minimum_matches_the_pipeline(self):
        self.assertEqual(scorecard.AFRICA_MIN_ACCOUNTS, config.AFRICA_MIN_ACCOUNTS)


if __name__ == '__main__':
    unittest.main()
