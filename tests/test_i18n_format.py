"""Interface strings and number formatting (ticket #5, PRD AC-IDX-6)."""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite.build import build  # noqa: E402
from djsite.config import I18N_DIR, LANGS  # noqa: E402
from djsite.fmt import (date_label, fcompact, fdec, fint, fpct, num, quarter_label,  # noqa: E402
                        rank_text)
from htmlcheck import Doc, Texts  # noqa: E402

MINUS = '−'


class Numbers(unittest.TestCase):
    def test_ac_idx_6_examples(self):
        self.assertEqual(fdec(586990.5, 1, 'en'), '586,990.5')
        self.assertEqual(fdec(586990.5, 1, 'ar'), '586.990,5')

    def test_integers(self):
        self.assertEqual(fint(586990, 'en'), '586,990')
        self.assertEqual(fint(586990, 'ar'), '586.990')
        self.assertEqual(fint(1794519, 'ar'), '1.794.519')
        self.assertEqual(fint(-193425, 'en'), MINUS + '193,425')
        self.assertEqual(fint(193425, 'en', sign=True), '+193,425')
        self.assertEqual(fint(0, 'en', sign=True), '0')

    def test_decimals(self):
        self.assertEqual(fdec(1.0630129985178622, 2, 'en'), '1.06')
        self.assertEqual(fdec(1.0630129985178622, 2, 'ar'), '1,06')
        self.assertEqual(fdec(0.03154057138963185, 4, 'ar'), '0,0315')
        self.assertEqual(fdec(-0.001, 2, 'en'), '0.00')   # no "−0.00"

    def test_signed_percentages(self):
        self.assertEqual(fpct(0.4914690076607422, 1, 'en'), '+49.1%')
        self.assertEqual(fpct(0.4914690076607422, 1, 'ar'), '+49,1%')
        self.assertEqual(fpct(-0.074, 1, 'en'), MINUS + '7.4%')
        self.assertEqual(fpct(-0.074, 1, 'ar'), MINUS + '7,4%')
        self.assertEqual(fpct(5.39, 0, 'en'), '+539%')
        self.assertEqual(fpct(0.0001, 1, 'en'), '0.0%')
        self.assertEqual(fpct(0.491, 1, 'en', sign=False), '49.1%')

    def test_axis_labels(self):
        self.assertEqual(fcompact(1_500_000, 'en'), '1.5M')
        self.assertEqual(fcompact(500_000, 'en'), '500k')
        self.assertEqual(fcompact(2_000_000, 'en'), '2M')
        self.assertEqual(fcompact(1_500_000, 'ar'), '1,5 مليون')
        self.assertEqual(fcompact(250, 'en'), '250')

    def test_ranks(self):
        self.assertEqual(rank_text(3, 7, 'en'), '3rd of 7')
        self.assertEqual(rank_text(19, 29, 'en'), '19th of 29')
        self.assertEqual(rank_text(22, 29, 'en'), '22nd of 29')
        self.assertEqual(rank_text(11, 29, 'en'), '11th of 29')
        self.assertEqual(rank_text(3, 7, 'ar'), '3 من 7')

    def test_quarters_and_dates(self):
        self.assertEqual(quarter_label('2026-Q1', 'en'), 'Q1 2026')
        self.assertEqual(quarter_label('2026-Q1', 'ar'), 'الربع الأول 2026')
        self.assertEqual(quarter_label('2026Q4', 'ar', 'short'), 'الربع 4 · 2026')
        self.assertEqual(quarter_label('2026 Q1', 'ar', 'axis'), '2026 Q1')
        self.assertEqual(date_label('2026-07-07', 'en'), '7 July 2026')
        self.assertEqual(date_label('2026-07-07', 'ar'), '7 جويلية 2026')
        self.assertEqual(date_label('2026-07-07', 'en', short=True), '7 Jul 2026')

    def test_figures_are_isolated(self):
        self.assertEqual(num('+49,1%'), '<span class="num" dir="ltr">+49,1%</span>')
        self.assertIn('dir="rtl"', num('3 من 7'))


class ArabicPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        build(cls.dist, dev=True, quiet=True, published=LANGS)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_signed_values_are_never_reordered(self):
        """Every '+49,1%' or '−7,4%' on an Arabic page sits inside a left-to-right element."""
        signed = re.compile(r'(?<![\w.,])[+−]\s?\d')
        checked = 0
        for page in (self.dist / 'ar').rglob('*.html'):
            for text, direction in Texts(page.read_text('utf-8')).items:
                if signed.search(text):
                    checked += 1
                    with self.subTest(page=str(page.relative_to(self.dist)), text=text.strip()):
                        self.assertEqual(direction, 'ltr')
        self.assertGreater(checked, 0, 'no signed values found to check')


class Fallback(unittest.TestCase):
    def test_missing_arabic_string_shows_english_with_a_notice(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        strings = tmp / 'i18n'
        strings.mkdir()
        shutil.copy2(I18N_DIR / 'en.json', strings / 'en.json')
        ar = json.loads((I18N_DIR / 'ar.json').read_text('utf-8'))
        del ar['nav']['hub']
        ar['_meta']['reviewed'] = True
        (strings / 'ar.json').write_text(json.dumps(ar, ensure_ascii=False), 'utf-8')
        build(tmp / 'dist', quiet=True, i18n_dir=strings, published=LANGS)

        page = (tmp / 'dist' / 'ar' / 'index.html').read_text('utf-8')
        self.assertIn('<span lang="en" dir="ltr" class="untranslated">Open source</span>', page)
        self.assertIn('بعض النصوص في هذه الصفحة لم تُترجم بعد', page)
        self.assertNotIn('النص العربي مسودة', page)   # reviewed, so no draft notice
        english = (tmp / 'dist' / 'en' / 'index.html').read_text('utf-8')
        self.assertFalse(Doc(english).find('div', class_='notice'))


if __name__ == '__main__':
    unittest.main()
