# Quarterly reports

After each Innovation Graph release, djazair.dev publishes a short report in Arabic and English (in English only until the Arabic site is reviewed, D28): what the new quarter says about Algeria's developer accounts, and what we did. This page explains how a report is written, checked and published (PRD §13, IDX-17, ticket [#34](https://github.com/djazairdev/djazair.dev/issues/34)).

Reports are at `/en/reports/` and `/ar/reports/`. Home shows the latest one.

## What a report contains

Every report has the same seven sections, in this order, in both languages:

| # | Section | Id |
| --- | --- | --- |
| 1 | Headline numbers, each with its source and quarter | `numbers` |
| 2 | What changed since the previous quarter and since a year earlier | `changes` |
| 3 | Algeria compared with the peer medians | `peers` |
| 4 | One deep dive: languages, collaboration or topics | your choice, e.g. `languages` |
| 5 | Caveats | `caveats` |
| 6 | What djazair.dev did: Hub numbers, meetups, the Prep Track once it runs | `djazair` |
| 7 | Press kit: five charts, their data, a methodology summary and a citation | `press` |

`tests/test_reports.py` fails if a language is missing a section, or if the two languages differ.

## The rules

From PRD §13:

- Headlines say **"developer accounts"**, not "developers".
- Report bad news as clearly as good news.
- Compare Algeria with **group medians**, not with one neighbour.
- Never credit GitHub with a claim it didn't make. Octoverse 2025, for example, doesn't mention Algeria.
- **A second pair of eyes:** before publishing, someone other than the author checks the numbers against the published data, and a fluent reader checks the translation.
- Publish within **14 days** of the data release. Publish corrections in the corrections log within 7 days.

## Where it lives

```
content/reports/2026-q1/
  report.json   the quarter, the release, the status, the Hub numbers and the claims
  en.md         the English text
  ar.md         the Arabic text
```

The folder is named after the data quarter. The site gives every folder a page at `/<lang>/reports/<folder>/`; there is no list of routes to edit.

A report reads its **own quarter** in `data/derived/<folder>/`, not the latest one. Its numbers stay as they were when newer data arrives. The data pipeline keeps every quarter's folder.

### `report.json`

```json
{
  "quarter": "2026-Q1",
  "number": 1,
  "release": "054c7dbc527518fa2ecfd316efe2aa01f3986c39",
  "status": "draft",
  "published": null,
  "hub": {"projects": 1, "issues": 6, "date": "2026-10-06"},
  "checks": [ … ]
}
```

| Field | Meaning |
| --- | --- |
| `quarter` | The data quarter. It must match the folder name. |
| `number` | 1 for the first report, then 2, 3… |
| `release` | The Innovation Graph commit the text was written from. If GitHub re-releases the quarter, the page shows a notice saying the figures come from a newer release. |
| `status` | `draft` until it is checked, then `published`. A draft says so at the top, carries `noindex`, stays out of the sitemap, and is marked *Draft* on the Reports page and on Home. |
| `published` | The publication date, `YYYY-MM-DD`. Required when `status` is `published`. |
| `hub` | The Hub's numbers the report quotes, with the date they were read. They are written down rather than read from the live Hub, so the report doesn't change after it is published. Update them on the day you publish. |
| `checks` | Every claim the text makes in words, such as "sped up" or "dropped out of the top ten". The tests check each one against the quarter's data (see below). |

### `en.md` and `ar.md`

```markdown
---
title: Algeria’s developer accounts, Q1 2026
standfirst: Algeria had {{accounts}} developer accounts on GitHub at the end of March 2026, …
---

## Headline numbers {#numbers}

::: numbers
- accounts
- growth
- pushes
- permillion
:::
```

The title and standfirst go at the top, between `---` lines. The rest uses the same Markdown subset as the Methodology page ([content/README.md](../content/README.md)).

## Numbers in the text

Don't type figures: use a `{{name}}`. The site fills it in from the quarter's data, in each language's number format. All of these are available:

| Name | Example (en) |
| --- | --- |
| `quarter`, `previous_quarter`, `year_earlier_quarter`, `first_quarter` | Q1 2026, Q4 2025, Q1 2025, Q1 2020 |
| `release_date`, `population_year` | 7 July 2026, 2025 |
| `accounts`, `accounts_previous`, `accounts_year_earlier`, `accounts_na` | 586,990, …, the North African median |
| `added_quarter`, `added_year`, `change_quarter` | 54,107, 193,425, 10.2% |
| `yoy`, `pushes`, `repos`, `orgs`, each with `_previous` and `_year_earlier` | 49.1%, 1.06, 1.04, 0.0315 |
| the same with `_na` and `_af` for the North African and African medians | `yoy_na` 44.0%, `pushes_af_year_earlier` 1.02 |
| `permillion` | 12,375 |
| `streak` | four quarters (in a row that growth sped up) |
| `n_na`, `n_af` | 7, 29 (economies in each group) |
| `rank.<indicator>.na`, `rank.<indicator>.af`, for `accounts`, `yoy`, `pushes`, `repos`, `orgs`, `permillion` | 3rd of 7 (Arabic: 3 من 7) |
| `lang.<language>.name`, `.pushers`, `.change`, `.rank`, `.rank_year_earlier`, `.rank_first`, and `.ord…` for "4th" | `lang.python.pushers` 6,383; `lang.cpp.name` C++ |
| `contact` | the contact address, as a link |

Language names are lower case, with `C++` written `cpp`, `C#` `csharp` and spaces as `_` (`jupyter_notebook`). In Arabic text, write `{{lang.cpp.name}}` rather than `C++`, so the signs stay in place.

An unknown name fails the build, so a typo can't reach the page.

## Blocks

| Block | Draws |
| --- | --- |
| `::: numbers` | Headline figures, one per line: `accounts`, `growth`, `pushes`, `permillion` |
| `::: figure <chart>` | One of the five charts, numbered in order: `units` (the unit map), `growth`, `pushes`, `accounts` (with the six core peers), `languages`. Each has its downloads and data table |
| `::: changes` | Algeria's six indicators this quarter, a quarter earlier and a year earlier, with the change |
| `::: peers` | Algeria against the North African and African medians, with its ranks |
| `::: languages` | The top ten languages, and any that left them, with their ranks now, a year earlier and in 2020 |
| `::: hub` | The Hub numbers from `report.json` |
| `::: presskit` | The press kit download, and each chart with its own downloads |
| `::: method` | The methodology summary. The press kit includes it as text |
| `::: cite` | How to cite the report |

## Claims

Words like "rose", "more than doubled" or "dropped out" are claims about the data. List each one under `checks` in `report.json`; `tests/test_reports.py` fails if one doesn't hold. The kinds:

| Check | Holds when |
| --- | --- |
| `"rising": [series…]` / `"falling": [series…]` | each series is higher (lower) at `to` than at `from` |
| `"series": s, "at_least": t` / `"below": t` / `"equals": t` | in every quarter from `from` to `to`, `s` is ≥, < or = `t` |
| `"series": s, "grew_at_least": 1.0` | `s` grew by at least 100% from `from` to `to` |
| `"series": s, "streak": "up", "min": 2` | `s` rose in each of at least the last 2 quarters |
| `"group": "africa", "bottom": 5` | Algeria is among the last 5 in the group |
| `"language": l, "grew_at_least": 1.0` | the language's developers grew by at least 100% in a year |
| `"language": l, "entered_top": 10` / `"left_top": 10` | it is in the top ten now and wasn't a year earlier, or the reverse |
| `"language": l, "rank_at_most": 4` / `"rank_over": 10` | its rank now |
| `"language": l, "always_first": true` | it was first in every quarter since 2020 |

Indicator checks take `indicator` and a span: `from` defaults to the first quarter and `to` to the report's quarter. Series are ISO codes (`DZ`) or `median_north_africa`, `median_africa`, `median_core_peers`. Add a `claim` with the words being checked, so a failure says which sentence is wrong.

## Writing the next report

1. Wait for the new quarter in `data/derived/`: the daily data job publishes it within a day of GitHub's release.
2. Copy the last report's folder to the new quarter's name, for example `content/reports/2026-q2/`.
3. In `report.json`, set `quarter`, `number`, `release` (from `data/derived/<folder>/manifest.json`), `status: "draft"`, `published: null`, the Hub numbers, and empty `checks`.
4. Rewrite the English. Keep the seven sections; choose this quarter's deep dive. Use `{{names}}` for every figure.
5. List every claim under `checks`, and run the tests:

   ```bash
   python3 -m unittest discover -s tests
   ```

6. Build and read it at `/en/reports/<folder>/`:

   ```bash
   python3 site/build.py
   ```

7. Draft the Arabic from the English, then have a fluent reader check it ([arabic-review.md](arabic-review.md)).

## Publishing

A report is published when all of these are done:

- [ ] Someone other than the author has checked every number on the page against the published data in `data/derived/<folder>/` (the CSV files open in any spreadsheet).
- [ ] A fluent reader has checked the Arabic, once the Arabic site is live (D28).
- [ ] The Hub numbers in `report.json` are from the day of publication.
- [ ] `status` is `published` and `published` is today's date.

Merging that pull request publishes it: the draft notice goes, the page enters the sitemap, and Home and the Reports page show the date. Note it in the [changelog](../content/changelog.json).

If a published number turns out to be wrong, fix the text, keep the report's date, and add the correction to [content/corrections.json](../content/corrections.json) within 7 days.

## The press kit

Each report page offers one zip (about 60 KB) with:

- the five charts as SVG, in English and Arabic, dark and light;
- the data behind each chart, as CSV and JSON;
- the methodology summary in both languages, as text;
- a README with the citation, licence and contact.

The zip is rebuilt from the report and its data, so the same report always gives the same file. PNG versions of each chart are in its download menu on the page, drawn by the browser.

Charts and text are CC BY 4.0, credit "djazair.dev"; the data is CC0.
