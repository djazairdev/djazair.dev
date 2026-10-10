# MVP implementation plan

**Version 1 · 6 October 2026.** Launch by **30 November 2026**; scope checkpoint on **15 November 2026**. Progress is tracked in [#1](https://github.com/djazairdev/djazair.dev/issues/1) and the milestones below.

This plan turns the PRD (v0.3, 6 October 2026) into ordered, estimated tickets. Every ticket is a GitHub issue, and every designed page is attached to the ticket that builds it ([section 5](#5-designs-and-their-tickets)).

## 1. Changes from the PRD

**French is out of the MVP (decision D20, 6 October 2026).** The site launches in English and Arabic. This replaces D12 and the French parts of §3.3, §6.2, §11 and AC-IDX-6, and the translation reviewers in R2 are needed for Arabic only. The designs no longer show French: the language switcher offers **EN · ع**. Removing French saves about two developer-days (strings, number formats, review and testing).

**The site is built by a small Python builder, not Astro (decision D21, 6 October 2026).** It uses only Python's standard library, like the pipeline and the Hub, so the project has one language and no npm dependency tree. The design generator's chart, tick and unit-map code is reused. Output is the same as planned: static HTML per language, build-time SVG charts and small scripts that only enhance.

**Hub ideas are voted on, and one is adopted each quarter (decision D22, 7 October 2026).** Anyone with a GitHub account votes with the idea's upvote in GitHub Discussions, so there is still no database. Each calendar quarter is a round: the Hub sync saves its count once it closes, and the maintainers adopt the idea with the most votes among those with a champion and at least 10 votes. It gets a repository in the djazairdev organisation. This replaces HUB-07's adoption by the champion alone ([hub-ideas.md](hub-ideas.md)).

**The site is hosted on Cloudflare Workers, not Pages (decision D23, 7 October 2026).** Cloudflare has moved Pages into Workers: its dashboard calls Pages the legacy workflow, and Wrangler hands Pages commands to Workers. The site is a Worker made only of static assets, so no code runs and the pages are the same files. CI deploys it with `wrangler deploy`, and pull requests get preview versions ([deploy.md](deploy.md)). This replaces Cloudflare Pages in the PRD's §10.

**Home's hero replays the years (decision D24, 7 October 2026).** The count runs through the same quarter of each year, from Q1 2020 to the latest, with the year above it, while the unit map adds each year's squares and the three figures under the number (growth, its rank in North Africa and the accounts added) count up or down to that year's in step. It rests on the latest quarter, rewinds and starts again. It is CSS only, generated from the data, so a new year joins the loop by itself. A button beside the year pauses it (WCAG 2.2.2), it rests while it is scrolled out of view, and with reduced motion the hero shows the latest numbers at rest ([accessibility.md](accessibility.md)).

**The Hub no longer requires 3 open beginner issues (decision D27, 9 October 2026).** A project needs issues turned on and the label `good first issue` or `help wanted`, which GitHub adds to every new repository; how many open issues carry it is reported, not required. A listed project with no open beginner issues is no longer flagged or hidden: it stays listed, and the health report names it. The founder's reason: the count shouldn't be forced on maintainers.

**The djazairdev organisation's repositories join the Hub by their topics (decision D29, 10 October 2026).** A public djazairdev repository that carries the `djazairdev` topic, a category topic (`app`, `library`, `tool` or `dataset`) and one to five tag topics is listed at the next Hub sync, without an entry in `projects.yml`. Only the organisation's maintainers can create those repositories or set their topics, and the project template makes the maintainer pledge. Projects outside the organisation still apply by pull request or the issue form, so this extends HUB-01 rather than replacing it. The founder's reason: the Hub showed 1 project while five djazairdev projects were ready, and a new project shouldn't wait on a pull request here ([hub/README.md](../hub/README.md#registry)).

**Should items are planned for Phase 1.1 from the start.** The Topics, Collaboration and External rankings pages, Hub ideas and the localisation section don't fit the capacity below. They come back into the MVP only if the work is ahead at the checkpoint. Quarterly report #1 stays in the MVP as a Should item because the launch is built around it.

## 2. How it is built

```
github/innovationgraph (CC0) ─ daily ─►  pipeline/ (Python 3.12) ─► data/raw/<sha>/      archived, checksummed
                                                  │                 data/derived/<yyyy-qN>/  CSV + JSON (CC0)
GitHub REST API ─ every 6 h ─────────►  hub/ (Python 3.12) ──────► data/derived/hub/
                                                  │
                                                  ▼
                         site/ (Python builder, /en/ + /ar/, build-time SVG charts) ─► Cloudflare Workers ─► djazair.dev
```

| Part | Choice | Why |
|---|---|---|
| Site | Small static builder in Python (standard library only), `/en/` and `/ar/` | One language with the pipeline and Hub, no npm dependencies, and the design generator's chart code is reused; small scripts only enhance (PRD §10, D21) |
| Charts | SVG rendered at build time, light and dark downloads | Readable without JavaScript and light on 4G (§11) |
| Data | Python 3.12 pipeline → `data/derived/` | Reproducible and testable against Appendix A (§9) |
| Hub | Python job every 6 h → `data/derived/hub/`; registry in `projects.yml` | No database, no accounts (§7.2) |
| Hosting | Cloudflare Workers, static assets only, deployed by GitHub Actions only when everything passes | The last good build stays live (§11); Cloudflare has moved Pages into Workers (D23) |
| Analytics | Cloudflare Web Analytics | No cookies, no personal data (§12) |

## 3. Schedule

Capacity at about 30 hours a week is roughly **3.75 developer-days a week**, or **29.5 days** between 7 October and 30 November. The Must tickets add up to **25.5 days** and report #1 to **1.5**, which leaves about **2.5 days** of slack. Estimates are rough; compare them with actual time after M1 and apply the checkpoint cuts early if the work runs more than 20% over. Non-development work (Hub recruitment, the Arabic reviewer, the second admin) runs alongside and isn't counted.

| Milestone | Due | Tickets | Days |
|---|---|---|--:|
| **M1 · Foundations**<br>Site shell in English and Arabic, design tokens, components, chart kit, CI and deploys. | 2026-10-18 | [#2](https://github.com/djazairdev/djazair.dev/issues/2), [#3](https://github.com/djazairdev/djazair.dev/issues/3), [#4](https://github.com/djazairdev/djazair.dev/issues/4), [#5](https://github.com/djazairdev/djazair.dev/issues/5), [#6](https://github.com/djazairdev/djazair.dev/issues/6), [#7](https://github.com/djazairdev/djazair.dev/issues/7), [#8](https://github.com/djazairdev/djazair.dev/issues/8) | 6.25 |
| **M2 · Data pipeline and Hub registry**<br>Innovation Graph ingestion, validation, indicators and tests; the Hub registry and submission checks, so projects can apply early. | 2026-10-28 | [#9](https://github.com/djazairdev/djazair.dev/issues/9), [#10](https://github.com/djazairdev/djazair.dev/issues/10), [#11](https://github.com/djazairdev/djazair.dev/issues/11), [#12](https://github.com/djazairdev/djazair.dev/issues/12), [#13](https://github.com/djazairdev/djazair.dev/issues/13), [#14](https://github.com/djazairdev/djazair.dev/issues/14), [#15](https://github.com/djazairdev/djazair.dev/issues/15), [#16](https://github.com/djazairdev/djazair.dev/issues/16) | 5.25 |
| **M3 · Index pages**<br>Home, Overview, Trends, Peers, Languages, Methodology, About and Data, ready before the 15 November scope checkpoint. | 2026-11-13 | [#17](https://github.com/djazairdev/djazair.dev/issues/17), [#18](https://github.com/djazairdev/djazair.dev/issues/18), [#19](https://github.com/djazairdev/djazair.dev/issues/19), [#20](https://github.com/djazairdev/djazair.dev/issues/20), [#21](https://github.com/djazairdev/djazair.dev/issues/21), [#22](https://github.com/djazairdev/djazair.dev/issues/22), [#23](https://github.com/djazairdev/djazair.dev/issues/23), [#24](https://github.com/djazairdev/djazair.dev/issues/24) | 8.25 |
| **M4 · Hub feed and page**<br>Six-hourly sync, daily health checks, the Hub page and at least 15 listed projects. | 2026-11-20 | [#25](https://github.com/djazairdev/djazair.dev/issues/25), [#26](https://github.com/djazairdev/djazair.dev/issues/26), [#27](https://github.com/djazairdev/djazair.dev/issues/27), [#28](https://github.com/djazairdev/djazair.dev/issues/28) | 2.75 |
| **M5 · Launch**<br>Accessibility and performance passes, Arabic sign-off, latest data, quarterly report #1 and go-live. | 2026-11-30 | [#29](https://github.com/djazairdev/djazair.dev/issues/29), [#30](https://github.com/djazairdev/djazair.dev/issues/30), [#31](https://github.com/djazairdev/djazair.dev/issues/31), [#32](https://github.com/djazairdev/djazair.dev/issues/32), [#33](https://github.com/djazairdev/djazair.dev/issues/33), [#34](https://github.com/djazairdev/djazair.dev/issues/34), [#35](https://github.com/djazairdev/djazair.dev/issues/35) | 4.5 |
| **Phase 1.1**<br>After launch: the Should and Could items not pulled in at the checkpoint, plus the meetups section. | 2027-02-26 | [#36](https://github.com/djazairdev/djazair.dev/issues/36), [#37](https://github.com/djazairdev/djazair.dev/issues/37), [#38](https://github.com/djazairdev/djazair.dev/issues/38), [#39](https://github.com/djazairdev/djazair.dev/issues/39), [#40](https://github.com/djazairdev/djazair.dev/issues/40), [#41](https://github.com/djazairdev/djazair.dev/issues/41), [#42](https://github.com/djazairdev/djazair.dev/issues/42), [#43](https://github.com/djazairdev/djazair.dev/issues/43) | 6.75 |

The Hub registry and submission checks sit in M2, before the pages, so maintainers can apply during November while the rest is built.

## 4. Tickets

### M1 · Foundations (due 2026-10-18)

| # | Ticket | Priority | Days | Depends on | Design |
|--:|---|---|--:|---|---|
| [#2](https://github.com/djazairdev/djazair.dev/issues/2) | Set up the site: Python builder, English and Arabic routes, page shell | Must | 1 | — | [Home — English, desktop](design/home-en-desktop.png), [Home — Arabic, desktop](design/home-ar-desktop.png) |
| [#3](https://github.com/djazairdev/djazair.dev/issues/3) | Implement the design tokens, fonts and base styles | Must | 0.5 | [#2](https://github.com/djazairdev/djazair.dev/issues/2) | [Foundations — colour, type, grid, motif](design/system-foundations.png) |
| [#4](https://github.com/djazairdev/djazair.dev/issues/4) | Build the core components | Must | 1.5 | [#3](https://github.com/djazairdev/djazair.dev/issues/3) | [Components, charts and motion](design/system-components.png) |
| [#5](https://github.com/djazairdev/djazair.dev/issues/5) | Set up interface strings and number formatting | Must | 0.75 | [#2](https://github.com/djazairdev/djazair.dev/issues/2) | [Overview — Arabic, desktop](design/overview-ar-desktop.png), [Overview — Arabic, phone](design/overview-ar-phone.png) |
| [#6](https://github.com/djazairdev/djazair.dev/issues/6) | Set up CI, deploys and repository protection | Must | 0.75 | [#2](https://github.com/djazairdev/djazair.dev/issues/2) | — |
| [#7](https://github.com/djazairdev/djazair.dev/issues/7) | Build the chart kit | Must | 1.5 | [#3](https://github.com/djazairdev/djazair.dev/issues/3) | [Components, charts and motion](design/system-components.png), [Trends — desktop](design/trends-en-desktop.png) |
| [#8](https://github.com/djazairdev/djazair.dev/issues/8) | Remove French from the README, CONTRIBUTING, site README and holding page | Must | 0.25 | — | — |

### M2 · Data pipeline and Hub registry (due 2026-10-28)

| # | Ticket | Priority | Days | Depends on | Design |
|--:|---|---|--:|---|---|
| [#9](https://github.com/djazairdev/djazair.dev/issues/9) | Detect, download and archive Innovation Graph releases | Must | 0.75 | — | — |
| [#10](https://github.com/djazairdev/djazair.dev/issues/10) | Validate releases and fail safely | Must | 0.5 | [#9](https://github.com/djazairdev/djazair.dev/issues/9) | — |
| [#11](https://github.com/djazairdev/djazair.dev/issues/11) | Compute the indicators for every economy | Must | 1.25 | [#10](https://github.com/djazairdev/djazair.dev/issues/10) | — |
| [#12](https://github.com/djazairdev/djazair.dev/issues/12) | Add regression tests against the Q1 2026 baseline | Must | 0.5 | [#11](https://github.com/djazairdev/djazair.dev/issues/11) | — |
| [#13](https://github.com/djazairdev/djazair.dev/issues/13) | Publish derived data as CSV and JSON | Must | 0.5 | [#11](https://github.com/djazairdev/djazair.dev/issues/11) | — |
| [#14](https://github.com/djazairdev/djazair.dev/issues/14) | Schedule the pipeline and rebuild on new data | Must | 0.25 | [#6](https://github.com/djazairdev/djazair.dev/issues/6), [#12](https://github.com/djazairdev/djazair.dev/issues/12), [#13](https://github.com/djazairdev/djazair.dev/issues/13) | — |
| [#15](https://github.com/djazairdev/djazair.dev/issues/15) | Define the Hub registry schema | Must | 0.25 | [#6](https://github.com/djazairdev/djazair.dev/issues/6) | — |
| [#16](https://github.com/djazairdev/djazair.dev/issues/16) | Add the Hub submission flow and inclusion checks | Must | 1.25 | [#15](https://github.com/djazairdev/djazair.dev/issues/15) | [Hub — desktop](design/hub-en-desktop.png), [Hub — phone](design/hub-en-phone.png) |

### M3 · Index pages (due 2026-11-13)

| # | Ticket | Priority | Days | Depends on | Design |
|--:|---|---|--:|---|---|
| [#17](https://github.com/djazairdev/djazair.dev/issues/17) | Design the remaining MVP pages | Must | 0.25 | — | — |
| [#18](https://github.com/djazairdev/djazair.dev/issues/18) | Build the Home page | Must | 1.5 | [#4](https://github.com/djazairdev/djazair.dev/issues/4), [#5](https://github.com/djazairdev/djazair.dev/issues/5), [#7](https://github.com/djazairdev/djazair.dev/issues/7), [#13](https://github.com/djazairdev/djazair.dev/issues/13) | [Home — English, desktop](design/home-en-desktop.png), [Home — English, phone](design/home-en-phone.png), [Home — Arabic, desktop](design/home-ar-desktop.png), [Home — Arabic, phone](design/home-ar-phone.png) |
| [#19](https://github.com/djazairdev/djazair.dev/issues/19) | Build the Index overview page | Must | 1.25 | [#4](https://github.com/djazairdev/djazair.dev/issues/4), [#5](https://github.com/djazairdev/djazair.dev/issues/5), [#7](https://github.com/djazairdev/djazair.dev/issues/7), [#13](https://github.com/djazairdev/djazair.dev/issues/13) | [Overview — English, desktop](design/overview-en-desktop.png), [Overview — English, phone](design/overview-en-phone.png), [Overview — Arabic, desktop](design/overview-ar-desktop.png), [Overview — Arabic, phone](design/overview-ar-phone.png) |
| [#20](https://github.com/djazairdev/djazair.dev/issues/20) | Build the Trends page | Must | 1.5 | [#5](https://github.com/djazairdev/djazair.dev/issues/5), [#7](https://github.com/djazairdev/djazair.dev/issues/7), [#13](https://github.com/djazairdev/djazair.dev/issues/13), [#17](https://github.com/djazairdev/djazair.dev/issues/17) | [Trends — desktop](design/trends-en-desktop.png), [Trends — phone](design/trends-en-phone.png) |
| [#21](https://github.com/djazairdev/djazair.dev/issues/21) | Build the Peers page | Must | 0.75 | [#17](https://github.com/djazairdev/djazair.dev/issues/17), [#19](https://github.com/djazairdev/djazair.dev/issues/19) | [Peers — desktop](design/peers-en-desktop.png), [Peers — phone](design/peers-en-phone.png) |
| [#22](https://github.com/djazairdev/djazair.dev/issues/22) | Build the Languages page | Must | 0.5 | [#7](https://github.com/djazairdev/djazair.dev/issues/7), [#13](https://github.com/djazairdev/djazair.dev/issues/13), [#17](https://github.com/djazairdev/djazair.dev/issues/17) | [Languages — desktop](design/languages-en-desktop.png), [Languages — phone](design/languages-en-phone.png) |
| [#23](https://github.com/djazairdev/djazair.dev/issues/23) | Build the Methodology and About pages | Must | 1.75 | [#4](https://github.com/djazairdev/djazair.dev/issues/4), [#5](https://github.com/djazairdev/djazair.dev/issues/5), [#17](https://github.com/djazairdev/djazair.dev/issues/17) | [Methodology — desktop](design/methodology-en-desktop.png), [Methodology — phone](design/methodology-en-phone.png) |
| [#24](https://github.com/djazairdev/djazair.dev/issues/24) | Build the Data page: downloads, changelog and corrections | Must | 0.75 | [#13](https://github.com/djazairdev/djazair.dev/issues/13), [#17](https://github.com/djazairdev/djazair.dev/issues/17) | [Data — desktop](design/data-en-desktop.png), [Data — phone](design/data-en-phone.png) |

### M4 · Hub feed and page (due 2026-11-20)

| # | Ticket | Priority | Days | Depends on | Design |
|--:|---|---|--:|---|---|
| [#25](https://github.com/djazairdev/djazair.dev/issues/25) | Sync Hub projects and issues every 6 hours | Must | 0.75 | [#6](https://github.com/djazairdev/djazair.dev/issues/6), [#15](https://github.com/djazairdev/djazair.dev/issues/15) | — |
| [#26](https://github.com/djazairdev/djazair.dev/issues/26) | Run daily Hub health checks | Must | 0.5 | [#25](https://github.com/djazairdev/djazair.dev/issues/25) | — |
| [#27](https://github.com/djazairdev/djazair.dev/issues/27) | Build the Hub page | Must | 1.25 | [#4](https://github.com/djazairdev/djazair.dev/issues/4), [#17](https://github.com/djazairdev/djazair.dev/issues/17), [#25](https://github.com/djazairdev/djazair.dev/issues/25) | [Hub — desktop](design/hub-en-desktop.png), [Hub — phone](design/hub-en-phone.png) |
| [#28](https://github.com/djazairdev/djazair.dev/issues/28) | Seed the Hub with at least 15 projects | Must | 0.25 | [#16](https://github.com/djazairdev/djazair.dev/issues/16) | — |

### M5 · Launch (due 2026-11-30)

| # | Ticket | Priority | Days | Depends on | Design |
|--:|---|---|--:|---|---|
| [#29](https://github.com/djazairdev/djazair.dev/issues/29) | Accessibility pass | Must | 0.75 | [#18](https://github.com/djazairdev/djazair.dev/issues/18), [#19](https://github.com/djazairdev/djazair.dev/issues/19), [#20](https://github.com/djazairdev/djazair.dev/issues/20), [#27](https://github.com/djazairdev/djazair.dev/issues/27) | — |
| [#30](https://github.com/djazairdev/djazair.dev/issues/30) | Performance pass | Must | 0.5 | [#18](https://github.com/djazairdev/djazair.dev/issues/18), [#19](https://github.com/djazairdev/djazair.dev/issues/19), [#20](https://github.com/djazairdev/djazair.dev/issues/20), [#27](https://github.com/djazairdev/djazair.dev/issues/27) | — |
| [#31](https://github.com/djazairdev/djazair.dev/issues/31) | Add search and sharing metadata | Must | 0.25 | [#2](https://github.com/djazairdev/djazair.dev/issues/2) | — |
| [#32](https://github.com/djazairdev/djazair.dev/issues/32) | Add analytics, uptime checks and failure alerts | Must | 0.25 | [#14](https://github.com/djazairdev/djazair.dev/issues/14), [#25](https://github.com/djazairdev/djazair.dev/issues/25) | — |
| [#33](https://github.com/djazairdev/djazair.dev/issues/33) | Review and sign off the Arabic text | Must | 0.25 | [#18](https://github.com/djazairdev/djazair.dev/issues/18), [#19](https://github.com/djazairdev/djazair.dev/issues/19), [#23](https://github.com/djazairdev/djazair.dev/issues/23), [#27](https://github.com/djazairdev/djazair.dev/issues/27) | — |
| [#34](https://github.com/djazairdev/djazair.dev/issues/34) | Write and publish quarterly report #1 | Should | 1.5 | [#7](https://github.com/djazairdev/djazair.dev/issues/7), [#17](https://github.com/djazairdev/djazair.dev/issues/17), [#33](https://github.com/djazairdev/djazair.dev/issues/33) | [Report — desktop](design/report-en-desktop.png), [Report — phone](design/report-en-phone.png) |
| [#35](https://github.com/djazairdev/djazair.dev/issues/35) | Launch | Must | 1 | [#21](https://github.com/djazairdev/djazair.dev/issues/21), [#22](https://github.com/djazairdev/djazair.dev/issues/22), [#24](https://github.com/djazairdev/djazair.dev/issues/24), [#28](https://github.com/djazairdev/djazair.dev/issues/28), [#29](https://github.com/djazairdev/djazair.dev/issues/29), [#30](https://github.com/djazairdev/djazair.dev/issues/30), [#31](https://github.com/djazairdev/djazair.dev/issues/31), [#32](https://github.com/djazairdev/djazair.dev/issues/32), [#33](https://github.com/djazairdev/djazair.dev/issues/33) | — |

### Phase 1.1 (due 2027-02-26)

| # | Ticket | Priority | Days | Depends on | Design |
|--:|---|---|--:|---|---|
| [#36](https://github.com/djazairdev/djazair.dev/issues/36) | Build the Topics page | Should | 0.75 | — | [Topics — desktop](design/topics-en-desktop.png), [Topics — phone](design/topics-en-phone.png) |
| [#37](https://github.com/djazairdev/djazair.dev/issues/37) | Build the Collaboration page | Should | 0.75 | — | [Collaboration — desktop](design/collaboration-en-desktop.png), [Collaboration — phone](design/collaboration-en-phone.png) |
| [#38](https://github.com/djazairdev/djazair.dev/issues/38) | Build the External rankings page (GDC26) | Should | 0.75 | — | [Rankings — desktop](design/rankings-en-desktop.png), [Rankings — phone](design/rankings-en-phone.png) |
| [#39](https://github.com/djazairdev/djazair.dev/issues/39) | Open Hub ideas in GitHub Discussions | Should | 1 | — | [Hub ideas — desktop](design/hub-ideas-en-desktop.png), [Hub ideas — phone](design/hub-ideas-en-phone.png) |
| [#40](https://github.com/djazairdev/djazair.dev/issues/40) | Add the Hub localisation section | Should | 0.5 | — | [Localisation — desktop](design/localisation-en-desktop.png), [Localisation — phone](design/localisation-en-phone.png) |
| [#41](https://github.com/djazairdev/djazair.dev/issues/41) | Publish Hub contributor metrics | Should | 1 | — | — |
| [#42](https://github.com/djazairdev/djazair.dev/issues/42) | Add embeddable charts and share images | Could | 1 | — | [Embed panel — desktop](design/embed-en-desktop.png), [Embed panel — phone](design/embed-ar-phone.png), [Embeds](design/embed-pages.png), [Share card](../site/static/share/2026-q1/en.png) |
| [#43](https://github.com/djazairdev/djazair.dev/issues/43) | Move founders.coffee under djazair.dev | Should | 1 | — | [Meetups — desktop](design/meetups-en-desktop.png), [Meetups — phone](design/meetups-en-phone.png) |

## 5. Designs and their tickets

The images in [`docs/design/`](design/) are exported from the djazair.dev design canvas, where the boards stay the source of truth, or taken from the built site ([design/README.md](design/README.md)). Each issue shows the first screen and links the full pages.

| Board | Image | Ticket |
|---|---|---|
| Home — English, desktop | [home-en-desktop.png](design/home-en-desktop.png) | [#18](https://github.com/djazairdev/djazair.dev/issues/18) (also [#2](https://github.com/djazairdev/djazair.dev/issues/2)) |
| Home — English, phone | [home-en-phone.png](design/home-en-phone.png) | [#18](https://github.com/djazairdev/djazair.dev/issues/18) |
| Home — Arabic, desktop | [home-ar-desktop.png](design/home-ar-desktop.png) | [#18](https://github.com/djazairdev/djazair.dev/issues/18) (also [#2](https://github.com/djazairdev/djazair.dev/issues/2)) |
| Home — Arabic, phone | [home-ar-phone.png](design/home-ar-phone.png) | [#18](https://github.com/djazairdev/djazair.dev/issues/18) |
| Overview — English, desktop | [overview-en-desktop.png](design/overview-en-desktop.png) | [#19](https://github.com/djazairdev/djazair.dev/issues/19) |
| Overview — English, phone | [overview-en-phone.png](design/overview-en-phone.png) | [#19](https://github.com/djazairdev/djazair.dev/issues/19) |
| Overview — Arabic, desktop | [overview-ar-desktop.png](design/overview-ar-desktop.png) | [#19](https://github.com/djazairdev/djazair.dev/issues/19) (also [#5](https://github.com/djazairdev/djazair.dev/issues/5)) |
| Overview — Arabic, phone | [overview-ar-phone.png](design/overview-ar-phone.png) | [#19](https://github.com/djazairdev/djazair.dev/issues/19) (also [#5](https://github.com/djazairdev/djazair.dev/issues/5)) |
| Trends — desktop | [trends-en-desktop.png](design/trends-en-desktop.png) | [#20](https://github.com/djazairdev/djazair.dev/issues/20) (also [#7](https://github.com/djazairdev/djazair.dev/issues/7)) |
| Trends — phone | [trends-en-phone.png](design/trends-en-phone.png) | [#20](https://github.com/djazairdev/djazair.dev/issues/20) |
| Hub — desktop | [hub-en-desktop.png](design/hub-en-desktop.png) | [#27](https://github.com/djazairdev/djazair.dev/issues/27) (also [#16](https://github.com/djazairdev/djazair.dev/issues/16)) |
| Hub — phone | [hub-en-phone.png](design/hub-en-phone.png) | [#27](https://github.com/djazairdev/djazair.dev/issues/27) (also [#16](https://github.com/djazairdev/djazair.dev/issues/16)) |
| Methodology — desktop | [methodology-en-desktop.png](design/methodology-en-desktop.png) | [#23](https://github.com/djazairdev/djazair.dev/issues/23) |
| Methodology — phone | [methodology-en-phone.png](design/methodology-en-phone.png) | [#23](https://github.com/djazairdev/djazair.dev/issues/23) |
| Foundations — colour, type, grid, motif | [system-foundations.png](design/system-foundations.png) | [#3](https://github.com/djazairdev/djazair.dev/issues/3) |
| Components, charts and motion | [system-components.png](design/system-components.png) | [#4](https://github.com/djazairdev/djazair.dev/issues/4) (also [#7](https://github.com/djazairdev/djazair.dev/issues/7)) |
| State: Indexed to 2020 Q1 = 100, Morocco brought forward, crosshair on 2024 Q2 | [trends-en-desktop-indexed-morocco.png](design/trends-en-desktop-indexed-morocco.png) | [#20](https://github.com/djazairdev/djazair.dev/issues/20) |
| State: Pushes per account, Kenya brought forward, crosshair on 2021 Q3 | [trends-en-desktop-pushes-kenya.png](design/trends-en-desktop-pushes-kenya.png) | [#20](https://github.com/djazairdev/djazair.dev/issues/20) |
| State: Filtered: good first issue + Markdown | [hub-en-desktop-filtered.png](design/hub-en-desktop-filtered.png) | [#27](https://github.com/djazairdev/djazair.dev/issues/27) |
| State: Search: "kotlin" | [hub-en-desktop-search.png](design/hub-en-desktop-search.png) | [#27](https://github.com/djazairdev/djazair.dev/issues/27) |
| Peers — English, desktop (built site) | [peers-en-desktop.png](design/peers-en-desktop.png) | [#21](https://github.com/djazairdev/djazair.dev/issues/21) |
| Peers — English, phone (built site) | [peers-en-phone.png](design/peers-en-phone.png) | [#21](https://github.com/djazairdev/djazair.dev/issues/21) |
| Languages — English, desktop (built site) | [languages-en-desktop.png](design/languages-en-desktop.png) | [#22](https://github.com/djazairdev/djazair.dev/issues/22) |
| Languages — English, phone (built site) | [languages-en-phone.png](design/languages-en-phone.png) | [#22](https://github.com/djazairdev/djazair.dev/issues/22) |
| Data — English, desktop (built site) | [data-en-desktop.png](design/data-en-desktop.png) | [#24](https://github.com/djazairdev/djazair.dev/issues/24) |
| Data — English, phone (built site) | [data-en-phone.png](design/data-en-phone.png) | [#24](https://github.com/djazairdev/djazair.dev/issues/24) |
| About — English, desktop (built site) | [about-en-desktop.png](design/about-en-desktop.png) | [#23](https://github.com/djazairdev/djazair.dev/issues/23) |
| About — English, phone (built site) | [about-en-phone.png](design/about-en-phone.png) | [#23](https://github.com/djazairdev/djazair.dev/issues/23) |
| Reports — English, desktop (built site) | [reports-en-desktop.png](design/reports-en-desktop.png) | [#34](https://github.com/djazairdev/djazair.dev/issues/34) |
| Reports — English, phone (built site) | [reports-en-phone.png](design/reports-en-phone.png) | [#34](https://github.com/djazairdev/djazair.dev/issues/34) |
| Report #1 — English, desktop (built site) | [report-en-desktop.png](design/report-en-desktop.png) | [#34](https://github.com/djazairdev/djazair.dev/issues/34) |
| Report #1 — English, phone (built site) | [report-en-phone.png](design/report-en-phone.png) | [#34](https://github.com/djazairdev/djazair.dev/issues/34) |
| Trends — Arabic, desktop (built site) | [trends-ar-desktop.png](design/trends-ar-desktop.png) | [#20](https://github.com/djazairdev/djazair.dev/issues/20) |
| Trends — Arabic, phone (built site) | [trends-ar-phone.png](design/trends-ar-phone.png) | [#20](https://github.com/djazairdev/djazair.dev/issues/20) |
| Hub — Arabic, desktop (built site) | [hub-ar-desktop.png](design/hub-ar-desktop.png) | [#27](https://github.com/djazairdev/djazair.dev/issues/27) |
| Hub — Arabic, phone (built site) | [hub-ar-phone.png](design/hub-ar-phone.png) | [#27](https://github.com/djazairdev/djazair.dev/issues/27) |
| Methodology — Arabic, desktop (built site) | [methodology-ar-desktop.png](design/methodology-ar-desktop.png) | [#23](https://github.com/djazairdev/djazair.dev/issues/23) |
| Methodology — Arabic, phone (built site) | [methodology-ar-phone.png](design/methodology-ar-phone.png) | [#23](https://github.com/djazairdev/djazair.dev/issues/23) |
| 404 — desktop (built site) | [404-desktop.png](design/404-desktop.png) | [#2](https://github.com/djazairdev/djazair.dev/issues/2) |
| 404 — phone (built site) | [404-phone.png](design/404-phone.png) | [#2](https://github.com/djazairdev/djazair.dev/issues/2) |
| Topics — English, desktop (built site) | [topics-en-desktop.png](design/topics-en-desktop.png) | [#36](https://github.com/djazairdev/djazair.dev/issues/36) |
| Topics — English, phone (built site) | [topics-en-phone.png](design/topics-en-phone.png) | [#36](https://github.com/djazairdev/djazair.dev/issues/36) |
| Collaboration — English, desktop (built site) | [collaboration-en-desktop.png](design/collaboration-en-desktop.png) | [#37](https://github.com/djazairdev/djazair.dev/issues/37) |
| Collaboration — English, phone (built site) | [collaboration-en-phone.png](design/collaboration-en-phone.png) | [#37](https://github.com/djazairdev/djazair.dev/issues/37) |
| Rankings — English, desktop (built site) | [rankings-en-desktop.png](design/rankings-en-desktop.png) | [#38](https://github.com/djazairdev/djazair.dev/issues/38) |
| Rankings — English, phone (built site) | [rankings-en-phone.png](design/rankings-en-phone.png) | [#38](https://github.com/djazairdev/djazair.dev/issues/38) |
| Hub ideas section — desktop (built site, `HUB_IDEAS` on) | [hub-ideas-en-desktop.png](design/hub-ideas-en-desktop.png) | [#39](https://github.com/djazairdev/djazair.dev/issues/39) |
| Hub ideas section — phone (built site, `HUB_IDEAS` on) | [hub-ideas-en-phone.png](design/hub-ideas-en-phone.png) | [#39](https://github.com/djazairdev/djazair.dev/issues/39) |
| Localisation — English, desktop (built site) | [localisation-en-desktop.png](design/localisation-en-desktop.png) | [#40](https://github.com/djazairdev/djazair.dev/issues/40) |
| Localisation — English, phone (built site) | [localisation-en-phone.png](design/localisation-en-phone.png) | [#40](https://github.com/djazairdev/djazair.dev/issues/40) |
| Embed panel — English, desktop (built site) | [embed-en-desktop.png](design/embed-en-desktop.png) | [#42](https://github.com/djazairdev/djazair.dev/issues/42) |
| Embed panel — Arabic, phone (built site) | [embed-ar-phone.png](design/embed-ar-phone.png) | [#42](https://github.com/djazairdev/djazair.dev/issues/42) |
| Embeds on another site (built site) | [embed-pages.png](design/embed-pages.png) | [#42](https://github.com/djazairdev/djazair.dev/issues/42) |
| Share card for Q1 2026 — English and Arabic | [en.png](../site/static/share/2026-q1/en.png), [ar.png](../site/static/share/2026-q1/ar.png) | [#42](https://github.com/djazairdev/djazair.dev/issues/42) |
| Meetups — English, desktop (built site) | [meetups-en-desktop.png](design/meetups-en-desktop.png) | [#43](https://github.com/djazairdev/djazair.dev/issues/43) |
| Meetups — English, phone (built site) | [meetups-en-phone.png](design/meetups-en-phone.png) | [#43](https://github.com/djazairdev/djazair.dev/issues/43) |

Peers, Languages, Data, About, Reports, the report page and 404, the Arabic Trends, Hub and Methodology, and in Phase 1.1 Topics, Collaboration, Rankings, the Hub's ideas and localisation, embeds and Meetups, were built straight in the design system. Their pictures, marked *built site*, are taken from the built pages with `site/tools/screens.py` ([#17](https://github.com/djazairdev/djazair.dev/issues/17)).

## 6. Definition of done

Every MVP ticket that ships a page or feature also meets these:

1. **English and Arabic.** Correct `lang` and `dir`; the layout mirrors in Arabic; numbers use `en` or `ar-DZ` (Western digits); chart time axes stay left to right and maps are never mirrored.
2. **Matches the design** at 390 px and 1440 px and holds up in between. Phones never scroll sideways; wide tables scroll inside their card.
3. **Every number shows its source and data quarter** (IDX-13).
4. **Accessible:** keyboard operable with visible focus, a data table for every chart, WCAG AA contrast, and no motion under reduced motion.
5. **Works without JavaScript;** interactions only enhance the page.
6. **Within budget:** ≤ 300 KB compressed per page excluding fonts; Overview LCP ≤ 2.5 s on a mid-range Android phone over 4G.
7. **Editorial rules:** "developer accounts" in headlines, group medians before single neighbours, and no claim GitHub didn't make.
8. **No personal data;** Hub cards never show usernames.
9. **Tested:** data logic has unit tests and CI is green.

## 7. Scope checkpoint, 15 November

M3 should be finished by the checkpoint. If it isn't, the launch keeps its date and these move out, in this order:

1. Report #1 shrinks to a short note, or moves to Phase 1.1 with report #2.
2. Motion polish beyond the defaults (scroll-linked drawing, the ticker).
3. The Languages chart ships as a table first.
4. Peers sorting ships as a fixed order.

If the work is ahead, Phase 1.1 Should tickets come in, in this order: Topics, External rankings, Collaboration, Hub ideas, localisation section.

## 8. Risks to the plan

| Risk | Mitigation |
|---|---|
| Little slack (about 2.5 days) | Velocity check after M1; checkpoint cuts are agreed in advance (section 7) |
| The Q2 2026 release slips past launch | Launch with Q1 2026 data and update when Q2 lands (PRD §1) |
| No Arabic reviewer by November | Line one up in October (R2); unreviewed strings fall back to English with a notice |
| The Hub launches with fewer than 15 projects | Submission checks ship in M2 so recruitment runs all of November; seed ticket tracks every invitation |
| Design drift between canvas and code | Tokens come from one table; designs are re-exported here when a board changes |

## 9. Keeping this plan current

- Ticket status lives in GitHub. This file changes only when scope, estimates or dates change; note each change below.
- When a board changes on the design canvas, re-export it to `docs/design/` with the same file name so the issues update. When a page built without a board changes, retake its pictures with `site/tools/screens.py`.

| Date | Change |
|---|---|
| 6 October 2026 | Version 1. French removed from the MVP (D20). |
| 6 October 2026 | The site uses a Python static builder instead of Astro (D21); [#2](https://github.com/djazairdev/djazair.dev/issues/2) renamed. |
| 7 October 2026 | [#17](https://github.com/djazairdev/djazair.dev/issues/17): the pages without a canvas board were built straight in the design system, so their designs in `docs/design/` are pictures of the built pages (`site/tools/screens.py`). |
| 7 October 2026 | Phase 1.1 pages built ahead of the checkpoint: Topics ([#36](https://github.com/djazairdev/djazair.dev/issues/36)), Collaboration ([#37](https://github.com/djazairdev/djazair.dev/issues/37)) and External rankings ([#38](https://github.com/djazairdev/djazair.dev/issues/38)), with pictures of the built pages. They ship with the launch unless they are hidden from the navigation. |
| 7 October 2026 | The rest of Phase 1.1 built ahead of the checkpoint: Hub ideas ([#39](https://github.com/djazairdev/djazair.dev/issues/39), off until Discussions is on), the localisation page ([#40](https://github.com/djazairdev/djazair.dev/issues/40)), Hub contributor metrics ([#41](https://github.com/djazairdev/djazair.dev/issues/41), off until counsel agrees), embeds and per-quarter share images ([#42](https://github.com/djazairdev/djazair.dev/issues/42)) and a meetups page ([#43](https://github.com/djazairdev/djazair.dev/issues/43)). founders.coffee has grown into its own app, with accounts, RSVPs and three countries, so moving its domain here waits for the founder ([meetups.md](meetups.md)). Until then the meetups page links to it. |
| 7 October 2026 | Hub ideas get a vote (D22): GitHub Discussions upvotes, a round each quarter and one idea adopted by the organisation, still without a database. [#39](https://github.com/djazairdev/djazair.dev/issues/39) grows from 0.5 to 1 day. |
| 7 October 2026 | Hosting moves from Cloudflare Pages to Cloudflare Workers, static assets only (D23). The holding page went up on djazair.dev and the site on its workers.dev address, deployed by hand; CI deploys once the API token is in ([#6](https://github.com/djazairdev/djazair.dev/issues/6)). |
| 7 October 2026 | Home's hero replays the years in a loop, with a pause button (D24): the count, the map and the three figures under the count follow the year. It was counting up from the year earlier only. |
| 9 October 2026 | The Hub's issues check asks for a beginner label, not 3 open issues, and no open beginner issues no longer hides a project (D27). |
| 10 October 2026 | djazairdev's repositories join the Hub by their topics, without a `projects.yml` entry (D29). |
