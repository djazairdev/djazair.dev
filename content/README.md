# content

- `editorial/`: headlines written for a data quarter (`2026-q1.json`), in English and Arabic. Each file lists the factual claims its words make under `checks`; the build uses the file only while every claim holds against `data/derived/`, and `tests/test_home.py` fails when one doesn't. Check kinds: `rising` (series higher at `to` than at `from`), `at_least` and `below` (one series against another in every quarter of the span). A span runs from `from` (default: the first quarter) to `to` (default: the file's quarter).
- `reports/`: quarterly reports, in Arabic and English.
- `meetups/`: the meetups section (from December 2026).

Text and charts are CC BY 4.0 ([LICENSE-content](../LICENSE-content)).
