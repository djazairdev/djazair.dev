"""Chart downloads (ticket #48): each chart's CSV and JSON hold the same numbers."""

import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'site'))

from djsite.build import build  # noqa: E402


def parse(cell):
    """A CSV cell as the JSON would write it."""
    if cell == '':
        return None
    if cell in ('true', 'false'):
        return cell == 'true'
    return float(cell)


class ChartDownloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.dist = cls.tmp / 'dist'
        cls.site = build(cls.dist, quiet=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_csv_and_json_hold_the_same_numbers(self):
        self.assertGreater(len(self.site.charts), 0)  # don't pass on an empty list

        for chart_id, entry in self.site.charts.items():
            with self.subTest(chart=chart_id):
                csv_path = self.dist / entry['csv'][0].lstrip('/')
                json_path = self.dist / entry['json'][0].lstrip('/')
                rows = list(csv.reader(io.StringIO(csv_path.read_text('utf-8'))))
                payload = json.loads(json_path.read_text('utf-8'))

                if 'series' in payload:
                    # the JSON holds columns, the CSV holds rows
                    self.assertEqual(rows[0], ['quarter'] + [s['key'] for s in payload['series']])
                    self.assertEqual([row[0] for row in rows[1:]], payload['x'])
                    for i, s in enumerate(payload['series']):
                        column = [parse(row[i + 1]) for row in rows[1:]]
                        self.assertEqual(column, s['values'])

                elif 'bars' in payload or 'rows' in payload:
                    # one CSV row per JSON item
                    items = payload['bars'] if 'bars' in payload else payload['rows']
                    header, body = rows[0], rows[1:]
                    self.assertEqual(len(body), len(items))
                    for row, item in zip(body, items):
                        for column, cell in zip(header, row):
                            field = 'key' if column == 'series' else column
                            if field == 'key':
                                self.assertEqual(cell, item['key'])
                            else:
                                value = parse(cell)
                                self.assertEqual(value, item[field])
                                # False == 0 in Python, so check booleans separately
                                self.assertEqual(type(value) is bool, type(item[field]) is bool)

                else:
                    self.fail(f'unknown JSON shape in {chart_id}')