"""Public discovery documents, downloadable dataset provenance and editorial links."""
import datetime
import base64
import hashlib
from html.parser import HTMLParser
import json
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
from djsite.assets import minify_css
from djsite.build import build
from djsite.config import LANGS, PUBLISHED, SITE_URL
from djsite.structured import script
from htmlcheck import Doc


class Scripts(HTMLParser):
    """Read script text with HTML tag semantics, including mixed-case tag names."""
    def __init__(self, text):
        super().__init__()
        self.items = []
        self.current = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.current = (dict(attrs), [])

    def handle_data(self, text):
        if self.current is not None:
            self.current[1].append(text)

    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            attrs, parts = self.current
            self.items.append((attrs, ''.join(parts)))
            self.current = None


class Discovery(unittest.TestCase):
    """The site as it ships, in its published languages."""
    PUBLISHED = PUBLISHED

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, quiet=True, published=cls.PUBLISHED)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def graphs(self, lang):
        text = (self.dist / lang / 'data/index.html').read_text('utf-8')
        return [json.loads(p) for attrs, p in Scripts(text).items if attrs.get('type') == 'application/ld+json']

    def test_dataset_catalogue_describes_every_real_download(self):
        for lang in self.PUBLISHED:
            nodes = [node for graph in self.graphs(lang) for node in graph['@graph']]
            datasets = [n for n in nodes if n['@type'] == 'Dataset']
            self.assertEqual(len(datasets), 14)
            self.assertEqual(len({n['@id'] for n in datasets}), 14)
            for dataset in datasets:
                with self.subTest(lang=lang, dataset=dataset['@id']):
                    self.assertTrue(dataset['name'])
                    self.assertTrue(dataset['description'])
                    self.assertNotRegex(dataset['description'], r'\{\w+\}')
                    self.assertEqual(dataset['inLanguage'], lang)
                    self.assertIn('creator', dataset)
                    target = urlsplit(dataset['url'])
                    html = (self.dist / target.path.lstrip('/') / 'index.html').read_text('utf-8')
                    self.assertIn(target.fragment, Doc(html).ids)
                    for download in dataset['distribution']:
                        self.assertEqual(download['@type'], 'DataDownload')
                        path = self.dist / download['contentUrl'].removeprefix(SITE_URL).lstrip('/')
                        self.assertTrue(path.is_file())
                        self.assertEqual(download['contentSize'], f'{path.stat().st_size} bytes')
                        self.assertEqual(download['encodingFormat'], {'csv': 'text/csv', 'json': 'application/json'}[path.suffix[1:]])

    def test_forecast_and_measured_data_keep_their_provenance(self):
        nodes = [n for g in self.graphs('en') for n in g['@graph'] if n['@type'] == 'Dataset']
        forecast = next(n for n in nodes if 'country-outlook.json' in n['@id'])
        self.assertEqual(forecast['creator']['name'], 'GitHub')
        self.assertEqual(forecast['datePublished'], '2025-10-28')
        self.assertEqual(forecast['temporalCoverage'], '2030')
        self.assertNotIn('license', forecast, 'no invented licence for the Octoverse publication')
        measured = next(n for n in nodes if 'global-accounts.csv' in n['@id'])
        self.assertEqual(measured['temporalCoverage'], '2026-01-01/2026-03-31')
        self.assertEqual(measured['license'], self.site.data.manifest['licence_url'])
        gdc = next(n for n in nodes if '/gdc26#dataset' in n['@id'])
        self.assertEqual(gdc['temporalCoverage'], '2025-07-01/2026-06-30')
        self.assertTrue(any(isinstance(s, dict) and s.get('license', '').endswith('/by/4.0/') for s in gdc['isBasedOn']))

    def test_jsonld_cannot_close_its_script_element(self):
        dangerous = '</script><script>alert("x")</script>&'
        output = str(script({'name': dangerous}))
        self.assertEqual(output.count('</script>'), 1)
        self.assertEqual(json.loads(output.split('>', 1)[1].rsplit('</script>', 1)[0])['name'], dangerous)

    def test_text_and_xml_sitemaps_match_without_nonindexed_pages(self):
        xml = ET.parse(self.dist / 'sitemap.xml')
        urls = [n.text for n in xml.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        text = (self.dist / 'sitemap.txt').read_text('utf-8').splitlines()
        self.assertEqual(text, urls)
        self.assertEqual(len(text), len(set(text)))
        self.assertFalse(any('/embed/' in u or '/404' in u or '/reports/' in u for u in text))

    def test_ai_guide_links_exist_and_explain_limits(self):
        guide = (self.dist / 'llms.txt').read_text('utf-8')
        self.assertTrue(guide.startswith('# djazair.dev\n\n>'))
        self.assertIn(self.site.data.quarter, guide)
        self.assertIn('not a prediction', guide)
        self.assertIn('inactive accounts', guide)
        self.assertIn('no combined score', guide)
        for url in re.findall(r'\]\((https://djazair.dev/[^)]+)\)', guide):
            path = urlsplit(url).path
            target = self.dist / path.lstrip('/')
            if path.endswith('/'):
                target /= 'index.html'
            self.assertTrue(target.is_file(), url)
        for lang in LANGS:
            md = self.dist / lang / 'data/index.md'
            self.assertEqual(md.is_file(), lang in self.PUBLISHED, 'a guide in each published language only')
            if md.is_file():
                text = md.read_text('utf-8')
                self.assertTrue(text.startswith('# '))
                self.assertNotIn('route:', text)
                self.assertIn('/overview.csv)', text)
        self.assertEqual(f'{SITE_URL}/ar/' in guide, 'ar' in self.PUBLISHED, 'Arabic addresses only once published')

    def test_security_disclosure_is_canonical_private_and_not_expired(self):
        text = (self.dist / '.well-known/security.txt').read_text('utf-8')
        self.assertEqual(text, (self.dist / 'security.txt').read_text('utf-8'))
        self.assertIn('Contact: https://github.com/djazairdev/djazair.dev/security/advisories/new', text)
        self.assertIn('Contact: mailto:contact@djazair.dev', text)
        self.assertIn(f'Canonical: {SITE_URL}/.well-known/security.txt', text)
        expires = datetime.datetime.fromisoformat(re.search(r'Expires: (.+)', text)[1].replace('Z', '+00:00'))
        remaining = expires - datetime.datetime.now(datetime.timezone.utc)
        self.assertGreater(remaining.total_seconds(), 0, 'renew security.txt after verifying the contact channels')
        self.assertLessEqual(remaining.days, 366)

    def test_script_policy_allows_only_the_known_language_redirect_inline(self):
        root = (self.dist / 'index.html').read_text('utf-8')
        inline = next(text for attrs, text in Scripts(root).items if not attrs.get('src') and not attrs.get('type'))
        digest = base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode()
        headers = (self.dist / '_headers').read_text('utf-8')
        policy = re.search(r'Content-Security-Policy: (.+)', headers)[1]
        self.assertIn(f"'sha256-{digest}'", policy)
        self.assertIn("script-src 'self' https://static.cloudflareinsights.com", policy)
        self.assertIn("script-src-attr 'none'", policy)
        self.assertNotIn("'unsafe-inline'", policy)
        self.assertNotIn("'unsafe-eval'", policy)

    def test_founders_coffee_has_followable_editorial_links(self):
        for lang in self.PUBLISHED:
            for page in ('index.html', 'meetups/index.html'):
                doc = Doc((self.dist / lang / page).read_text('utf-8'))
                links = [a for a in doc.anchors if urlsplit(a.get('href', '')).hostname == 'founders.coffee']
                self.assertTrue(links, (lang, page))
                for link in links:
                    self.assertFalse({'nofollow', 'ugc', 'sponsored'} & set(link.get('rel', '').split()))

    def test_page_css_excludes_unrelated_routes(self):
        home = (self.dist / 'en/index.html').read_text('utf-8').split('<style>')[1].split('</style>')[0]
        data = (self.dist / 'en/data/index.html').read_text('utf-8').split('<style>')[1].split('</style>')[0]
        self.assertNotIn('.outlook-', home)
        self.assertNotIn('.hub-search', home)
        self.assertNotIn('.trc:', home)
        self.assertNotIn('.hero-map-stage', data)
        self.assertIn('prefers-reduced-motion', home)
        self.assertIn('prefers-reduced-motion', data)

    def test_css_compaction_preserves_strings_and_calc_spacing(self):
        css = '.a :hover { width: calc(100% - 2px); content: "x /* literal */ y"; } /* drop */'
        result = minify_css(css)
        self.assertIn('.a :hover', result)
        self.assertIn('calc(100% - 2px)', result)
        self.assertIn('"x /* literal */ y"', result)
        self.assertNotIn('drop', result)


class DiscoveryWithArabic(Discovery):
    """The same checks with the Arabic pages built, as they will be once reviewed."""
    PUBLISHED = LANGS


if __name__ == '__main__':
    unittest.main()
