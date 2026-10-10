# Documentation

## Repository layout

| Path | What it holds |
|---|---|
| `pipeline/` | Python: downloads Innovation Graph releases and computes the Index |
| `hub/` | Python: syncs Hub projects and runs inclusion and health checks ([hub/README.md](../hub/README.md)) |
| `data/raw/` | Archived source files, with checksums |
| `data/derived/` | Published indicators (CSV and JSON) |
| `projects.yml` | The Hub registry |
| `site/` | The static website |
| `content/` | Quarterly reports and the meetups section |
| `docs/` | This documentation |
| `.github/workflows/` | Scheduled jobs and deployment |

## Guides

| Guide | What it covers |
|---|---|
| [implementation-plan.md](implementation-plan.md) | The work for the first version, and the decisions (D1, D2, …) |
| [design/](design/) | The page designs and the design system |
| [deploy.md](deploy.md) | How the site is deployed to Cloudflare Workers |
| [accessibility.md](accessibility.md) | The accessibility promises and the checks to make by hand |
| [performance.md](performance.md) | The performance budgets |
| [arabic-review.md](arabic-review.md) | How the Arabic text is reviewed |
| [reports.md](reports.md) | How quarterly reports are written and checked |
| [hub-ideas.md](hub-ideas.md) | How project ideas are proposed and voted on |
| [discovery.md](discovery.md) | Structured data, sitemaps and `llms.txt` |
| [meetups.md](meetups.md) | The meetups section and founders.coffee |
| [launch.md](launch.md) | The launch checklist |
