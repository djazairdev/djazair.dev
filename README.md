# Hub snapshot

Written by `python -m hub sync` every 6 hours (`.github/workflows/hub.yml`), from the projects
listed in `projects.yml` on `main` and the djazairdev repositories that carry the `djazairdev`
topic. Don't edit it: the next sync replaces it. The site build reads it from this branch
(`.github/scripts/hub-snapshot.sh`).

| File | What it holds |
|---|---|
| `projects.json` | Every listed project: its registry entry (or the one its topics give) and what GitHub says about it |
| `issues.json` | The open `good first issue` and `help wanted` issues of the projects the Hub shows |
| `cache.json` | The ETag of each GitHub answer and what was kept from it, for the next sync |
| `HEALTH.md` | The health report: every flagged or hidden project, why, and since when, and the djazairdev repositories that can't be listed yet |
| `metrics.json` | Contributor counts by quarter, counts only, once `HUB_METRICS` is on (`python -m hub metrics`) |
| `ideas.json` | Project ideas from GitHub Discussions, ranked by votes, and each quarter's count once it closes (`python -m hub ideas`) |

Nothing here identifies a person: no usernames, avatars or assignees, and no issue or idea text
but the title (and an issue's "You'll need" line). See `hub/README.md` on `main`.
