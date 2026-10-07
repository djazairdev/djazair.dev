# Algeria Developer Index, 2026 Q1 data

Computed by [djazair.dev](https://djazair.dev) from GitHub Innovation Graph release
[`054c7dbc5275`](https://github.com/github/innovationgraph/tree/054c7dbc527518fa2ecfd316efe2aa01f3986c39/data) (2026-07-07).

- **Licence:** [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), no rights reserved.
- **Attribution:** Data: GitHub Innovation Graph (CC0). Population: World Bank (CC BY 4.0), each economy’s latest year.
- **Format:** every table as CSV (UTF-8, one header row) and as JSON (the same rows, plus the licence, the source
  release and a description of every column). Numbers are rounded to six decimal places. An empty CSV cell or a JSON
  `null` means the value is missing, never zero.
- **Checksums:** `manifest.json` lists every file with its size and SHA-256.

| Files | What they hold |
|---|---|
| [`overview.csv`](overview.csv), [`overview.json`](overview.json) | Algeria’s latest value of each indicator, the same quarter a year earlier, and its place and the median in each peer group. One row per indicator. |
| [`peers.csv`](peers.csv), [`peers.json`](peers.json) | Algeria, the rest of North Africa and the core peers in the latest quarter, with the counts behind each ratio. |
| [`groups.csv`](groups.csv), [`groups.json`](groups.json) | The members of each peer group in every quarter, and the median of each indicator across the members with data. |
| [`ranks.csv`](ranks.csv), [`ranks.json`](ranks.json) | Every member’s place in each peer group for each indicator in the latest quarter, highest first. Earlier quarters can be ranked from the indicators and groups tables. |
| [`trends.csv`](trends.csv), [`trends.json`](trends.json) | Every indicator in every quarter since 2020 Q1 for Algeria, the rest of North Africa and the core peers, with the peer-group medians. |
| [`languages.csv`](languages.csv), [`languages.json`](languages.json) | Developers who pushed in each language in the latest quarter and a year earlier. One developer can push in several languages, so the counts can’t be added up. GitHub lists a language once 100 or more developers push in it. |
| [`languages_algeria.csv`](languages_algeria.csv), [`languages_algeria.json`](languages_algeria.json) | Developers in Algeria who pushed in each language, every quarter since 2020 Q1. |
| [`topics.csv`](topics.csv), [`topics.json`](topics.json) | The topics GitHub publishes for each economy in the latest quarter, and a year earlier: those with 100 or more developers pushing. |
| [`collaboration.csv`](collaboration.csv), [`collaboration.json`](collaboration.json) | Git pushes and pull requests between Algeria and other economies, both ways, every quarter: those developers in Algeria sent to repositories owned elsewhere, and those repositories owned in Algeria received. |
| [`gdc26.csv`](gdc26.csv), [`gdc26.json`](gdc26.json) | GitHub’s one-off rankings for the Global Digital Collaboration Conference (September 2026): git pushes from 2025 Q3 to 2026 Q2, corrected for VPN use, per 1,000 working-age people for Africa’s ten highest, and in total for the 30 economies with the most. Then djazair.dev’s estimate of the same measure, uncorrected, for Algeria, its core peers and the ten. |
| [`indicators.csv`](indicators.csv), [`indicators.json`](indicators.json) | Every indicator for every economy in the release, every quarter since 2020 Q1. Empty where an input is missing, never zero. |
| [`revisions.csv`](revisions.csv), [`revisions.json`](revisions.json) | Past values this release changed, against the release archived before it (named in manifest.json). An empty before or now means the value was added or removed. |

Every column is described in [data/README.md](https://github.com/djazairdev/djazair.dev/blob/main/data/README.md).
