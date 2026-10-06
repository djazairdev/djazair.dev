# content

- `editorial/`: headlines written for a data quarter (`2026-q1.json`), in English and Arabic. Each file lists the factual claims its words make under `checks`; the build uses the file only while every claim holds against `data/derived/`, and `tests/test_home.py` fails when one doesn't. Check kinds: `rising` (series higher at `to` than at `from`), `at_least` and `below` (one series against another in every quarter of the span). A span runs from `from` (default: the first quarter) to `to` (default: the file's quarter).
- `methodology/` and `about/`: the Methodology and About pages, `en.md` and `ar.md` each. A small Markdown subset (`site/djsite/markdown.py`): `## Title {#id}` starts a numbered section, `::: name` blocks are drawn by the page with its components, and `{{name}}` values are computed from the data so figures stay true. The formulas must match `pipeline/indicators.py`; `tests/test_methodology.py` checks them.
- `changelog.json`: changes worth telling readers about. Data releases are added automatically from `data/derived/*/manifest.json`.
- `corrections.json`: every correction to a published number or statement, within 7 days of its discovery.
- `reports/`: quarterly reports, in Arabic and English.
- `meetups/`: the meetups section (from December 2026).

Text and charts are CC BY 4.0 ([LICENSE-content](../LICENSE-content)).
