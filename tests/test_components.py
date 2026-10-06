"""Shared components (ticket #4)."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite import components as C  # noqa: E402
from djsite.build import build  # noqa: E402
from djsite.config import I18N_DIR  # noqa: E402
from djsite.context import Ctx, Route, Site  # noqa: E402
from djsite.i18n import Catalog  # noqa: E402
from djsite.markup import Markup, esc  # noqa: E402
from htmlcheck import Doc, resolve  # noqa: E402


def ctx(lang='en'):
    site = Site(catalog=Catalog(I18N_DIR), routes={'home': Route('home', '', lambda c: None)})
    return Ctx(site, lang, site.routes['home'])


class Components(unittest.TestCase):
    def test_figure_chips_are_isolated_left_to_right(self):
        self.assertIn('dir="ltr"', C.chip('−81%'))
        self.assertNotIn('dir="ltr"', C.chip(Markup('▲ 49,1% خلال عام')))

    def test_rank_row_labels_its_strip(self):
        html = C.rank_row(Markup('North Africa'), 3, 7, 'en')
        self.assertIn('aria-label="North Africa: 3rd of 7"', html)
        self.assertEqual(html.count('<rect'), 7)
        self.assertEqual(html.count('class="on"'), 1)
        ar = C.rank_row(Markup('<span lang="en" dir="ltr" class="untranslated">North Africa</span>'), 3, 7, 'ar')
        self.assertIn('aria-label="North Africa: 3 من 7"', ar)

    def test_issue_cards_escape_github_text_and_show_no_usernames(self):
        html = C.issue_card(ctx(), dict(url='https://github.com/o/r/issues/1', title='<script>alert(1)</script>',
                                        labels=['good first issue'], repo='o/r', language='Python', days=3, user='someone'))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('someone', html)
        self.assertIn('3 days ago', html)

    def test_ago_in_both_languages(self):
        self.assertEqual(C.ago(1, 'en'), '1 day ago')
        self.assertEqual(C.ago(22, 'en'), '3 weeks ago')
        self.assertEqual(C.ago(2, 'ar'), 'منذ يومين')
        self.assertEqual(C.ago(5, 'ar'), 'منذ 5 أيام')
        self.assertEqual(C.ago(14, 'ar'), 'منذ أسبوعين')

    def test_check_panel_counts_passes(self):
        html = C.check_panel(ctx(), [('licence', esc('A licence'), True), ('issues', esc('3 issues'), False)])
        self.assertIn('1 of 2 passed', html)
        self.assertIn('class="fail"', html)
        self.assertNotIn('all-ok', html)

    def test_tables_carry_sort_values(self):
        html = C.data_table(esc('Peers'), [(esc('Economy'), 'start'), (esc('Accounts'), 'end')],
                            [('DZ', [esc('Algeria'), (esc('586.990'), 586990)])], sortable=True, highlight='DZ',
                            sorted_by=(1, 'descending'))
        self.assertIn('data-sortable', html)
        self.assertIn('data-v="586990"', html)
        self.assertIn('class="is-dz"', html)
        self.assertIn('aria-sort="descending"', html)
        self.assertIn('<th scope="row"', html)


class DevPages(unittest.TestCase):
    def test_component_pages_build_with_valid_links(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        dist = tmp / 'dist'
        build(dist, dev=True, quiet=True)
        for lang in ('en', 'ar'):
            page = dist / lang / '_dev' / 'components' / 'index.html'
            doc = Doc(page.read_text('utf-8'))
            self.assertEqual(doc.html['dir'], 'rtl' if lang == 'ar' else 'ltr')
            for a in doc.anchors:
                target = resolve(dist, a.get('href', ''))
                if target is not None:
                    self.assertTrue(target.exists(), a['href'])


if __name__ == '__main__':
    unittest.main()
