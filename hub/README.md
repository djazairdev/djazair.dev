# hub

The Project Hub (PRD §8). Python 3.12+, standard library only.

```sh
python3 -m hub check-registry                    # validate projects.yml against hub/projects.schema.json
python3 -m hub check-project owner/name --pledge # run the inclusion checks on one repository
python3 -m hub check-submission --proposed FILE  # check the entries a new projects.yml adds or changes
python3 -m hub check-issue --body-file FILE      # check a request made with the issue form
python3 -m hub sync                              # fetch the listed projects and their beginner issues
python3 -m hub metrics                           # count new contributors and response times (counts only)
```

Set `GITHUB_TOKEN` for the higher API rate limit; public data needs no token.

## Registry

[`projects.yml`](../projects.yml) lists the projects, one entry each: `repository`, `category`, `tags`, `maintainer_pledge` and `added` (PRD HUB-01). Language, licence and activity are read from GitHub, so they aren't stored. [CONTRIBUTING.md](../CONTRIBUTING.md#list-a-project-in-the-hub) explains each field and lists the tags.

| File | What it does |
|---|---|
| `projects.schema.json` | The JSON Schema for `projects.yml`. Editors with a YAML language server use it while you type |
| `registry.py` | Reads `projects.yml`, checks it against the schema, then checks what a schema can't: a repository listed twice (GitHub names ignore case) and a date in the future |
| `miniyaml.py` | A strict reader for the part of YAML the registry uses. Anything else (anchors, tags, block scalars, tabs, duplicate keys) is an error with its line number |
| `schemacheck.py` | Applies the JSON Schema keywords the schema uses, and refuses a schema that uses any other, so no check is silently skipped. Errors name the field (`projects[2] (owner/name).category`) and say what to write instead |

CI runs `python -m hub check-registry` on every pull request. In GitHub Actions each problem is also an annotation on the line to fix.

## Submissions and inclusion checks

A project applies with a pull request that adds its entry, or with the *List a project in the Hub* issue form (`.github/ISSUE_TEMPLATE/hub-listing.yml`), which applies the `hub listing` label (PRD HUB-02). Neither needs a djazair.dev account (AC-HUB-2).

The `Hub listing check` workflow (`.github/workflows/hub-listing.yml`) then runs the seven inclusion checks and comments with the result, and updates that comment each time it runs again (HUB-03):

| Check | How |
|---|---|
| `licence` | GitHub's licence detection: an OSI-approved SPDX licence (or an open data licence for a dataset) |
| `activity` | The last commit on the default branch is at most 90 days old, and the repository isn't archived |
| `docs` | GitHub's community profile finds a README and a CONTRIBUTING file (a code of conduct is noted, not required) |
| `issues` | At least 3 open issues, not pull requests, labelled `good first issue` or `help wanted` |
| `pledge` | `maintainer_pledge: true`, or the pledge ticked in the issue form |
| `topic` | The repository carries the topic `djazairdev` |
| `relevance` | A person checks this; a listed project counts as checked |

Pull requests are checked with `pull_request_target`, so the bot can comment on pull requests from forks. That job runs the base branch's code only: it reads the proposed `projects.yml` through the API and parses it as data, and nothing from the pull request runs. Issue text reaches the script through an environment variable, never inside the script. Submitted text in comments is made inert (no HTML, no @mentions).

| File | What it does |
|---|---|
| `github.py` | A small GitHub REST client: retries, rate limits, and the comment that is created once and then updated |
| `checks.py` | The seven checks; each failure says what was found and how to fix it. The health checks use the same 90 days and topic |
| `submission.py` | Finds the entries a pull request adds or changes, reads the issue form, and writes the comment |

## Sync (issues feed)

`python -m hub sync` builds the Hub's data (PRD HUB-04, HUB-05). For each project in `projects.yml` it asks GitHub for the repository (description, primary language, licence, topics, archived), its last commit on the default branch, and its open issues labelled `good first issue` or `help wanted`, pull requests left out. It writes a snapshot to `data/derived/hub/`:

| File | What it holds |
|---|---|
| `projects.json` | Every listed project: its registry entry, what GitHub says about it, its number of open beginner issues, and `shown` |
| `issues.json` | The open beginner issues of the projects the Hub shows, newest first: `repo`, `number`, `url`, `title`, `labels`, `created_at`, the repository's `language`, and `needs` |
| `cache.json` | The ETag of each answer and what was kept from it, for the next run |
| `HEALTH.md` | The health report |

Which projects show is decided by the health checks below.

**No personal data** (AC-HUB-5). Nothing about who opened, commented on or was assigned an issue is kept: no usernames, avatars or assignees, and no issue text but the title and its *You'll need* line (`needs`). That line is read from an issue that says, for example, `You'll need: Python, pytest`, or from an issue form field called *You'll need*; an aside that names someone is taken out, and a line that still names someone is left out. Commits give only their date.

**Rate limits** (AC-HUB-4). A run makes about 4 requests per project (the repository, its last commit and one page of issues per label), so about 100 for 25 projects, far below the workflow token's hourly limit (GitHub reported 5,000 on the first run). Every request carries the ETag of the last answer; when nothing changed GitHub answers *304 Not Modified*, which doesn't count against the limit. Before it starts, the sync checks the quota left covers a whole run, and otherwise stops without writing anything. It logs the requests made, how many were unchanged, and the quota left:

```
Hub: 25 projects (23 healthy, 1 flagged, 1 hidden), 131 open issues. GitHub API: 102 requests, 87 unchanged (304, free); 4,912 of 5,000 left, resets at 13:04 UTC.
```

Without `GITHUB_TOKEN`, GitHub allows 60 requests an hour, which covers about a dozen projects.

### Where the snapshot lives

The snapshot isn't committed to `main`. The `Hub sync` workflow (`.github/workflows/hub.yml`) runs every 6 hours:

1. `.github/scripts/hub-snapshot.sh` puts the last snapshot in `data/derived/hub/`, so its ETags are reused.
2. `python -m hub sync` refreshes it, and `python site/build.py` checks the site builds with it.
3. `.github/scripts/hub-publish.sh` saves it as a commit on the **`hub-data`** branch, which holds only the snapshot, then runs CI on `main`, which deploys.

Every CI build runs `hub-snapshot.sh` first, so a deploy from `main` always carries the latest snapshot. If the branch can't be reached the build fails, and the live site keeps its Hub. Before the first sync, and in forks, there is no branch: the site builds with an empty Hub.

To see the Hub locally, get the snapshot (or run `python3 -m hub sync` with a token):

```sh
.github/scripts/hub-snapshot.sh
```

## Contributor metrics

`python -m hub metrics` counts, for the projects the Hub shows (PRD HUB-10, ticket #41), from their pull requests and issues on GitHub (`metrics.py`, GraphQL API):

| Count, per quarter from 2026 Q1 | What it is |
|---|---|
| `new_contributors` | People whose first merged pull request to any of these repositories was merged that quarter |
| `opened` | Issues and pull requests opened that quarter by newcomers: anyone but bots and the repositories' maintainers |
| `answered`, `waiting` | Of those, how many a maintainer has responded to (a comment, a review, or merging the pull request), and how many not yet |
| `within_pledge` | Answered within 7 days, the time every listed project pledges |
| `median_hours` | The median time to that first response, among those answered |

Maintainers are the people GitHub marks `OWNER`, `MEMBER` or `COLLABORATOR` on the repository; bots and deleted accounts don't count as anyone. It writes `metrics.json` next to the snapshot, and the Hub page shows it as a table, newest quarter first.

**Counts only.** Usernames are read in memory, to tell people apart and to see who answered, and are never written, logged or published. A run starts from GitHub each time, so no list of people is kept between runs either. PRD §12 asks for a review with counsel before this runs on real data, so the Hub sync runs it only when the repository variable `HUB_METRICS` is `true`, at most once a day (`--daily`), and a failure there doesn't stop the sync ([docs/deploy.md](../docs/deploy.md#hub-sync)). The About page's privacy section mentions the counts once there are any.

**Cost.** GraphQL queries cost about one point per page of 50 to 100 items: a few points per project a day, against the workflow token's 1,000 points an hour. A run stops without writing anything if fewer than 100 points are left.

The counts follow the projects the Hub shows on the day: when a project joins or leaves, past quarters change with it.

## Health checks

Every sync, so four times a day, checks each listed project with what it has just fetched, at no extra cost (`health.py`; PRD HUB-06):

| Flag | When | Hidden |
|---|---|---|
| `inactive` | No commit on the default branch in the last 90 days | After 14 days flagged |
| `no_issues` | No open issues labelled `good first issue` or `help wanted` | After 14 days flagged |
| `topic` | The repository no longer carries the `djazairdev` topic | At once (AC-HUB-3): only maintainers set topics, so removing it withdraws consent |
| `archived` | The repository is archived | At once |
| `missing` | The repository is gone or private | At once |

A project shows again as soon as the problem is fixed. `projects.json` gives each project its `flags` (reason, the date it was first flagged, what was found), `status` (`healthy`, `flagged` or `hidden`), `hide_on` and `shown`; the next sync reads the dates from it, so a flag keeps its first date. The Hub only shows projects with `shown`, and the feed only their issues.

The health report, [`HEALTH.md` on the `hub-data` branch](https://github.com/djazairdev/djazair.dev/blob/hub-data/HEALTH.md), lists every flagged and hidden project with the reason, what was found, the date it was flagged and the date it is or was hidden. A project stays in `projects.yml` while it is hidden; remove its entry by pull request if it won't come back.
