"""The teacher download page: release facts, safe feedback and a quiet local-only page."""
import json
import gzip
import hashlib
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite.build import build
from djsite.config import LANGS
from djsite.context import Ctx
from djsite.pages import minhajna
from djsite.icons import android_mark
from htmlcheck import Doc
from a11y import Tree, check


class TeacherPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, quiet=True, published=LANGS, analytics='a' * 32, actions=True)
        cls.html = {lang: (cls.dist / lang / 'minhajna/index.html').read_text('utf-8') for lang in LANGS}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_release_links_and_checksums_are_the_published_preview(self):
        data = minhajna.load_release()
        self.assertEqual(data['version'], '0.1.0')
        self.assertEqual(data['published'], '2026-10-18')
        self.assertEqual(data['apk_bytes'], 34454115)
        self.assertEqual(data['minimum_android'], 8)
        for html in self.html.values():
            self.assertIn('https://github.com/djazairdev/minhajna/releases/download/app-v0.1.0/minhajna-0.1.0.apk', html)
            self.assertIn('334f2b0b991f9d25b13438a1b6b2ba119e0f90f34056c6bbb06c3ddb413036ba', html)
            self.assertIn('de2a5a7839bb88733456078bb937179f43ff99004d2408cb965093aa0aed6a5b', html)

    def test_feedback_is_facebook_then_email_then_github(self):
        for html in self.html.values():
            section = html.split('id="feedback"', 1)[1].split('</section>', 1)[0]
            links = [a['href'] for a in Doc(section).anchors]
            self.assertEqual(links[:3], [
                'https://www.facebook.com/djazairdev',
                'mailto:contact@djazair.dev?subject=Minhajna%20feedback',
                'https://github.com/djazairdev/minhajna/issues/new?template=bug.yml',
            ])
            self.assertIn('mailto:contact@djazair.dev?subject=Minhajna%20private%20report', section)

    def test_banner_explains_the_project_has_not_been_officially_adopted(self):
        expected = {
            'ar': 'منهاجنا مشروع مستقل، وليس تطبيقًا رسميًا معتمدًا من الدولة الجزائرية أو وزارة التربية الوطنية.',
            'en': 'Minhajna is an independent project. It has not been officially adopted by the Algerian state or the Ministry of National Education.',
        }
        for lang, html in self.html.items():
            banner = html.split('<div class="notice"', 1)[1].split('<main ', 1)[0]
            self.assertIn('role="note"', banner)
            self.assertIn(expected[lang], banner)
            ctx = Ctx(self.site, lang, self.site.routes['minhajna'])
            self.assertNotIn(str(ctx.t('notice.draft')), html)
        other_page = (self.dist / 'ar/index.html').read_text('utf-8')
        self.assertIn('النص العربي مسودة', other_page)
        self.assertNotIn(expected['ar'], other_page)

    def test_download_area_is_rendered_once_for_all_screen_sizes(self):
        download = 'https://github.com/djazairdev/minhajna/releases/download/app-v0.1.0/minhajna-0.1.0.apk'
        for html in self.html.values():
            doc = Doc(html)
            self.assertEqual(len(doc.find('div', class_='mh-download')), 1)
            self.assertEqual(len(doc.find('div', class_='mh-download-actions')), 1)
            self.assertEqual(sum(a.get('href') == download for a in doc.anchors), 1)
            self.assertNotIn('mh-mobile-download', html)

    def test_android_download_has_the_robot_and_ios_is_a_disabled_button(self):
        for lang, html in self.html.items():
            doc = Doc(html)
            self.assertEqual(len(doc.find('svg', class_='android-mark')), 1)
            self.assertEqual(len(doc.find('svg', class_='ios-phone')), 1)
            buttons = doc.find('button', class_='mh-ios')
            self.assertEqual(len(buttons), 1)
            for button in buttons:
                self.assertIn('disabled', button)
                self.assertEqual(button.get('aria-disabled'), 'true')
                self.assertEqual(button.get('type'), 'button')
                self.assertNotIn('href', button)
                self.assertNotIn('onclick', button)
            label = Ctx(self.site, lang, self.site.routes['minhajna']).t('minhajna.ios_soon')
            self.assertIn(str(label), html)
            self.assertEqual(doc.find('a', class_='mh-ios'), [])
            self.assertIn('https://creativecommons.org/licenses/by/3.0/', html)

    def test_robot_preserves_the_official_svg_geometry_and_has_unique_ids(self):
        source = ET.parse(ROOT / 'site/static/brand/android-head-flat.svg').getroot()
        rendered = ET.fromstring(android_mark('test'))
        paths = lambda root: [node.attrib for node in root.iter() if node.tag.endswith('}path')]
        self.assertEqual(paths(source), paths(rendered))
        self.assertEqual(rendered.get('viewBox'), '0 0 152 89')
        self.assertEqual(rendered.get('aria-hidden'), 'true')
        self.assertEqual(rendered.get('focusable'), 'false')
        marks = str(android_mark('mobile')) + str(android_mark('card'))
        self.assertEqual(len(Doc(marks).ids), 2)

    def test_no_tracking_scripts_embeds_or_forms_even_when_the_site_enables_them(self):
        for html in self.html.values():
            doc = Doc(html)
            self.assertEqual([a for a in doc.find('script') if a.get('src')], [])
            self.assertEqual(doc.find('iframe'), [])
            self.assertEqual(doc.find('form'), [])
            self.assertNotIn('data-action', html)
            self.assertNotIn('cloudflareinsights', html)

    def test_original_logo_is_used_in_the_header_and_single_download_card(self):
        originals = {
            'minhajna-icon.svg': 'b658b4eb1c72dce0d1aebc147716a1a90db7298bbc12316c4a0e323f40b9f538',
            'minhajna-wordmark-chalk.svg': 'ec034ce1b56af37cd332eac8d705239c09ff449a5c541fb4da919fe5f60e788c',
        }
        for name, expected in originals.items():
            source = (ROOT / 'site/static/minhajna' / name).read_bytes()
            self.assertEqual(hashlib.sha256(source).hexdigest(), expected)
            self.assertEqual((self.dist / self.site.assets.minhajna[name].lstrip('/')).read_bytes(), source)
        for html in self.html.values():
            doc = Doc(html)
            for cls in ('mh-app-icon', 'mh-wordmark'):
                images = doc.find('img', class_=cls)
                self.assertEqual(len(images), 2)
                self.assertTrue(all(img['alt'] == '' for img in images))
            self.assertEqual(len(doc.find('span', class_='mh-lockup')), 2)
            self.assertTrue(doc.find('a', class_='mh-brand')[0].get('aria-label'))

    def test_three_real_screenshots_have_light_previews_and_native_enlargement(self):
        for lang, html in self.html.items():
            section = html.split('id="screenshots"', 1)[1].split('</section>', 1)[0]
            doc = Doc(section)
            images = doc.find('img')
            links = doc.find('a', class_='mh-screen-link')
            self.assertEqual(len(images), 3)
            self.assertEqual(len(links), 3)
            self.assertEqual(len(doc.find('figcaption')), 3)
            for name, img, link in zip(('today', 'week', 'roll'), images, links):
                self.assertEqual(img['src'], self.site.assets.minhajna[f'{name}-0.1.0-thumb.jpg'])
                self.assertEqual(img.get('loading'), 'lazy')
                self.assertEqual(img.get('decoding'), 'async')
                self.assertEqual((img.get('width'), img.get('height')), ('270', '600'))
                self.assertTrue(img.get('alt'))
                self.assertTrue(link.get('aria-label'))
                self.assertNotIn('target', link)
                full = self.dist / link['href'].lstrip('/')
                data = full.read_bytes()
                self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                self.assertEqual(struct.unpack('>II', data[16:24]), (720, 1600))
                expected = {
                    'today': '84393e28130b5a17b9bec97cc5392623b93512284379b1730681f8de915a7ce5',
                    'week': '9627a76405b6f8cf81ab305ac4795e34103b05711510c201bfe601753230a1b3',
                    'roll': '591fb82f1be2f92fa717172996c1438aacc2a77918eff1f34a5117afaef1d726',
                }
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected[name])
            self.assertIn('0.1.0', section)
            self.assertNotIn('docs/design/screens', html)
            self.assertIn('https://creativecommons.org/licenses/by-sa/4.0/', html)

    def test_initial_page_images_stay_light_full_size_images_are_on_demand(self):
        for html in self.html.values():
            doc = Doc(html)
            paths = {img['src'] for img in doc.find('img')}
            total = len(gzip.compress(html.encode(), 6))
            total += sum(len(gzip.compress((self.dist / path.lstrip('/')).read_bytes(), 6)) for path in paths)
            self.assertLessEqual(total, 100 * 1024)
            self.assertTrue(all(path.startswith('/assets/minhajna-') for path in paths))

    def test_update_guidance_is_translated_and_offers_help_without_uninstalling(self):
        for lang, html in self.html.items():
            ctx = Ctx(self.site, lang, self.site.routes['minhajna'])
            self.assertIn('id="update"', html)
            section = html.split('id="update"', 1)[1].split('</section>', 1)[0]
            self.assertIn(str(ctx.t('minhajna.update.lede')), section)
            self.assertIn(str(ctx.t('minhajna.update.warning')), section)
            self.assertIn(str(ctx.t('minhajna.update.help')), section)
            self.assertIn('href="#feedback"', section)
            self.assertEqual(len(Doc(section).find('li')), 2)
            self.assertTrue(any(a.get('href') == '#update' for a in Doc(html).anchors))

    def test_download_card_keeps_only_teacher_facing_information(self):
        for lang, html in self.html.items():
            ctx = Ctx(self.site, lang, self.site.routes['minhajna'])
            expected = 'Free download' if lang == 'en' else 'تنزيل مجاني'
            self.assertEqual(str(ctx.t('minhajna.download_note')), expected)
            card = html.split('<div class="mh-download">', 1)[1].split('</section>', 1)[0]
            text = Tree(card).root.text()
            for jargon in ('APK', 'GitHub', 'ARM', 'account', 'حساب'):
                self.assertNotIn(jargon, text)

    def test_education_system_vision_is_separate_from_the_current_preview(self):
        expected = {
            'ar': ('لبناء نظام رقمي متكامل', 'تدريجيًا', 'الكراس اليومي', 'دفتر النصوص', 'كراس المناداة'),
            'en': ('building an integrated digital system', 'gradually', 'daily journals', 'lesson logs', 'attendance registers'),
        }
        for lang, html in self.html.items():
            hero = html.split('<section class="mh-hero"', 1)[1].split('</section>', 1)[0]
            text = Tree(hero).root.text()
            for phrase in expected[lang]:
                self.assertIn(phrase, text)
            self.assertIn('mh-mission', hero)
            self.assertIn('mh-caution', hero)
            self.assertIn('id="limits"', html)
            self.assertIn('id="features"', html)

    def test_arabic_uses_concrete_school_tasks_and_explains_released_labels(self):
        html = self.html['ar']
        features = html.split('id="features"', 1)[1].split('</section>', 1)[0]
        for phrase in ('إدخال جدول حصصك الأسبوعي', 'الأفواج الفرعية', 'كل أسبوعين',
                       'تسجيل الحضور والغيابات والتأخرات', 'الدروس المنجزة في كل قسم'):
            self.assertIn(phrase, features)
        for jargon in ('تنظيم استعمال الزمن', 'الأسابيع المتناوبة', 'تقدّم الأقسام'):
            self.assertNotIn(jargon, features)
        exercise = html.split('id="try"', 1)[1].split('</section>', 1)[0]
        for phrase in ('الطور التعليمي', 'لإدخال عناوين الدروس يدويًا', 'دون حزمة: كتابة العناصر',
                       'تأكيد الحصة', 'مخطط الجلوس', 'أماكن جلوس التلاميذ'):
            self.assertIn(phrase, exercise)
        for jargon in ('مدخلاتك', 'طراز الهاتف'):
            self.assertNotIn(jargon, Tree(html).root.text())

    def test_technical_checks_and_credits_are_collapsed_not_removed(self):
        for html in self.html.values():
            verify = html.split('id="verify"', 1)[1].split('</section>', 1)[0]
            details = Doc(verify).find('details')
            self.assertEqual(len(details), 1)
            self.assertNotIn('open', details[0])
            self.assertIn('334f2b0b991f9d25b13438a1b6b2ba119e0f90f34056c6bbb06c3ddb413036ba', verify)
            credits = Doc(html).find('details', class_='mh-credits')
            self.assertEqual(len(credits), 1)
            self.assertNotIn('open', credits[0])

    def test_both_languages_are_accessible_and_the_switch_keeps_the_page(self):
        for lang, html in self.html.items():
            self.assertEqual(check(html, lang), [], lang)
            doc = Doc(html)
            self.assertEqual(doc.html['dir'], 'rtl' if lang == 'ar' else 'ltr')
            self.assertEqual({a['data-lang']: a['href'] for a in doc.anchors if 'data-lang' in a},
                             {code: f'/{code}/minhajna/' for code in LANGS})
            self.assertIn('id="install"', html)
            self.assertIn('id="try"', html)
            self.assertIn('id="limits"', html)
            self.assertIn('id="verify"', html)
            self.assertFalse(any('data-header-contribute' in a for a in doc.anchors))

    def test_all_page_strings_are_translated(self):
        for lang in LANGS:
            ctx = Ctx(self.site, lang, self.site.routes['minhajna'])
            minhajna.render(ctx)
            self.assertFalse(ctx.fallbacks)
        for key in self.site.catalog.flat['en']:
            if key.startswith('minhajna.'):
                self.assertIn(key, self.site.catalog.flat['ar'])

    def test_only_the_reviewed_arabic_page_is_published_by_default(self):
        dist = self.tmp / 'default'
        site = build(dist, quiet=True, analytics='')
        html = (dist / 'ar/minhajna/index.html').read_text('utf-8')
        self.assertNotIn('noindex', html)
        self.assertIn('class="mh-download"', html)
        self.assertEqual(site.published, ('en',))
        self.assertFalse(site.catalog.reviewed('ar'))
        self.assertEqual(site.reviewed_pages, {'minhajna': ('ar',)})
        self.assertIn('noindex', (dist / 'ar/index.html').read_text('utf-8'))
        self.assertNotIn('النص العربي مسودة', html)
        self.assertIn('href="/en/"', html, 'About leads to the published homepage')

    def test_no_arabic_approval_keeps_the_page_as_an_invitation(self):
        reviews = self.tmp / 'no-reviews.json'
        reviews.write_text('{}', 'utf-8')
        dist = self.tmp / 'unreviewed'
        build(dist, quiet=True, analytics='', review_file=reviews)
        html = (dist / 'ar/minhajna/index.html').read_text('utf-8')
        self.assertIn('noindex', html)
        self.assertNotIn('class="mh-download"', html)


class ReleaseValidation(unittest.TestCase):
    def test_bad_metadata_fails_the_build_instead_of_linking_to_another_host(self):
        data = minhajna.load_release()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'release.json'
            for key, value in [('version', '0.1.0/elsewhere'), ('apk_sha256', 'invalid'),
                               ('certificate_sha256', 'invalid'), ('apk_bytes', 0),
                               ('minimum_android', True), ('published', 'not-a-date')]:
                path.write_text(json.dumps({**data, key: value}), 'utf-8')
                with self.subTest(key=key), self.assertRaises(ValueError):
                    minhajna.load_release(path)


if __name__ == '__main__':
    unittest.main()
