# Launch

djazair.dev launches by **30 November 2026**, with a scope checkpoint on 15 November (ticket [#35](https://github.com/djazairdev/djazair.dev/issues/35), PRD §14). This page covers:

- what has to be true before launch;
- the launch-day steps, in order;
- the first weeks after launch.

Ticket status lives in GitHub.

## Ready when

| What | Ticket or guide |
| --- | --- |
| Every MVP page is built, in English and Arabic | [implementation plan](implementation-plan.md) |
| The latest Innovation Graph release is live: Q2 2026 if GitHub has released it, otherwise Q1 2026 | the `Data` workflow ([deploy.md](deploy.md#data-updates)) |
| Someone other than the founder has checked the published numbers | [below](#checking-the-numbers) |
| A fluent reviewer has signed off the Arabic | [#33](https://github.com/djazairdev/djazair.dev/issues/33), [arabic-review.md](arabic-review.md) |
| Report #1 is ready to publish | [#34](https://github.com/djazairdev/djazair.dev/issues/34), [reports.md](reports.md#publishing) |
| At least 15 projects are listed in the Hub | [#28](https://github.com/djazairdev/djazair.dev/issues/28) |
| The corrections log is live on the Data page | `/en/data/#corrections` |
| The Pages project, API token, secrets and `main` ruleset exist | [deploy.md](deploy.md#one-time-setup-founder) |
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
| Report #1 | Every figure in the text, the tables and the charts | the same files; `tests/test_reports.py` also checks every claim the words make |

Then check a few numbers against GitHub's own files. For example, take Algeria's account count in `data/raw/<release>/developers.csv` (economy `DZ`, the latest quarter). Then recompute one ratio from the Methodology page's formulas: its worked example shows how.

Note who checked and when in a comment on #35.

## Launch day

1. **Freeze `main`.** Merge only the launch changes until the domain has moved.
2. **Check the Pages project's own address.** CI has deployed `main` there. Run:

   ```bash
   python3 site/tools/smoke.py https://<project>.pages.dev
   ```

   It reads the sitemap and checks:
   - every page and every link to the site itself;
   - the share images and the zip files;
   - robots.txt and the 404 page;
   - the headers from `_headers`.

   It should end with *All good.* A note that the address is hidden from search engines is normal there: Cloudflare does that for its own addresses.
3. **Date the launch** in one pull request:
   - set the date of the *Index v1* entry in [content/changelog.json](../content/changelog.json);
   - publish report #1 (see [reports.md](reports.md#publishing)): `status`, `published`, and the Hub numbers from that day.

   Merging it deploys.
4. **Move the domain.** In Cloudflare, go to *Workers & Pages*:
   1. Open the holding-page project's *Custom domains* tab and remove `djazair.dev`.
   2. In the site project, choose *Custom domains → Set up a custom domain → djazair.dev*. Cloudflare creates the DNS record. Today djazair.dev has none, only its name servers and mail records ([#50](https://github.com/djazairdev/djazair.dev/issues/50)).
   3. In *SSL/TLS → Edge Certificates*, turn on *Always Use HTTPS*.

   Keep the holding-page project for a week, in case you need to move back.
5. **Check the real address:**

   ```bash
   python3 site/tools/smoke.py
   ```

   Then open https://djazair.dev/ on a phone, in both languages.
6. **Turn on monitoring.**
   1. Set the repository variable `UPTIME_URLS` to `https://djazair.dev/ https://djazair.dev/en/ https://djazair.dev/ar/`.
   2. Run the *Uptime* workflow by hand. Issue #50 closes when it passes.
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

Use the numbers from the published report: the drafts below take its title and standfirst, which the reviewer has already checked in both languages. Don't post Arabic that a fluent reader hasn't checked (D13).

### For the Innovation Graph team

> **Title:** Algeria Developer Index: a quarterly index built on the Innovation Graph
>
> Hello Innovation Graph team,
>
> We have launched [djazair.dev](https://djazair.dev/en/), an open-source site that follows Algeria's developer accounts every quarter with your data. It compares Algeria with the medians of North African and African peer groups. Every figure names its source quarter, and every table we derive is published as CSV and JSON under CC0.
>
> - Methodology (sources, formulas, peer groups, known limitations): https://djazair.dev/en/methodology/
> - Our first quarterly report: https://djazair.dev/en/reports/&lt;quarter&gt;/
> - Code and data: https://github.com/djazairdev/djazair.dev
>
> We describe the counts as developer accounts placed in an economy by network address, not as people. We also note that pushes are rising across GitHub. If we describe anything wrongly, or there is a better way to use the data, we would be glad to know: corrections go in our public log within 7 days.
>
> Thank you for publishing the data under CC0.

### Announcements

**LinkedIn, English:**

> *[the report's standfirst]*
>
> Today we are launching djazair.dev:
> - a quarterly Algeria Developer Index built on GitHub's Innovation Graph, compared with the North African and African medians, with every table free to reuse;
> - a Hub of open-source projects with issues for first-time contributors.
>
> Report: https://djazair.dev/en/reports/&lt;quarter&gt;/ · Index: https://djazair.dev/en/index/ · Hub: https://djazair.dev/en/hub/

**LinkedIn, Arabic:**

> *[ملخّص التقرير]*
>
> نطلق اليوم djazair.dev:
> - مؤشرًا ربعيًا لحسابات المطوّرين في الجزائر، مبنيًا على بيانات GitHub Innovation Graph، يقارن الجزائر بوسيطَي شمال أفريقيا وأفريقيا، وكل جداوله متاحة لإعادة الاستخدام بحرّية؛
> - مركزًا للمشاريع مفتوحة المصدر ومهامها المناسبة للمبتدئين.
>
> التقرير: https://djazair.dev/ar/reports/&lt;quarter&gt;/ · المؤشر: https://djazair.dev/ar/index/ · المركز: https://djazair.dev/ar/hub/

**X:** the report's title and link, plus one chart from the press kit. Use the Arabic chart for the Arabic post.

**Meetups:** a ten-minute talk.
1. What the Index measures: accounts, not people.
2. Three numbers from the report, including the bad news.
3. Algeria against the medians.
4. The languages.
5. How to help: list a project in the Hub, pick an issue, review the Arabic, or check the numbers.

The press kit's charts work as slides.
