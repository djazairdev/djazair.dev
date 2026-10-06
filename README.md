# Hub snapshot

Written by `python -m hub sync` every 6 hours (`.github/workflows/hub.yml`), from the projects
listed in `projects.yml` on `main`. Don't edit it: the next sync replaces it. The site build
reads it from this branch (`.github/scripts/hub-snapshot.sh`).

| File | What it holds |
|---|---|
| `projects.json` | Every listed project: its registry entry and what GitHub says about it |
| `issues.json` | The open `good first issue` and `help wanted` issues of the projects the Hub shows |
| `cache.json` | The ETag of each GitHub answer and what was kept from it, for the next sync |
| `HEALTH.md` | The health report: every flagged or hidden project, why, and since when |

Nothing here identifies a person: no usernames, avatars or assignees, and no issue text but
the title and its "You'll need" line. See `hub/README.md` on `main`.
