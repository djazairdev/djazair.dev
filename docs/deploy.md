# Deploying djazair.dev

The `CI` workflow (`.github/workflows/ci.yml`) runs on every pull request and every push to `main`:

1. **Test**: a syntax check and the unit tests, on Python 3.12 and 3.13.
2. **Build**: `python site/build.py`, uploaded as the `site` artifact.
3. **Measure load times**: `python site/tools/perf.py` loads the built pages in Chrome on a throttled phone profile and fails if a page is over its budget ([performance.md](performance.md)). It runs beside the deploy and doesn't hold it up.
4. **Deploy** to Cloudflare Pages, only after the tests and the build pass, so a failing change never replaces the live site:
   - a push to `main` deploys to the project's production branch (`main`);
   - a pull request from this repository deploys a preview at `pr-<number>.<project>.pages.dev`, linked from the pull request. Pull requests from forks never deploy, because they can't see the secrets.

Until the settings below exist, the deploy step is skipped with a notice and everything else still runs.

## One-time setup (founder)

These need account access, so they aren't automated.

1. **Create the Pages project.** In Cloudflare, go to *Workers & Pages → Create → Pages → Upload assets* and create a project for the full site (for example `djazair-dev-site`), with `main` as the production branch. Keep the project that serves the holding page as it is: djazair.dev stays on the holding page until launch.
2. **Create an API token.** *My Profile → API Tokens → Create Token → Custom token*, with the single permission *Account → Cloudflare Pages → Edit* for the djazair.dev account. Give it an expiry date and note it in your password manager.
3. **Add them to GitHub.** In the repository, *Settings → Secrets and variables → Actions*:
   - secret `CLOUDFLARE_API_TOKEN`: the token;
   - secret `CLOUDFLARE_ACCOUNT_ID`: the account ID (shown in the Cloudflare dashboard sidebar);
   - variable `CLOUDFLARE_PAGES_PROJECT`: the project name from step 1.
4. **Protect `main`.** *Settings → Rules → Rulesets → New branch ruleset* targeting `main`: require a pull request before merging; require the status checks `Test (Python 3.12)`, `Test (Python 3.13)` and `Build the site` (add `Measure load times` once it has run reliably for a few weeks); block force pushes; restrict deletions.
5. **Add the second admin** (PRD R2) to the GitHub organisation and the Cloudflare account, with two-factor authentication.

Secrets are only read by the deploy step, are passed to Wrangler through its inputs and are never printed. The built site contains no secrets.

## Scheduled jobs

Scheduled workflows (the Innovation Graph check, the Hub sync, the uptime check and the weekly link check) only run when the repository variable `SCHEDULES_ENABLED` is `true`, so nothing runs on a timer until you turn it on. Each can also be started by hand from the *Actions* tab. When one fails, it opens an issue ([Alerts](#alerts)).

### Hub sync

The `Hub sync` workflow (`.github/workflows/hub.yml`) runs every 6 hours, at 00:41, 06:41, 12:41 and 18:41 UTC. It fetches the listed projects and their beginner issues with `python -m hub sync`, runs the health checks (a project without the `djazairdev` topic leaves the Hub at once; one flagged for 14 days is hidden), checks the site builds with them, saves the snapshot on the `hub-data` branch, and runs CI on `main`, which deploys (details in [hub/README.md](../hub/README.md#sync-issues-feed)). `main` never changes, so it needs no pull request.

**Setup (founder):** nothing beyond `SCHEDULES_ENABLED`. Keep the `hub-data` branch out of the `main` ruleset: the workflow pushes to it. Don't delete it either: it holds the snapshot every build uses. If it is deleted, the next sync starts it again.

### Link check

The `Link check` workflow (`.github/workflows/links.yml`) runs every Monday at 06:23 UTC. It opens every link the site curates, the translation teams on the Hub's localisation page (`content/localisation.json`), with `python site/tools/links.py`. A link is broken when it doesn't answer 200 at the same address with a page that names the team's language: a team that moved, closed or became a sign-in page. A site that turns robots away (401, 403, 429, 5xx) or doesn't answer is listed in the log as not checked, without failing the run.

### Data updates

The `Data` workflow (`.github/workflows/data.yml`) runs every day at 06:23 UTC:

1. `python -m pipeline fetch` archives the latest GitHub Innovation Graph release. If it isn't new, the run stops here.
2. `python -m pipeline publish` validates it and writes `data/derived/`; `python -m pipeline revisions` compares it with the release before it.
3. The tests and the site build run with the new data.
4. `.github/scripts/data-pr.sh` commits `data/` to a `data/<quarter>-<commit>` branch, opens a pull request, runs CI on it, merges it when CI passes, and then runs CI on `main`, which deploys. Pull requests and merges made with the workflow's token start no workflow by themselves, so the script starts CI by hand and waits for it.
5. If the release revises past values, the pull request stays open for editorial review instead of merging; merging it by hand deploys as usual.

If any step fails, `.github/scripts/data-failed.sh` opens a *Data update failed* issue with the validation report (or comments on the one already open); the next run that works closes it. The live site only changes when CI passes on `main`, so a failed run leaves it as it was.

*Run workflow* on the *Actions* tab starts it by hand; tick *force* to publish the latest release again even if it is already archived (with unchanged data, nothing is committed).

**Setup (founder):**

- *Settings → Actions → General → Workflow permissions*: tick **Allow GitHub Actions to create and approve pull requests**. Without it the run stops at the pull request, and the issue it opens links to the branch so you can open the pull request yourself.
- Set the repository variable `SCHEDULES_ENABLED` to `true` to run it daily.
- Auto-merge isn't needed: the workflow merges after CI passes. With the ruleset from step 4 above it can still merge, because the checks it starts run on the pull request's commit. Don't require approving reviews in that ruleset, or data pull requests will wait for one.

## Alerts

Each scheduled workflow opens a GitHub issue when it fails, or comments on the one already open, so a problem is never silent and never repeats as a new issue. The next run that works closes it.

| Issue | Opened by | When |
| --- | --- | --- |
| *Data update failed* | `Data` | The Innovation Graph update fails: fetching, validating, testing, building or merging. |
| *Hub sync failed* | `Hub sync` | The Hub sync fails, health checks included. The site keeps the last snapshot. |
| *Broken links* | `Link check` | A translation team's link on the localisation page is broken. Fix or remove it in `content/localisation.json`. |
| *Site down* | `Uptime` | `https://djazair.dev/` doesn't answer 200 with the site in it, three tries 30 seconds apart. The check runs from GitHub Actions every 30 minutes. |

**Who gets them:** the founder and the second admin. Set the repository variable `ALERT_ASSIGNEES` to their GitHub usernames, comma-separated (for example `founder,second-admin`). New alert issues are assigned to them, so GitHub notifies them by email and in the app, depending on their notification settings. Both should also *Watch* the repository for issues as a backstop.

**Testing an alert:** on the *Actions* tab, run the workflow by hand with **Fail on purpose** ticked. It stops at its first step and opens (or comments on) its issue. Running it again without the box closes the issue. For `Data`, only do that when no new Innovation Graph release is waiting, or the run publishes it.

**Uptime addresses:** the variable `UPTIME_URLS` (space-separated) replaces the default `https://djazair.dev/`. At launch, add `https://djazair.dev/en/` and `https://djazair.dev/ar/`. Like the other schedules, uptime checks run only when `SCHEDULES_ENABLED` is `true`.

## Analytics

The site can count visits with [Cloudflare Web Analytics](https://www.cloudflare.com/web-analytics/), which sets no cookies and keeps totals only (pages, referrers, countries, browsers), so no consent banner is needed.

**Setup (founder):** in Cloudflare, *Analytics & Logs → Web Analytics → Add a site*, enter `djazair.dev` and copy the token from the snippet it shows (32 characters). Save it as the repository variable `CLOUDFLARE_WEB_ANALYTICS_TOKEN` (a variable, not a secret: it is public in every page). The next deploy adds the beacon to every page, and the Privacy section of the About page then says that visits are counted. Don't also turn on the automatic setup in the Pages project, or visits count twice.

## Launch

At launch, move the `djazair.dev` custom domain from the holding-page project to the site project (*Custom domains* tab). Before and after the move, `python3 site/tools/smoke.py <address>` checks the deployed site from the outside: every page in the sitemap, every link to the site, the downloads, the 404 page and the response headers. [launch.md](launch.md) has the full launch-day list.
