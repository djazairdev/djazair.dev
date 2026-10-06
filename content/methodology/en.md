<!-- The Methodology page (ticket #23; PRD §9). Each ## section is one numbered section with
     its id; ::: blocks are drawn by site/djsite/pages/methodology.py, and {{name}} values come
     from the data. Formulas must match pipeline/indicators.py: tests/test_methodology.py checks. -->

## What the Index is {#what}

The Algeria Developer Index is a quarterly scorecard of Algeria’s developer ecosystem on GitHub. It compares Algeria with North Africa and with Africa’s largest developer communities, using public data only.

::: callout
### A scorecard, not a score
Version 1 has no combined score. Each indicator stands on its own, with its rank and peer medians. A combined score may come later, but only with a published formula, normalisation and sensitivity analysis.
:::

::: cards
### Public data only
No data from djazair.dev users, and nothing about individuals.
### Reproducible
Code under MIT, derived data under CC0, every source release archived with checksums.
### Peers first
Each number is read against group medians before anything else.
:::

## Sources {#sources}

Four public sources. The scorecard uses the Innovation Graph and World Bank population, and the GitHub API feeds the Project Hub. GDC26 is kept for comparisons with GitHub’s own country rankings.

| Source | What it provides | Licence | Updated |
|---|---|---|---|
| **GitHub Innovation Graph** | Eight files covering {{economies}} economies since {{first_quarter}}: developers, pushes, repositories, organisations, languages, topics, licences and collaborators. | CC0 | Quarterly, 3 to 4.5 months after the quarter |
| **GDC26 supplementary data** | VPN-corrected pushes and pushes per 1,000 working-age people, top 10 per region. | CC0 | One-off, September 2026 |
| **World Bank** | Population and working-age population. | CC BY 4.0 | Yearly |
| **GitHub REST API** | Hub only: repository details, issues and pull requests. | GitHub terms | Every 6 hours |

::: releases
- 2025-08-13
- 2025-11-04
- 2026-01-28
- 2026-05-07
- 2026-07-07
:::

## Indicators and formulas {#indicators}

Notation: `c` is an economy, `q` a quarter and `q-4` the same quarter a year earlier. Every indicator is computed for every economy, because ranks and medians need them all.

::: formulas
### Developer accounts {#accounts}
`developers(c, q)`
Accounts located in the economy at the end of the quarter. A running total, located by network address. Includes inactive accounts; excludes bots and spam.
### Year-on-year growth {#yoy}
`developers(c, q) / developers(c, q-4) - 1`
Compares a quarter with the same quarter a year earlier, so seasonal swings cancel out.
### Growth since 2020 {#since_2020}
`developers(c, q) / developers(c, 2020 Q1) - 1`
Also shown as an index, with 2020 Q1 = 100, on the [Trends page](route:trends).
### Pushes per account {#pushes_per_account}
`git_pushes(c, q) / developers(c, q)`
Pushes during the quarter divided by all accounts. A four-quarter average smooths spikes: `Σ pushes over the last 4 quarters / mean accounts over them / 4`.
### Public repositories per account {#repos_per_account}
`repositories(c, q) / developers(c, q)`
Both are running totals. Public repositories only.
### Organisations per account {#orgs_per_account}
`organizations(c, q) / developers(c, q)`
Both are running totals.
### Accounts per million people {#accounts_per_million}
`developers(c, q) / population(c) × 10⁶`
Population from the World Bank, latest year: {{population_year}} for {{quarter}} data.
### Topics above the threshold {#topics}
`count(topics(c, q))`
GitHub publishes a topic only once 100 or more developers use it.
### Developers pushing in a language {#languages}
`num_pushers(c, q, language)`
Developers who pushed in the language during the quarter. One developer can push in several languages, so the counts can’t be added up. GitHub lists a language once 100 or more developers push in it.
### Peer median {#median}
`median(indicator over group members with data)`
The middle value, so one large economy can’t pull it far.
### Rank {#rank}
`position in descending order`
Within the ranking group. Ties share a rank.
:::

::: example
- yoy: Year-on-year growth
- pushes_per_account: Pushes per account
- repos_per_account: Repositories per account
- orgs_per_account: Organisations per account
- accounts_per_million: Accounts per million people
:::

## Peer groups {#peer-groups}

::: groups
### North Africa {#north_africa}
Medians and ranks. Every member counts, whatever its size.
### Core peers {#core_peers}
Comparison table and medians. North African neighbours with large ecosystems, plus Africa’s largest.
### Africa ranking group {#africa}
African economies with at least {{africa_min}} accounts a year earlier ({{africa_n}} in {{quarter}}).

Ranks and medians. The minimum size keeps small bases from distorting growth.
:::

We compare Algeria with group medians rather than with one neighbour at a time. Medians are steadier, and single-country comparisons can read as rivalry.

## Known limitations {#limitations}

Read these before quoting a number. They are also summarised next to each chart.

::: limits
### What “developer accounts” counts
- **Accounts are not active developers.** The count is a running total that includes dormant accounts.
- **Location is by network address,** so VPN use distorts it. GitHub’s GDC26 data corrects pushes using profile locations; the main dataset does not.
- **Profile location barely affects the headline counts.** Octoverse’s country totals closely match the Innovation Graph’s network-address counts: Morocco 560K against Octoverse 2024’s “>556K”, Kenya 395K against “>393K”. Only 12–16k accounts mention Algeria in their profile.
### Repositories and pushes
- **Repositories counts public repositories only.**
- **A push can contain many commits,** and edits in GitHub’s web interface count as pushes.
- **Pushes are rising sharply everywhere:** the US {{pushes_us}} and Algeria {{pushes_dz}} year on year in {{quarter}}. This is likely linked to AI coding tools, which is why peer comparisons come first.
### Thresholds and coverage
- **A 100-developer threshold** hides small categories. Only {{dz_topics}} of Algeria’s topics clear it.
- **Translation work** done on platforms like Weblate or Crowdin is pushed from their servers, so it doesn’t count as Algerian activity.
### Timing
- **The data lags** by 3 to 4.5 months after each quarter ends.
- **Revisions are flagged.** Each release is archived, and any past value a new release changes is listed in the changelog. {{revisions}}
:::

## Update process {#updates}

Steps 1 to 5 run automatically on GitHub Actions. Step 6 is editorial and needs people.

::: steps
1. `detect` [Daily] Look for a new commit to the Innovation Graph’s data folder. If there is one, download every file, record its SHA-256 checksum and archive it. Archived releases are never overwritten.
2. `validate` [On release] Check columns, types and quarter coverage. If anything fails, the last good site stays live and an issue is opened on GitHub.
3. `compute` [On release] Compute every indicator for every economy and quarter, written as CSV and JSON under `data/derived/`.
4. `test` [On release] The published 2026 Q1 baseline must still match exactly. A changed past value is flagged as a revision for editorial review.
5. `deploy` [Within 24 hours] The data pages build and deploy automatically.
6. `report` [Within 14 days] [Human step] The quarterly report is drafted, translated, checked by a second person and a fluent reviewer, then published in Arabic and English.
:::

## Corrections and citation {#corrections}

Before anything is published, someone other than the author checks the numbers against the published data. If you find an error, open an issue or write to {{contact}}. Corrections are published within 7 days, and the log keeps every one.

::: logs
:::

::: cite
:::
