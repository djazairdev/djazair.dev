"""The Arabic review kit (ticket #33): strings out to a spreadsheet, corrections back in, with
the placeholders kept and the sign-off left to a person."""
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site' / 'tools'))

import strings  # noqa: E402

EN = {'_meta': {'language': 'English'}, 'nav': {'hub': 'Hub', 'data': 'Data'},
      'count': '{n} open issues', 'ind': {'does': ['Counts accounts', 'Includes bots']}}
AR = {'_meta': {'language': 'العربية', 'reviewed': False}, 'nav': {'hub': 'المركز', 'data': 'البيانات'},
      'count': '{n} مهام مفتوحة', 'ind': {'does': ['يحصي الحسابات', 'يشمل الروبوتات']}}


class ReviewKit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / 'en.json').write_text(json.dumps(EN, ensure_ascii=False), 'utf-8')
        (self.tmp / 'ar.json').write_text(json.dumps(AR, ensure_ascii=False), 'utf-8')
        self.sheet = self.tmp / 'review.csv'

    def table(self) -> list:
        with self.sheet.open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    def write(self, rows):
        with self.sheet.open('w', encoding='utf-8-sig', newline='') as f:
            out = csv.DictWriter(f, fieldnames=strings.HEADER)
            out.writeheader()
            out.writerows(rows)

    def ar(self) -> dict:
        return json.loads((self.tmp / 'ar.json').read_text('utf-8'))

    def test_export_lists_every_string(self):
        self.assertEqual(strings.export(self.sheet, self.tmp), 5)
        self.assertTrue(self.sheet.read_bytes().startswith(b'\xef\xbb\xbf'), 'a BOM, so spreadsheets read UTF-8')
        rows = self.table()
        self.assertEqual([r['Key'] for r in rows], ['nav.hub', 'nav.data', 'count', 'ind.does[0]', 'ind.does[1]'])
        self.assertEqual(rows[0]['Arabic now'], 'المركز')
        self.assertEqual(rows[3]['English'], 'Counts accounts')

    def test_import_applies_only_the_corrections(self):
        strings.export(self.sheet, self.tmp)
        rows = self.table()
        rows[0]['Corrected Arabic'] = 'مركز المشاريع'
        rows[4]['Corrected Arabic'] = 'يشمل الحسابات الآلية'
        self.write(rows)
        self.assertEqual(strings.apply(self.sheet, self.tmp), ['nav.hub', 'ind.does[1]'])
        ar = self.ar()
        self.assertEqual(ar['nav'], {'hub': 'مركز المشاريع', 'data': 'البيانات'})
        self.assertEqual(ar['ind']['does'], ['يحصي الحسابات', 'يشمل الحسابات الآلية'])
        self.assertIs(ar['_meta']['reviewed'], False, 'the sign-off is made by hand')

    def test_placeholders_must_stay(self):
        strings.export(self.sheet, self.tmp)
        rows = self.table()
        rows[2]['Corrected Arabic'] = 'مهام مفتوحة'
        rows[0]['Corrected Arabic'] = 'مركز المشاريع'
        self.write(rows)
        with self.assertRaises(SystemExit) as caught:
            strings.apply(self.sheet, self.tmp)
        self.assertIn("count must keep the placeholders ['n']", str(caught.exception))
        self.assertEqual(self.ar(), AR, 'nothing is changed when one correction is wrong')

    def test_unknown_keys_are_refused(self):
        self.write([{'Key': 'nav.blog', 'English': 'Blog', 'Arabic now': '', 'Corrected Arabic': 'المدونة', 'Notes': ''}])
        with self.assertRaises(SystemExit):
            strings.apply(self.sheet, self.tmp)

    def test_the_real_catalog_round_trips(self):
        sheet = self.tmp / 'real.csv'
        n = strings.export(sheet)
        self.assertGreater(n, 500)
        with sheet.open(encoding='utf-8-sig', newline='') as f:
            self.assertTrue(all(row['Arabic now'] for row in csv.DictReader(f)), 'every string has an Arabic draft')


if __name__ == '__main__':
    unittest.main()
