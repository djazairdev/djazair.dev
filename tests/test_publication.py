"""Individual Arabic approvals never publish other pages or silently accept changed copy."""
import copy
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite.config import I18N_DIR, LANGS
from djsite.i18n import Catalog
from djsite.publication import REVIEW_FILE, digest, reviewed_pages


class HumanReview(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog(I18N_DIR)
        self.records = json.loads(REVIEW_FILE.read_text('utf-8'))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'reviews.json'

    def read(self, records=None, published=('en',)):
        self.path.write_text(json.dumps(self.records if records is None else records), 'utf-8')
        return reviewed_pages(self.catalog, published, self.path)

    def test_named_approval_matches_the_current_page_and_shared_labels(self):
        self.assertEqual(self.read(), {'minhajna': ('ar',)})
        self.assertEqual(self.records['minhajna']['ar']['strings_sha256'],
                         digest(self.catalog, 'minhajna', 'ar'))
        self.assertFalse(self.catalog.reviewed('ar'))

    def test_no_approval_publishes_nothing_extra(self):
        self.assertEqual(self.read({}), {})

    def test_changes_to_approved_copy_require_fresh_review(self):
        for key in ('minhajna.unofficial_notice', 'pages.minhajna.title', 'a11y.language'):
            catalog = copy.deepcopy(self.catalog)
            catalog.flat['ar'][key] += ' changed'
            self.path.write_text(json.dumps(self.records), 'utf-8')
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'changed since human review'):
                reviewed_pages(catalog, ('en',), self.path)

    def test_unrelated_arabic_changes_do_not_broaden_the_approval(self):
        self.catalog.flat['ar']['home.title'] = 'unreviewed home edit'
        self.assertEqual(self.read(), {'minhajna': ('ar',)})

    def test_missing_translation_cannot_be_approved_through_english_fallback(self):
        del self.catalog.flat['ar']['minhajna.unofficial_notice']
        with self.assertRaisesRegex(ValueError, 'untranslated'):
            digest(self.catalog, 'minhajna', 'ar')

    def test_malformed_or_unsigned_approvals_fail_closed(self):
        record = self.records['minhajna']['ar']
        invalid = [[], {'home': {'ar': record}}, {'minhajna': []},
                   {'minhajna': {'fr': record}}, {'minhajna': {'ar': None}}]
        for patch in ({'reviewer': ''}, {'reviewer': None}, {'date': 'invalid'}, {'date': None},
                      {'date': (date.today() + timedelta(days=1)).isoformat()},
                      {'strings_sha256': 'invalid'}):
            invalid.append({'minhajna': {'ar': {**record, **patch}}})
        for records in invalid:
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.read(records)

    def test_local_all_languages_preview_can_show_new_draft_copy(self):
        self.catalog.flat['ar']['minhajna.unofficial_notice'] += ' draft'
        self.assertEqual(self.read(published=LANGS), {})


if __name__ == '__main__':
    unittest.main()
