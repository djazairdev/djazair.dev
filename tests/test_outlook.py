"""Account standings must be reproducible; external forecasts and local scenarios must
never masquerade as measured contributions or an official Algeria forecast."""
import csv
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))
from djsite import data, outlook
from djsite.build import build
from djsite.config import LANGS


class Calculations(unittest.TestCase):
    def test_ties_missing_data_eu_and_quarter_filter(self):
        rows = [dict(economy=c, accounts=a, quarter=q) for c,a,q in (
            ('EU', 900, '2026-Q1'), ('US', 100, '2026-Q1'), ('IN', 100, '2026-Q1'),
            ('DZ', 20, '2026-Q1'), ('MA', None, '2026-Q1'), ('US', 999, '2025-Q4'))]
        fake = SimpleNamespace(quarter='2026-Q1', rows=lambda _: rows)
        found = outlook.standings(fake)
        self.assertEqual([(r['economy'],r['rank']) for r in found], [('IN',1),('US',1),('DZ',3)])
        self.assertNotIn('rank', rows[1], 'do not modify shared derived rows')

    def test_current_algeria_rank_recomputed_from_source(self):
        d = data.load()
        latest = [r for r in d.rows('indicators') if r['quarter']==d.quarter and r['economy']!='EU' and r['accounts'] is not None]
        dz = next(r for r in latest if r['economy']=='DZ')
        calculated = next(r for r in outlook.standings(d) if r['economy']=='DZ')
        self.assertEqual(calculated['rank'], 1+sum(r['accounts']>dz['accounts'] for r in latest))
        self.assertEqual((calculated['rank'],len(latest)), (50,229))

    def test_scenario_compounding_target_and_required_rate(self):
        self.assertEqual(outlook.horizon('2026-Q1'),4)
        self.assertEqual(outlook.horizon('2026-Q3'),3.5)
        self.assertEqual(outlook.horizon('2030-Q1'),0)
        self.assertLess(outlook.horizon('2030-Q2'),0)
        self.assertAlmostEqual(outlook.future(586990,.15,4),1026649.1786875)
        needed = outlook.required_rate(586990,4)
        self.assertAlmostEqual(needed,.14246347483868949)
        self.assertAlmostEqual(outlook.future(586990,needed,4),1_000_000)
        self.assertEqual(outlook.future(586990,0,4),586990)
        self.assertEqual(outlook.required_rate(1_100_000,4),0)
        for base,rate,years in ((0,.1,4),(586990,-.1,4),(586990,.1,0)):
            with self.assertRaises(ValueError): outlook.future(base,rate,years)

    def test_external_facts_match_the_published_chart(self):
        f = outlook.forecasts()
        values = {r['economy']:r['projected_accounts'] for r in f['rows']}
        self.assertEqual(values, dict(IN=57500000,US=54700000,BR=19600000,CN=17700000,JP=11700000,
            GB=11000000,DE=9800000,ID=8700000,CA=7200000,EG=4100000,NG=3300000,ZA=2700000,KE=1900000,MA=1400000))
        self.assertNotIn('DZ',values)
        self.assertEqual(f['target_year'],2030)
        self.assertEqual(f['baseline'],'2025-09')
        self.assertEqual(f['source_url'],outlook.SOURCE)


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        build(cls.tmp/'dist',quiet=True, published=LANGS)
        cls.dist=cls.tmp/'dist'

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.tmp)

    def test_order_and_source_boundaries_in_both_languages(self):
        for lang in ('en','ar'):
            html = (self.dist/lang/'index/index.html').read_text()
            ids = ['world-standing','developer-outlook','algeria-scenario','detailed-indicators','overview-next-h']
            self.assertEqual([html.index(f'id="{i}"') for i in ids],sorted(html.index(f'id="{i}"') for i in ids))
            self.assertIn(f'/{lang}/index/rankings/#global-accounts',html)
            self.assertIn('data-base="586990" data-years="4.0"',html)
            self.assertIn('value="15"',html)
            self.assertIn('class="scenario-control" hidden',html, 'hide the nonfunctional slider without JS')
            self.assertIn(outlook.SOURCE,html)
            self.assertIn('name="outlook-group"',html)
            self.assertIn('id="outlook-africa" checked',html)
            self.assertNotIn('class="untranslated"',html)
            forecast=re.search(r'id="developer-outlook".*?</section>',html,re.S).group()
            self.assertNotIn('data-economy="DZ"',forecast)
            self.assertIn(f'/{lang}/hub/?kind=gfi#issues',html)

    def test_country_table_and_csv_cover_same_measured_rows(self):
        csv_rows = list(csv.DictReader(io.StringIO((self.dist/'data/2026-q1/global-accounts.csv').read_text())))
        self.assertEqual(len(csv_rows),229)
        self.assertNotIn('EU',[r['economy'] for r in csv_rows])
        self.assertEqual(next(r['rank'] for r in csv_rows if r['economy']=='DZ'),'50')
        for lang in ('en','ar'):
            html=(self.dist/lang/'index/rankings/index.html').read_text()
            section=re.search(r'id="global-accounts".*?</section>',html,re.S).group()
            self.assertEqual(re.findall(r'data-key="([A-Z]{2})"',section),[r['economy'] for r in csv_rows])
            self.assertIn('class="is-dz" data-key="DZ"',section)
            self.assertIn('data-sortable',section)
            self.assertIn('GDC26',html, 'retain the distinct activity ranking')

    def test_published_download_keeps_provenance_and_forecast_measure(self):
        facts=json.loads((self.dist/'data/octoverse-2025/country-outlook.json').read_text())
        self.assertEqual(facts,outlook.forecasts())
        self.assertIn('not new accounts',facts['measure'])
        self.assertIn('no Algeria forecast',facts['method'])


if __name__=='__main__': unittest.main()
