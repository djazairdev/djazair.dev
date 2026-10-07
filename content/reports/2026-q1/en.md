---
title: Algeria’s developer accounts, Q1 2026
standfirst: Algeria had {{accounts}} developer accounts on GitHub at the end of March 2026, {{yoy}} more than a year earlier. Growth has sped up for {{streak}} in a row and kept pace with North Africa. Activity per account rose fast, but it still trails the region.
---

## Headline numbers {#numbers}

::: numbers
- accounts
- growth
- pushes
- permillion
:::

Every figure is for {{quarter}}, from the GitHub Innovation Graph data released on {{release_date}}. Accounts per million people use the World Bank’s population estimate for {{population_year}}.

::: figure units
:::

## What changed {#changes}

**On the previous quarter.** Algeria added {{added_quarter}} developer accounts between {{previous_quarter}} and {{quarter}}, a rise of {{change_quarter}}. Year-on-year growth went from {{yoy_previous}} to {{yoy}}: it has now sped up for {{streak}} in a row. Pushes per account went from {{pushes_previous}} to {{pushes}}.

**On a year earlier.** The count grew by {{added_year}} accounts, or {{yoy}}; a year earlier, growth was {{yoy_year_earlier}}. Pushes per account more than doubled, from {{pushes_year_earlier}} to {{pushes}}. Two ratios fell: public repositories per account, from {{repos_year_earlier}} to {{repos}}, and organisations per account, from {{orgs_year_earlier}} to {{orgs}}. Accounts grew faster than repositories and organisations, and the same happened in the North African and African medians.

::: changes
:::

**The region sped up too.** Over the same year, the North African median growth rate rose from {{yoy_na_year_earlier}} to {{yoy_na}}, and the African median from {{yoy_af_year_earlier}} to {{yoy_af}}. Algeria has grown as fast as the North African median or faster since late 2023, but more slowly than the African median since Q2 2024.

::: figure growth
:::

**Pushes rose everywhere.** The jump in pushes per account isn’t Algeria’s alone: the North African median rose from {{pushes_na_year_earlier}} to {{pushes_na}} over the same year, and the African median from {{pushes_af_year_earlier}} to {{pushes_af}}. Pushes are rising sharply across GitHub, probably helped by AI coding tools, so the comparison with peers says more than the rise itself. On that comparison, Algeria is still behind both medians.

::: figure pushes
:::

## Algeria and its peers {#peers}

We compare Algeria with the median of each peer group rather than with one neighbour at a time ([how the groups are made](route:methodology#peer-groups)). In {{quarter}}:

- **Above the North African median:** developer accounts ({{accounts}} against {{accounts_na}}; {{rank.accounts.na}} in North Africa) and growth ({{yoy}} against {{yoy_na}}; {{rank.yoy.na}}).
- **At the median:** accounts per million people ({{permillion}}) and organisations per account ({{orgs}}). On both, Algeria is the middle of the seven North African economies.
- **Below it:** pushes per account ({{pushes}} against {{pushes_na}}) and public repositories per account ({{repos}} against {{repos_na}}).

Among Africa’s {{n_af}} largest developer communities, Algeria is {{rank.accounts.af}} by number of accounts but {{rank.yoy.af}} by growth, {{rank.pushes.af}} by pushes per account and {{rank.repos.af}} by repositories per account. Accounts are being opened quickly; the activity on them is among the lowest in the group.

::: peers
:::

::: figure accounts
:::

## Deep dive: languages {#languages}

For each language, GitHub counts the developers who pushed code in it during the quarter. One developer can count in several languages, so the numbers overlap and can’t be added up.

**HTML has led in every quarter since {{first_quarter}}.** {{lang.html.pushers}} developers pushed HTML in {{quarter}}, ahead of JavaScript ({{lang.javascript.pushers}}) and CSS ({{lang.css.pushers}}).

**Python and TypeScript more than doubled in a year.** Python is {{lang.python.ord}}, with {{lang.python.pushers}} developers ({{lang.python.change}}). TypeScript is {{lang.typescript.ord}}, with {{lang.typescript.pushers}} ({{lang.typescript.change}}); in {{first_quarter}} it was {{lang.typescript.ord_first}}.

**Tools entered the top ten.** Dockerfile rose from {{lang.dockerfile.ord_year_earlier}} to {{lang.dockerfile.ord}} ({{lang.dockerfile.change}}), and Jupyter Notebook from {{lang.jupyter_notebook.ord_year_earlier}} to {{lang.jupyter_notebook.ord}}. Java and C++ dropped out. Java was {{lang.java.ord_first}} in {{first_quarter}}; it is {{lang.java.ord}} now.

The shift is towards web front ends (TypeScript), data work (Python, Jupyter Notebook) and deployment (Dockerfile, Shell).

::: figure languages
:::

::: languages
:::

## Caveats {#caveats}

- **Accounts, not people.** The count is a running total of accounts placed in Algeria. It includes dormant accounts, and one person can have several.
- **Location is by network address.** Developers who use a VPN, or who work from abroad, can be counted elsewhere.
- **Pushes measure activity, not quality.** A push can hold many commits, and pushes are rising everywhere.
- **The data lags.** {{quarter}} data was published on {{release_date}}. This first report comes later than the 14 days we aim for, because djazair.dev opened after that release.
- **Figures can be revised.** GitHub can change past values in a later release. We archive every release and list changes in the [changelog](route:data#changelog); a correction to this report goes in the [corrections log](route:data#corrections) within 7 days.
- **Medians move.** Each peer median is recomputed every quarter from the members with data.

## What djazair.dev did {#djazair}

This is our first report. Since GitHub published the {{quarter}} data, we have:

- opened the [Algeria Developer Index](route:overview): six indicators compared with North Africa and Africa, quarterly trends since {{first_quarter}} and languages, with the data behind every table and chart free to reuse (CC0);
- published the [methodology](route:methodology): sources, formulas, peer groups, known limitations and how we correct mistakes;
- opened the [Project Hub](route:hub), which lists open-source projects with a link to Algeria and their beginner-friendly issues.

::: hub
:::

The Hub is small for now. We are inviting maintainers to [list their projects](route:hub#list): it takes a single pull request.

## Press kit {#press}

The five charts in this report, ready to publish, with the data behind them and a summary of the methodology. Charts and text are CC BY 4.0: credit “djazair.dev”. The data is CC0.

::: presskit
:::

::: method
- **Source:** GitHub Innovation Graph, {{quarter}} data, released on {{release_date}} (CC0). Population: World Bank, {{population_year}} (CC BY 4.0).
- **Developer accounts:** accounts that GitHub places in Algeria by network address at the end of the quarter, dormant ones included. They are not a count of people.
- **Growth:** the count compared with the same quarter a year earlier.
- **Per-account ratios:** pushes during the quarter, public repositories and organisations, each divided by the number of accounts.
- **Peer groups:** North Africa (seven economies), six core peers (Morocco, Tunisia, Egypt, Nigeria, Kenya and South Africa) and the {{n_af}} African economies with at least 20,000 accounts a year earlier. We compare with group medians, not with single countries.
- **Corrections:** published in the corrections log within 7 days.
:::

::: cite
:::

Questions about the report: {{contact}}.
