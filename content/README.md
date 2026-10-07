# content

- `editorial/`: headlines written for a data quarter (`2026-q1.json`), in English and Arabic. Each file lists the factual claims its words make under `checks`; the build uses the file only while every claim holds against `data/derived/`, and `tests/test_home.py` fails when one doesn't. Check kinds: `rising` (series higher at `to` than at `from`), `at_least` and `below` (one series against another in every quarter of the span). A span runs from `from` (default: the first quarter) to `to` (default: the file's quarter). Reports use more kinds, listed in [docs/reports.md](../docs/reports.md#claims).
- `methodology/` and `about/`: the Methodology and About pages, `en.md` and `ar.md` each. A small Markdown subset (`site/djsite/markdown.py`): `## Title {#id}` starts a numbered section, `::: name` blocks are drawn by the page with its components, and `{{name}}` values are computed from the data so figures stay true. The formulas must match `pipeline/indicators.py`; `tests/test_methodology.py` checks them.
- `changelog.json`: changes worth telling readers about. Data releases are added automatically from `data/derived/*/manifest.json`.
- `localisation.json`: the translation teams the Hub's localisation page links to (ticket #40): name, platform, what is translated there in English and Arabic, and one link per language (`ar`, `kab`, `zgh`). Its `about` explains the fields; `site/tools/links.py` checks the links every week.
- `corrections.json`: every correction to a published number or statement, within 7 days of its discovery.
- `reports/`: quarterly reports, one folder per data quarter (`2026-q1/`): `report.json` (status, Hub numbers, the claims the text makes) and `en.md`, `ar.md`. [docs/reports.md](../docs/reports.md) explains how to write, check and publish one.
- `meetups/`: the meetups section (from December 2026).

Text and charts are CC BY 4.0 ([LICENSE-content](../LICENSE-content)).
