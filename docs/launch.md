# Launch

djazair.dev launches on **12 October 2026** (decision D30, ticket [#35](https://github.com/djazairdev/djazair.dev/issues/35), PRD §14), in English: every Arabic page invites people to help translate the site until fluent contributors have translated and reviewed it (D28). This page covers:

- what has to be true before launch;
- the launch-day steps, in order;
- the first weeks after launch.

Ticket status lives in GitHub.

## Ready when

| What | Ticket or guide |
| --- | --- |
| Every MVP page is built in English, and every `/ar/` address shows the invitation to translate | [implementation plan](implementation-plan.md), [#61](https://github.com/djazairdev/djazair.dev/issues/61) |
| The latest Innovation Graph release is live: Q1 2026 at launch, and Q2 2026 within a day of GitHub releasing it | the `Data` workflow ([deploy.md](deploy.md#data-updates)) |
| Someone other than the founder has checked the published numbers | [below](#checking-the-numbers) |
| The seed projects that pass every check are listed in the Hub: five of six at launch, and ksarjs once it passes (D25, D30) | [#28](https://github.com/djazairdev/djazair.dev/issues/28), the [health report](https://github.com/djazairdev/djazair.dev/blob/hub-data/HEALTH.md) |
| The corrections log is live on the Data page | `/en/data/#corrections` |
| The Cloudflare API token, its two secrets and the `main` ruleset exist, and CI has deployed `main` | [deploy.md](deploy.md#one-time-setup-founder) |
| A second admin is on the registrar, Cloudflare and the GitHub organisation, with two-factor authentication; djazair.dev and founders.coffee have auto-renewal and the registrar lock | PRD §11, R2 |
| Schedules and alerts are on: `SCHEDULES_ENABLED`, `ALERT_ASSIGNEES`, and Actions may create pull requests | [deploy.md](deploy.md#scheduled-jobs) |

## Checking the numbers

Before launch, someone other than the founder checks every number on the site against the published data (PRD §13). Every table is in `data/derived/<quarter>/` as CSV, which opens in any spreadsheet. Each page names the file behind it, and its *Data* links download the same tables.

| Page | Numbers | File |
| --- | --- | --- |
| Home | The account count, the three stats, the scorecard | `overview.csv` |
| Overview | Each indicator: this quarter, a year earlier, the change, the medians and Algeria's ranks | `overview.csv`, `ranks.csv` |
| Peers | North Africa and the core peers; the rank tables | `peers.csv`, `ranks.csv`, `groups.csv` |
| Trends | Every quarter since 2020, for Algeria and the medians | `trends.csv` |
| Languages | The top ten, a year earlier and the change | `languages_algeria.csv` |

Then check a few numbers against GitHub's own files. For example, take Algeria's account count in `data/raw/<release>/developers.csv` (economy `DZ`, the latest quarter). Then recompute one ratio from the Methodology page's formulas: its worked example shows how.

Note who checked and when in a comment on #35.

## Launch day

1. **Freeze `main`.** Merge only the launch changes until the domain has moved.
2. **Check the site's own address.** CI has deployed `main` there. Run:

   ```bash
   python3 site/tools/smoke.py https://djazair-dev-site.<subdomain>.workers.dev
   ```

   It reads the sitemap and checks:
   - every page and every link to the site itself, and the chart embeds, dark and light;
   - the share images and the zip files;
   - robots.txt and the 404 page;
   - the headers from `_headers`, including that only the chart embeds can be framed by other sites.

   It should end with *All good.*
3. **Date the launch:** set the date of the *Index v1* entry in [content/changelog.json](../content/changelog.json). Merging it deploys. The public Reports and Methodology pages were removed on 9 October; sources and formulas are on the Data page, and report #1 stays a draft in `content/reports/`.
4. **Move the domain** from the holding page to the site:
   1. In Cloudflare, open *Workers & Pages → djazair-dev-holding → Settings → Domains & Routes* and remove `djazair.dev`. The address stops answering until the next step has deployed.
   2. Merge a pull request that changes [`wrangler.jsonc`](../wrangler.jsonc): add the `routes` line from the comment at its end, and set `"workers_dev": false`, so the site has one address. Keep `"preview_urls": true`: pull-request previews still work. CI deploys it, and Cloudflare attaches djazair.dev with its DNS record and certificate within minutes.
   3. In *SSL/TLS → Edge Certificates*, turn on *Always Use HTTPS*.

   Keep the holding page's Worker and `wrangler.holding.jsonc` for a week, in case you need to move back: remove `djazair.dev` from the site's Worker the same way, take the route out of `wrangler.jsonc`, and run `npx wrangler deploy --config wrangler.holding.jsonc`. After that week, delete both (`npx wrangler delete --name djazair-dev-holding`).
5. **Check the real address:**

   ```bash
   python3 site/tools/smoke.py
   ```

   Then open https://djazair.dev/ on a phone: it should go to the English site. Check that https://djazair.dev/ar/ shows the invitation to translate.
6. **Turn on monitoring.**
   1. Set the repository variable `UPTIME_URLS` to `https://djazair.dev/ https://djazair.dev/en/ https://djazair.dev/ar/`.
   2. Run the *Uptime* workflow by hand: it should pass for all three addresses.
   3. Optionally, add `CLOUDFLARE_WEB_ANALYTICS_TOKEN` ([deploy.md](deploy.md#analytics)).
7. **Tell search engines.** Add djazair.dev to Google Search Console and Bing Webmaster Tools (a DNS TXT record proves you own it), then submit `https://djazair.dev/sitemap.xml`.
8. **Share the methodology with GitHub (D17).** Post the [note below](#for-the-innovation-graph-team) in the [Innovation Graph discussions](https://github.com/github/innovationgraph/discussions), which its README invites.
9. **Announce it** ([drafts below](#announcements)):
   - the founders.coffee meetups in Algiers and Oran;
   - Google developer groups and university clubs;
   - LinkedIn and X.
10. **Close #35.**

## The first weeks

- **Alerts** arrive as issues assigned to `ALERT_ASSIGNEES` ([deploy.md](deploy.md#alerts)). Act on *Site down* at once.
- **Corrections** come in through the *Correction* issue form. Fix the number and log it in [content/corrections.json](../content/corrections.json) within 7 days.
- **The next quarter.** The `Data` workflow publishes each new Innovation Graph release within a day. A report is due within 14 days of the release ([reports.md](reports.md#writing-the-next-report)).
- **Load times.** After a few weeks of reliable runs, add *Measure load times* to the checks the `main` ruleset requires ([deploy.md](deploy.md#one-time-setup-founder)).

## Drafts

The drafts use this summary of the Q1 2026 data, from `data/derived/2026-q1/overview.csv` and `trends.csv`; update it when a new quarter is published:

> Algeria had 586,990 developer accounts on GitHub at the end of March 2026, 49% more than a year earlier. Growth has sped up four quarters in a row and kept pace with North Africa (median 44%). Pushes per account more than doubled, from 0.51 to 1.06, but still trail the North African median of 1.34.

At launch the site is in English (D28), so post the English drafts, and ask Arabic speakers to help translate it ([#62](https://github.com/djazairdev/djazair.dev/issues/62)). Keep the Arabic drafts for when the Arabic site is live, and don't post Arabic that a fluent reader hasn't checked (D13).

### For the Innovation Graph team

> **Title:** Algeria Developer Index: a quarterly index built on the Innovation Graph
>
> Hello Innovation Graph team,
>
> We have launched [djazair.dev](https://djazair.dev/en/), an open-source site that follows Algeria's developer accounts every quarter with your data. It compares Algeria with the medians of North African and African peer groups. Every figure names its source quarter, and every table we derive is published as CSV and JSON under CC0.
>
> - The Index: https://djazair.dev/en/index/
> - Sources, formulas, peer groups, known limitations and every table: https://djazair.dev/en/data/
> - Code and data: https://github.com/djazairdev/djazair.dev
>
> We describe the counts as developer accounts placed in an economy by network address, not as people. We also note that pushes are rising across GitHub. If we describe anything wrongly, or there is a better way to use the data, we would be glad to know: corrections go in our public log within 7 days.
>
> Thank you for publishing the data under CC0.

### Announcements

**LinkedIn, English:**

> Algeria had 586,990 developer accounts on GitHub at the end of March 2026, 49% more than a year earlier. Growth has sped up four quarters in a row and kept pace with North Africa (median 44%). Pushes per account more than doubled, from 0.51 to 1.06, but still trail the North African median of 1.34.
>
> Today we are launching djazair.dev:
> - a quarterly Algeria Developer Index built on GitHub's Innovation Graph, compared with the North African and African medians, with every table free to reuse;
> - a Hub of open-source projects with issues for first-time contributors.
>
> Index: https://djazair.dev/en/index/ · Data: https://djazair.dev/en/data/ · Hub: https://djazair.dev/en/hub/
>
> Read Arabic? Help us bring djazair.dev to Arabic: https://github.com/djazairdev/djazair.dev/issues/62

**LinkedIn, Arabic** (once the Arabic site is live, D28):

> *[ملخّص أرقام الربع]*
>
> نطلق اليوم djazair.dev:
> - مؤشرًا ربعيًا لحسابات المطوّرين في الجزائر، مبنيًا على بيانات GitHub Innovation Graph، يقارن الجزائر بوسيطَي شمال أفريقيا وأفريقيا، وكل جداوله متاحة لإعادة الاستخدام بحرّية؛
> - مركزًا للمشاريع مفتوحة المصدر ومهامها المناسبة للمبتدئين.
>
> المؤشر: https://djazair.dev/ar/index/ · البيانات: https://djazair.dev/ar/data/ · المركز: https://djazair.dev/ar/hub/

**X:** the summary's first sentence and https://djazair.dev/en/, plus one chart from the Index (each chart has an SVG download), and a line asking Arabic speakers to help translate the site.

**Meetups:** a ten-minute talk.
1. What the Index measures: accounts, not people.
2. Three numbers from the Q1 2026 data, including the bad news.
3. Algeria against the medians.
4. The languages.
5. How to help: translate the site into Arabic, list a project in the Hub, pick an issue, or check the numbers.

The Index's chart downloads (SVG) work as slides.
