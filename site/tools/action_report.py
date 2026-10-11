"""Export aggregate campaign counts from Cloudflare Analytics Engine as CSV.

Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_ANALYTICS_TOKEN (Account Analytics Read).
python3 site/tools/action_report.py --days 7 --out /private/path/week.csv
Credentials stay in environment and HTTPS headers, never files or printed errors.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def query(days):
    if not isinstance(days, int) or not 1 <= days <= 90:
        raise ValueError('days must be between 1 and 90')
    return f"""SELECT toDate(timestamp) AS date, blob1 AS event, blob2 AS page,
blob3 AS language, blob4 AS section, blob5 AS source, blob6 AS medium, blob7 AS campaign,
SUM(_sample_interval * double1) AS count FROM djazair_landing_events
WHERE timestamp >= NOW() - INTERVAL '{days}' DAY
GROUP BY date, event, page, language, section, source, medium, campaign
ORDER BY date, campaign, event FORMAT JSON"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--days', type=int, default=7)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    account = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '')
    token = os.environ.get('CLOUDFLARE_ANALYTICS_TOKEN', '')
    if not re.fullmatch(r'[0-9a-f]{32}', account) or not token:
        raise SystemExit('Set the account ID and an Account Analytics Read token in the environment.')
    try:
        sql = query(args.days)
        request = Request(f'https://api.cloudflare.com/client/v4/accounts/{account}/analytics_engine/sql',
                          data=sql.encode(), headers={'Authorization': f'Bearer {token}'}, method='POST')
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        rows = result['data']
    except (HTTPError, URLError, ValueError, KeyError):
        raise SystemExit('The aggregate report could not be retrieved. Check permissions, dates and dataset availability.') from None
    fields = ('date', 'event', 'page', 'language', 'section', 'source', 'medium', 'campaign', 'count')
    # Restrict export dimensions too: no spreadsheet formulas or unexpected fields.
    for row in rows:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(row.get('date', ''))):
            raise SystemExit('Unexpected report date.')
        if any(not re.fullmatch(r'[a-z0-9_-]{1,64}', str(row.get(k, ''))) for k in fields[1:-1]):
            raise SystemExit('Unexpected report dimension.')
        try:
            if float(row['count']) < 0:
                raise ValueError
        except (KeyError, ValueError):
            raise SystemExit('Unexpected report count.') from None
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    args.out.write_text(buffer.getvalue(), encoding='utf-8')
    print(f'Exported {len(rows)} aggregate rows.')


if __name__ == '__main__':
    main()
