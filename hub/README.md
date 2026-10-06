# hub

The Project Hub (PRD §8). Python 3.12+, standard library only.

```sh
python3 -m hub check-registry                    # validate projects.yml against hub/projects.schema.json
python3 -m hub check-project owner/name --pledge # run the inclusion checks on one repository
python3 -m hub check-submission --proposed FILE  # check the entries a new projects.yml adds or changes
python3 -m hub check-issue --body-file FILE      # check a request made with the issue form
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
| `checks.py` | The seven checks; each failure says what was found and how to fix it. The daily health checks (#26) reuse them |
| `submission.py` | Finds the entries a pull request adds or changes, reads the issue form, and writes the comment |

Still to come: the issues feed refreshed every 6 hours (#25) and the daily health checks (#26).
