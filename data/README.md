# data

| Folder | What it holds | Licence |
|---|---|---|
| `raw/<commit>/` | One archived GitHub Innovation Graph release per folder, named after the source commit | CC0 (as published by GitHub) |
| `derived/<yyyy-qN>/` | The Index: indicators computed by `pipeline/`, as CSV and JSON | CC0 ([LICENSE-data](../LICENSE-data)) |
| `derived/latest.json` | Which quarter the site builds: `{"quarter", "folder", "release", "licence", …}` | CC0 |
| `population.json` | World Bank population (`SP.POP.TOTL`) and working-age population (`SP.POP.1564.TO`), every economy, every year since 2015 | CC BY 4.0 (World Bank) |

Data: GitHub Innovation Graph (CC0).

## Raw archive

Each `raw/<commit>/` folder holds the eight files of the release exactly as GitHub published them, plus:

- `SHA256SUMS`: the SHA-256 of every file, in `sha256sum` format (`sha256sum -c SHA256SUMS` checks them);
- `release.json`: the source commit, its date and message, the data quarter (the latest quarter in `developers.csv`), and each file's size and checksum.

The pipeline only writes a release folder once and never changes it afterwards. Each new release adds about 10 MB of files, but releases repeat most of the previous release's rows, so git stores them compactly.

## Derived data

`python3 -m pipeline publish` validates the latest archived release and writes `derived/<yyyy-qN>/` from it. The site reads nothing else: every number on it comes from these files.

Each folder holds:

- one **CSV** and one **JSON** file per table (below);
- `README.md`: the licence, the attribution and the source release;
- `manifest.json`: the data quarter and every quarter covered, the source release (`release`, `release_date`, `source`), the population year used, the revision check (`revisions`: the release compared with and how many past values changed), `generated_at`, and every file with its size, SHA-256, table and row count.

**Format**

- CSV: UTF-8, comma-separated, one header row, `\n` line ends. Booleans are `true` or `false`.
- JSON: an object with `licence`, `licence_url`, `attribution`, `quarter`, `release`, `release_date`, `source`, `format_version`, `table`, `title`, `description`, `columns` (each column's `name`, `type` and `description`) and `rows` (one object per row, keys in column order).
- Types: `string`, `integer`, `number` or `boolean`. Numbers are rounded to six decimal places and written without an exponent or trailing zeros.
- Missing values are empty in CSV and `null` in JSON. A missing value is never written as zero.
- Shares and growth rates are fractions: `0.491469` is 49.1469%.
- Economies are ISO 3166-1 alpha-2 codes as GitHub publishes them; `EU` is the European Union.
- Quarters are written `2026-Q1`; folder names use lower case (`2026-q1`).

**Stable for diffs:** rows come in a fixed order, JSON keys are sorted (row keys keep the column order, one row per line), and `generated_at` changes only when a file does. Publishing the same release twice changes nothing. A test checks that the committed files are exactly what the code makes from the archived release.

**Peer groups** (PRD §9.3): `north_africa` (Algeria, Egypt, Libya, Mauritania, Morocco, Sudan, Tunisia), `core_peers` (Morocco, Tunisia, Egypt, Nigeria, Kenya, South Africa), `africa` (every African economy with at least 20,000 accounts a year earlier, so from 2021 Q1) and `algeria_and_peers` (Algeria and the core peers, for ranks among seven). Medians use the members with data; ranks are 1 for the highest, and ties share a place.

**Population** comes from the World Bank: each economy's latest year (recorded in `population_year` and in the manifest).

### Tables

### `overview`

Algeria’s latest value of each indicator, the same quarter a year earlier, and its place and the median in each peer group. One row per indicator.

| Column | Type | Meaning |
|---|---|---|
| `indicator` | string | Indicator: one of the indicator columns of the indicators table |
| `quarter` | string | Data quarter, as YYYY-QN |
| `value` | number | Algeria, in the indicator’s unit |
| `year_earlier` | number | Algeria in the same quarter a year earlier |
| `change` | number | value / year_earlier − 1 (empty for yoy and since_2020, which are already changes) |
| `north_africa_median` | number | Median across the members of north_africa with data |
| `north_africa_rank` | integer | Algeria’s place in north_africa: 1 is the highest, ties share a place |
| `north_africa_ranked` | integer | Members of north_africa with data |
| `core_peers_median` | number | Median across the members of core_peers with data |
| `core_peers_rank` | integer | Algeria’s place in core_peers: 1 is the highest, ties share a place |
| `core_peers_ranked` | integer | Members of core_peers with data |
| `africa_median` | number | Median across the members of africa with data |
| `africa_rank` | integer | Algeria’s place in africa: 1 is the highest, ties share a place |
| `africa_ranked` | integer | Members of africa with data |
| `algeria_and_peers_median` | number | Median across the members of algeria_and_peers with data |
| `algeria_and_peers_rank` | integer | Algeria’s place in algeria_and_peers: 1 is the highest, ties share a place |
| `algeria_and_peers_ranked` | integer | Members of algeria_and_peers with data |

### `peers`

Algeria, the rest of North Africa and the core peers in the latest quarter, with the counts behind each ratio.

| Column | Type | Meaning |
|---|---|---|
| `economy` | string | ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union) |
| `north_africa` | boolean | In the North Africa group |
| `core_peer` | boolean | One of the six core peers |
| `quarter` | string | Data quarter, as YYYY-QN |
| `accounts_2020_q1` | integer | Accounts in 2020 Q1 |
| `accounts` | integer | Developer accounts located in the economy (a running total) |
| `yoy` | number | Growth in accounts on the same quarter a year earlier: accounts / accounts a year earlier − 1 |
| `since_2020` | number | Growth in accounts since 2020 Q1: accounts / accounts in 2020 Q1 − 1 |
| `pushes_per_account` | number | Git pushes during the quarter / accounts |
| `pushes_per_account_4q` | number | Pushes over the last four quarters / mean accounts over them / 4 |
| `repos_per_account` | number | Repositories / accounts (both running totals) |
| `orgs_per_account` | number | Organisations / accounts (both running totals) |
| `accounts_per_million` | number | Accounts per million people (World Bank population, latest year) |
| `population_year` | integer | Year of the World Bank population used |
| `topics` | integer | Topics GitHub publishes for the economy: those with 100 or more developers pushing |
| `git_pushes` | integer | Git pushes during the quarter (Innovation Graph git_pushes) |
| `repositories` | integer | Repositories, a running total (Innovation Graph repositories) |
| `organizations` | integer | Organisations, a running total (Innovation Graph organizations) |
| `population` | integer | World Bank population (SP.POP.TOTL) in population_year |

### `groups`

The members of each peer group in every quarter, and the median of each indicator across the members with data.

| Column | Type | Meaning |
|---|---|---|
| `group` | string | north_africa: Algeria, Egypt, Libya, Mauritania, Morocco, Sudan and Tunisia; core_peers: Morocco, Tunisia, Egypt, Nigeria, Kenya and South Africa; africa: African economies with at least 20,000 accounts a year earlier (from 2021 Q1); algeria_and_peers: Algeria and the six core peers |
| `quarter` | string | Data quarter, as YYYY-QN |
| `members` | integer | Members with data |
| `economies` | string | Member codes, separated by spaces |
| `median_accounts` | number | Median of accounts across the members with data |
| `median_yoy` | number | Median of yoy across the members with data |
| `median_since_2020` | number | Median of since_2020 across the members with data |
| `median_pushes_per_account` | number | Median of pushes_per_account across the members with data |
| `median_pushes_per_account_4q` | number | Median of pushes_per_account_4q across the members with data |
| `median_repos_per_account` | number | Median of repos_per_account across the members with data |
| `median_orgs_per_account` | number | Median of orgs_per_account across the members with data |
| `median_accounts_per_million` | number | Median of accounts_per_million across the members with data |
| `median_topics` | number | Median of topics across the members with data |

### `ranks`

Every member’s place in each peer group for each indicator in the latest quarter, highest first. Earlier quarters can be ranked from the indicators and groups tables.

| Column | Type | Meaning |
|---|---|---|
| `group` | string | Peer group (see the groups table) |
| `quarter` | string | Data quarter, as YYYY-QN |
| `indicator` | string | Indicator: one of the indicator columns of the indicators table |
| `economy` | string | ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union) |
| `value` | number | Value of the indicator |
| `rank` | integer | Place: 1 is the highest, ties share a place |
| `ranked` | integer | Members with data |

### `trends`

Every indicator in every quarter since 2020 Q1 for Algeria, the rest of North Africa and the core peers, with the peer-group medians.

| Column | Type | Meaning |
|---|---|---|
| `quarter` | string | Data quarter, as YYYY-QN |
| `indicator` | string | Indicator: one of the indicator columns of the indicators table |
| `series` | string | ISO code of the economy, or `median_<group>` for a peer-group median |
| `value` | number | Value; empty where an input is missing |

### `languages`

Developers who pushed in each language in the latest quarter and a year earlier. One developer can push in several languages, so the counts can’t be added up. GitHub lists a language once 100 or more developers push in it.

| Column | Type | Meaning |
|---|---|---|
| `economy` | string | ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union) |
| `quarter` | string | Data quarter, as YYYY-QN |
| `rank` | integer | Place by developers pushing |
| `language` | string | Language, as GitHub Linguist names it |
| `language_type` | string | programming, markup, data or prose |
| `pushers` | integer | Developers who pushed in the language |
| `rank_year_earlier` | integer | Place in the same quarter a year earlier |
| `pushers_year_earlier` | integer | Developers who pushed in it a year earlier |
| `change` | number | pushers / pushers_year_earlier − 1 |

### `languages_algeria`

Developers in Algeria who pushed in each language, every quarter since 2020 Q1.

| Column | Type | Meaning |
|---|---|---|
| `quarter` | string | Data quarter, as YYYY-QN |
| `rank` | integer | Place by developers pushing |
| `language` | string | Language, as GitHub Linguist names it |
| `language_type` | string | programming, markup, data or prose |
| `pushers` | integer | Developers who pushed in the language |

### `topics`

The topics GitHub publishes for each economy in the latest quarter, and a year earlier: those with 100 or more developers pushing.

| Column | Type | Meaning |
|---|---|---|
| `economy` | string | ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union) |
| `quarter` | string | Data quarter, as YYYY-QN |
| `rank` | integer | Place by developers pushing |
| `topic` | string | Repository topic |
| `pushers` | integer | Developers who pushed to repositories with the topic |
| `rank_year_earlier` | integer | Place in the same quarter a year earlier; empty if GitHub didn’t publish the topic then |
| `pushers_year_earlier` | integer | Developers who pushed to repositories with the topic a year earlier |
| `change` | number | pushers / pushers_year_earlier − 1 |

### `collaboration`

Git pushes and pull requests between Algeria and other economies, both ways, every quarter: those developers in Algeria sent to repositories owned elsewhere, and those repositories owned in Algeria received.

| Column | Type | Meaning |
|---|---|---|
| `quarter` | string | Data quarter, as YYYY-QN |
| `direction` | string | sent: from developers in Algeria to repositories owned in the partner; received: from developers in the partner to repositories owned in Algeria |
| `rank` | integer | Place by weight among the economies in the quarter and direction; empty for the EU |
| `partner` | string | ISO code of the partner economy; EU for the European Union, which GitHub lists as the sum of its members listed |
| `weight` | integer | Git pushes sent and pull requests opened (GitHub economy_collaborators) |

GitHub places a repository in the economy of its owner, and an organisation's repositories where most of its members are. It lists a pair of economies only above its publication threshold, and calls the measure a lower bound: work on a repository with contributors in several economies counts toward one.

### `gdc26`

GitHub’s one-off rankings for the Global Digital Collaboration Conference (September 2026): git pushes from 2025 Q3 to 2026 Q2, corrected for VPN use, per 1,000 working-age people for Africa’s ten highest, and in total for the 30 economies with the most. Then djazair.dev’s estimate of the same measure, uncorrected, for Algeria, its core peers and the ten.

| Column | Type | Meaning |
|---|---|---|
| `list` | string | africa: GitHub’s ten highest in Africa by pushes per 1,000 working-age people; world: GitHub’s 30 economies with the most pushes; estimate: djazair.dev’s estimate from the quarterly files |
| `rank` | integer | Place in GitHub’s list; empty for estimates |
| `economy` | string | ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union) |
| `region` | string | ICANN region, as GitHub gives it; empty for estimates |
| `pushes` | integer | Git pushes from 2025 Q3 to 2026 Q2: weighted by GitHub to correct for VPN use in its lists, unweighted in estimates |
| `working_age_population` | integer | People aged 15 to 64 (World Bank, 2025); empty in the world list |
| `per_1k_working_age` | number | pushes / working_age_population × 1,000; empty in the world list |
| `pushes_2025_q3` | integer | Estimates: git pushes in 2025 Q3, from the quarterly files |
| `pushes_2025_q4` | integer | Estimates: git pushes in 2025 Q4, from the quarterly files |
| `pushes_2026_q1` | integer | Estimates: git pushes in 2026 Q1, from the quarterly files |
| `pushes_2026_q2` | integer | Estimates: git pushes in 2026 Q2, from the quarterly files |
| `quarters_assumed` | integer | Estimates: how many of the four quarters aren’t released yet and repeat the latest one |

GitHub’s figures come from `supplementary_data/git_pushes_weighted_by_profile_economy/` in github/innovationgraph, archived in [`raw/gdc26/`](raw/gdc26/) (`python3 -m pipeline gdc26`). GitHub weights each economy’s pushes by how many developers’ profiles name it against how many it locates there by network address, so its lists can’t be reproduced from the quarterly files. The estimate can: it sums the same four quarters of `git_pushes`, repeating the latest released quarter for any still to come, and divides by the World Bank’s working-age population for 2025, the year GitHub used.

### `indicators`

Every indicator for every economy in the release, every quarter since 2020 Q1. Empty where an input is missing, never zero.

| Column | Type | Meaning |
|---|---|---|
| `economy` | string | ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union) |
| `quarter` | string | Data quarter, as YYYY-QN |
| `accounts` | integer | Developer accounts located in the economy (a running total) |
| `yoy` | number | Growth in accounts on the same quarter a year earlier: accounts / accounts a year earlier − 1 |
| `since_2020` | number | Growth in accounts since 2020 Q1: accounts / accounts in 2020 Q1 − 1 |
| `pushes_per_account` | number | Git pushes during the quarter / accounts |
| `pushes_per_account_4q` | number | Pushes over the last four quarters / mean accounts over them / 4 |
| `repos_per_account` | number | Repositories / accounts (both running totals) |
| `orgs_per_account` | number | Organisations / accounts (both running totals) |
| `accounts_per_million` | number | Accounts per million people (World Bank population, latest year) |
| `topics` | integer | Topics GitHub publishes for the economy: those with 100 or more developers pushing |
| `population_year` | integer | Year of the population used |

### `revisions`

Past values this release changed, against the release archived before it (named in manifest.json). An empty before or now means the value was added or removed.

| Column | Type | Meaning |
|---|---|---|
| `series` | string | Innovation Graph file |
| `economy` | string | ISO 3166-1 alpha-2 code of the economy (GitHub uses EU for the European Union) |
| `quarter` | string | Data quarter, as YYYY-QN |
| `before` | integer | Value in the earlier release |
| `now` | integer | Value in this release |
