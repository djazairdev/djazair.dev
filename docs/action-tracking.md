# Landing action counts

The landing page’s campaign measurements use a first-party `/api/events` endpoint on the existing Cloudflare Worker. No package or external tracking script is added. The production CI build enables counts with `--actions`, and the Worker configuration sets `ACTION_ANALYTICS_ENABLED` to `"true"`. The standalone build still defaults to counts off unless `--actions` is supplied. Counts start after the enabled version is deployed; previous visits cannot be recovered.

## Local review

```bash
python3 site/build.py --all-languages --actions
python3 site/tools/preview_actions.py --port 4322
```

Open `/en/?utm_source=facebook&utm_medium=paid&utm_campaign=week1`. Follow a beginner-task link or use Share. `http://127.0.0.1:4322/_review/events` displays aggregate counts held in memory. Restarting clears them. The preview binds to loopback, logs no requests and sends nothing to Cloudflare. `--all-languages` is only for translation review; Arabic remains unpublished.

## What the numbers mean

| Event | What it measures | What it cannot establish |
| --- | --- | --- |
| `landing_view`, `hub_view`, `meetups_view` | A page load where the script runs | Unique people or ad reach; refreshes count again |
| `task_browse` | A link to the Hub was clicked | That a suitable task was chosen |
| `task_open` | A GitHub issue link was clicked | That work began or a contribution was accepted |
| `meetup_find`, `meetup_host` | A discovery or hosting link was clicked | Registration, attendance or a completed meetup |
| `share_open` | Native sharing was requested | That the user finished sharing |
| `share_complete` | The native share promise resolved | That another person received or read the link |
| `share_copy` | A share link was successfully copied | That it was sent to someone |

Never add these as if they were unique participants. Never use a low click cost as evidence of community health. People can forge or repeat client events; these are directional counts, not authoritative outcomes. Local test events are separate from production.

## Attribution and privacy

Only `utm_source`, `utm_medium`, `utm_campaign` codes consisting of 1–64 lowercase letters, digits, underscores or hyphens are accepted. Use campaign labels such as `week1-developers`; never put a person’s name, email, phone or ad click ID in a code. Missing attribution uses direct, broad referrer categories, or none. No raw referrer is sent.

These codes are preserved through internal page links and the Algeria discovery/hosting links on founders.coffee. GitHub issue links remain plain. Sharing produces a fresh `community / share / city-builders` link, so recipients are not attributed to the sender’s paid ad. Local anchors, filter parameters and fragments remain intact. Parameters reaching founders.coffee do not by themselves establish completed meetup attribution; its own outcome measurement must be joined separately.

The stored dimensions are event, page category, language, section category, source, medium and campaign. There are no visitor IDs, cookies, persistent attribution storage, issue titles, user-generated text, IP addresses or full URLs in the event dataset. The browser and endpoint respect Do Not Track and Global Privacy Control. The About page discloses enabled counts. Cloudflare still receives ordinary HTTP requests as the hosting provider.

The endpoint requires same-origin POST JSON, validates an allowlist, limits bodies to 1 KB and sends no data when disabled. It sets no cookies, has no public read endpoint and uses no personal identifiers for deduplication. The browser caps counts at 50 events per page and suppresses rapid duplicate link clicks. This limits accidental repeats, not forged traffic. Check anomalous campaigns before spending more.

## Production configuration and report access

1. Review the event names, privacy text and campaign convention.
2. Build the production artifact with `python3 site/build.py --actions` (without `--all-languages`). The production CI build includes this flag.
3. Set `vars.ACTION_ANALYTICS_ENABLED` to `"true"` in `wrangler.jsonc`; keep the `EVENTS` Analytics Engine binding and selective `/api/events` routing.
4. Deploy through the existing workflow, verify actual campaign events, and keep the default static asset routes and security headers. A missing binding or disabled endpoint returns 503 and leaves navigation working.
5. Export weekly aggregates with an Account Analytics Read token; keep it in the environment, never the repository:

```bash
python3 site/tools/action_report.py --days 7 --out /private/report-directory/week.csv
```

Analytics Engine creates its dataset on the first write, uses sampling at scale and retains raw data for three months. The report sums sample weights rather than raw row counts. Export weekly to preserve the full 90-day record. Check current [Cloudflare setup](https://developers.cloudflare.com/analytics/analytics-engine/get-started/), [retention limits](https://developers.cloudflare.com/analytics/analytics-engine/limits/) and [pricing](https://developers.cloudflare.com/analytics/analytics-engine/pricing/) before activation. Pages stay static through [selective Worker routing](https://developers.cloudflare.com/workers/static-assets/routing/worker-script/).

## Weekly decisions for the 90-day validation

Record spend and qualified engagement by campaign alongside these counts. Compare task opens and meetup clicks per landing-page load within the same source/campaign; call these **actions per view**, since neither side counts unique people. Review shared-link arrivals and share actions together; copied links and cancelled share dialogs are weak signals alone. Native social-platform shares are a separate metric and are not observed by this website.

Verify actual accepted contributions from GitHub, and completed meetups, repeat hosts and returning attendees from the meetup records. Keep outcome evidence separate from this anonymous dataset. HEART measures meaningful activity and returning participation; the North Star remains completed, recurring community activity, not views or clicks. Continue the approved small ad pilot from day one, but only expand spending after qualified engagement, sharing and verified participation improve. This change does not start ads.

## Rollback and verification

To stop collection, set `vars.ACTION_ANALYTICS_ENABLED` to `"false"` and remove `--actions` from the CI build, then deploy. The endpoint returns 503 while disabled, and the untracked build removes the action-count disclosure. Navigation continues to work.

For activation verification, use a clearly labeled campaign such as `activation-check-20261011`, with `utm_source=review` and `utm_medium=test`. Confirm page and click requests receive 204, then verify the corresponding event rows in `djazair_landing_events` using Cloudflare account access. A 204 response alone is not proof the data is queryable. Exclude the test campaign from growth and paid-pilot results. Do not disable visitors’ privacy settings to obtain a count. Weekly report-token setup is separate from enabling collection.
