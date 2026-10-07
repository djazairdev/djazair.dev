# site

The static website, in English and Arabic (right to left), built by a small Python builder that uses only the standard library (decision D21 in the PRD). Output is plain HTML, one stylesheet and a small script that only enhances: every page works without JavaScript. Hosted on Cloudflare Pages.

## Build and preview

Needs Python 3.12 or later, nothing else.

```sh
python3 site/build.py                                         # writes site/dist
python3 -m http.server 4322 --bind 127.0.0.1 --directory site/dist
```

Then open <http://localhost:4322/>. `python3 site/build.py --dev` also builds `/en/_dev/components/` and `/ar/_dev/components/`, which show every shared component and the chart kit on real data; they are never deployed.

## How it's organised

| Path | What it holds |
|---|---|
| `build.py` | Entry point |
| `djsite/routes.py` | Every page and its path under `/en/` and `/ar/` |
| `djsite/data.py` | The Index data: the quarter `data/derived/latest.json` names, each file checked against its `manifest.json`; and the Hub snapshot in `data/derived/hub/` (`Hub`), read once per build. The site reads no other data |
| `djsite/scorecard.py` | The six headline indicators as Home and the Index overview show them |
| `djsite/editorial.py` | Sentences tied to the data: computed facts (growth streaks) and the per-quarter headlines in `content/editorial/`, used only while their claims hold; `verify` checks the claims of headlines and reports |
| `djsite/reports.py` | The quarterly reports in `content/reports/`: one page each, read from the report's own data quarter ([docs/reports.md](../docs/reports.md)) |
| `djsite/layout.py` | The page shell: head, skip link, header, Index sub-nav, notices, footer |
| `djsite/components.py` | Shared components: buttons, chips, chart controls, tiles, figure frame, source line, tables, disclosure, Hub issue rows, check panel, code sample |
| `djsite/charts.py` | Build-time SVG charts: line, bar and unit map, sparklines, rank strips; their CSV, JSON and SVG downloads |
| `djsite/figures.py` | A chart on a page: numbered label, wide and phone drawings, key, source line, downloads, data table |
| `djsite/unitmap.py`, `geo/algeria.json` | The unit map's layout inside Algeria's outline |
| `djsite/fmt.py` | Number, quarter and date formats for `en` and `ar-DZ` |
| `djsite/pages/` | One renderer per page; `root.py` is the language chooser at `/` |
| `djsite/i18n.py`, `i18n/*.json` | Interface strings (see below) |
| `djsite/markup.py` | HTML escaping: everything that isn't our own markup goes through `esc()` |
| `static/css/` | Stylesheets, concatenated in file-name order and inlined in every page ([docs/performance.md](../docs/performance.md)) |
| `static/js/` | `site.js` (every page) and page-specific scripts (`trends.js`, `hub.js`) |
| `static/fonts/` | Self-hosted Tajawal and JetBrains Mono woff2 subsets, with their licences (SIL OFL 1.1) |
| `tools/fetch_fonts.py` | Re-downloads the fonts and writes `static/css/05-fonts.css`; only needed to update them |
| `tools/make_outline.py` | Rebuilds `geo/algeria.json` from Natural Earth (public domain); only needed to change the outline |
| `tools/share.py`, `static/share/` | Draws the share images (1200 × 630, one per language) in Chrome; only needed to change them |
| `tools/perf.py` | Measures load times in Chrome on a throttled phone profile ([docs/performance.md](../docs/performance.md)) |
| `tools/screens.py` | Takes pictures of the built pages for `docs/design/` (full page and first screen, desktop and phone) |
| `tools/smoke.py` | Checks a deployed copy of the site from the outside: every page in the sitemap and every link to the site answer, the downloads, the 404 page and Cloudflare's headers ([docs/launch.md](../docs/launch.md)) |
| `tools/links.py` | Opens every link the site curates (the translation teams in `content/localisation.json`) and reports the broken ones; the *Link check* workflow runs it every Monday ([docs/deploy.md](../docs/deploy.md#link-check)) |
| `tools/strings.py` | Exports every string to a spreadsheet for the Arabic review and imports the corrections ([docs/arabic-review.md](../docs/arabic-review.md)) |
| `djsite/palette.py` | Chart colours: dark (the page, equal to the tokens) and light, for downloads |
| `holding/` | The pre-launch page served at djazair.dev until launch |

## Search and sharing

Every page has its own title and description, a canonical link and `hreflang` links to both languages; Home's `x-default` is `/`, the language chooser. Shared links show an Open Graph and X card with the page's title and description and the share image in the page's language. The build writes `sitemap.xml`, with both languages of every page, and `robots.txt`, which points to it. A placeholder page (`pages/stub.py`), a report still in draft and the 404 page carry `noindex` and stay out of the sitemap. `tests/test_seo.py` checks all of it.

## Design tokens

`static/css/00-tokens.css` holds every colour, type size, spacing step, radius and easing from the Foundations board ([docs/design/system-foundations.png](../docs/design/system-foundations.png)). Other stylesheets use only these custom properties; `tests/test_design_tokens.py` fails on a raw colour anywhere else and checks that text colours meet WCAG AA on every surface. With `prefers-reduced-motion: reduce`, nothing animates.

## Routes and languages

Pages live at `/en/<path>` and `/ar/<path>` with matching `lang`, `dir`, `hreflang` and canonical links. The language switcher keeps the reader on the same page.

`/` picks a language with a small inline script: the language the reader last chose with the switcher (kept in `localStorage`), otherwise the first Arabic or English entry in the browser's preferred languages, otherwise English. Without JavaScript, `/` is a plain bilingual chooser. Each language also has its own `404.html`; Cloudflare Pages serves the nearest one.

## Strings

English (`i18n/en.json`) is the source: a key a page uses but `en.json` lacks fails the build. A key missing from `ar.json` falls back to English, marked `lang="en"`, and the page says that some text isn't translated yet. Arabic is AI-drafted, so until a fluent reviewer signs it off (`_meta.reviewed` in `ar.json`), Arabic pages say the text is a draft (PRD D13). [docs/arabic-review.md](../docs/arabic-review.md) explains the review.

## Numbers, quarters and dates

`djsite/fmt.py` formats numbers the way `Intl.NumberFormat` does for `en` (`586,990.5`) and `ar-DZ` (`586.990,5`, Western digits), with the typographic minus `−` for negative values. Quarters read "Q1 2026" or "الربع الأول 2026" in text and "2026 Q1" on axes and in tables; dates are Gregorian with Algerian month names in Arabic. Inside Arabic text, every figure goes through `num()`, which isolates it left to right so `+49,1%` keeps its sign on the left; `tests/test_i18n_format.py` checks every signed value on every Arabic page.

## Charts

Every chart is drawn at build time as SVG, so a page can be read without fetching data or running JavaScript. A chart is a language-neutral spec, `LineChart`, `BarChart`, `HBarChart` or `UnitMap` in `djsite/charts.py`: names and titles are `{'en': …, 'ar': …}` and formatters take `(value, lang)`. `figures.figure(ctx, chart, n, source=…)` puts it on a page with:

- a wide drawing and a phone drawing (they switch at 760 px), and a key on phones, where lines have no end labels;
- `role="img"` with a title and a description, and a data table with every value in a disclosure under the chart (AC-IDX-7);
- downloads (IDX-15): CSV and JSON (CC0, the same for both languages) at `/charts/<yyyy-qN>/<id>.csv` and `.json`, and SVG files in the dark and light palettes at `/charts/<yyyy-qN>/<lang>/<id>-dark.svg` and `-light.svg`, each with its title and credit line. PNG files are drawn from those SVG files in the browser, with the site's fonts embedded, so their menu items appear only with JavaScript.

Colours come from `djsite/palette.py`; on-page charts use the dark palette, which a test keeps equal to the CSS tokens. Time runs left to right in Arabic too; Arabic words are set right to left and figures left to right. End labels never overlap: labels that would collide form a group centred on their lines. The unit map fills Algeria's outline with one square per 1,000 accounts; the squares show quantity, never location, and the map is never mirrored. The same data always gives byte-identical files (`tests/test_charts.py`).

## Home

`djsite/pages/home.py` builds the hero (the account count, three stats, the unit map), the scorecard, the growth trend, the latest quarterly report, the Hub teaser and the open-by-default links, all from the derived data. The count ticks up from the year-earlier value with CSS counters and no JavaScript; its rules depend on the data, so the builder generates them and adds them to the stylesheet (`ticker_css`). Readers who prefer reduced motion, and browsers without registered custom properties, see the plain number. The trend headline comes from `content/editorial/<yyyy-qN>.json` when the file exists and every claim it lists still holds; otherwise the section uses computed text.

The build also publishes the derived data as it is in `data/derived/`: `/data/<yyyy-qN>/<table>.csv` and `.json`, with `manifest.json` and `README.md`, every CSV table in one zip (`djazair.dev-index-<yyyy-qN>-csv.zip`, byte-identical for the same data), and `/data/latest.json`.

## Index overview

`djsite/pages/overview.py` shows the six indicators as full cards (`components.indicator_card`, with `id="ind-<key>"` so Home's tiles link to them), each with its change, medians, ranks, what it measures and its source; Algeria and six peers in a sortable table whose group medians sit in the table footer, so sorting leaves them below; and four limits to read before quoting the numbers.

Motion: Algeria's line draws as the chart scrolls into view (scroll-driven animations where the browser has them; elsewhere `site.js` draws charts below the fold over one second when they arrive), then the end dot and notes pop in, and unit-map squares appear in bands from Algiers. With `prefers-reduced-motion: reduce`, nothing moves.

## Trends

`djsite/pages/trends.py` draws all eight views at build time (four indicators, actual or indexed to 2020 Q1 = 100), each as a wide and a phone drawing with its downloads and data table. The metric tabs, the scale switch and the "Compare with" chips are radio buttons; CSS (`:has()`, in `static/css/51-index.css`) shows the chosen view and brings the chosen peer forward in amber, so all of it works without JavaScript. `static/js/trends.js` adds the crosshair readout: pointer and drag, ←/→ and Home/End on the focused chart, announced through a live region. It reads its positions and figures from a JSON block on the page (`#trends-data`), written by the builder from the same layout as the drawings, and lets a pressed peer chip clear when pressed again.

## Peers

`djsite/pages/peers.py` reuses the Overview's peers table (without its link to this page), then gives a rank table for North Africa and one for Africa (every economy with at least 20,000 accounts a year earlier, `scorecard.AFRICA_MIN_ACCOUNTS`, which a test keeps equal to the pipeline's). Rows come from the derived `ranks` table in order of accounts; each figure carries its rank in the group, read out as "rank 3 of 7", and the group median sits in the footer. The "How peers are chosen" button links to `methodology#peer-groups`.

Every sortable table (`components.data_table(..., sortable=True, announce=components.sort_text(ctx))`) sorts by its header buttons, with a mouse or the keyboard, and `site.js` writes the new order ("Sorted by Growth, highest first") into the table's live region. A sort value of `''` marks a missing figure, which stays last whichever way the column runs.

## Languages

`djsite/pages/languages.py` draws Algeria's top ten languages as an `HBarChart`: each bar is the developers a year earlier plus those added since, in the unit map's two greens (a loss would show as a dashed outline). The bars are categories, not time, so the Arabic drawing is mirrored, with names on the right. The figure's lede is computed: which language leads (and whether it has every quarter since 2020), what entered and left the top ten, and what grew fastest. Language names in Arabic text are wrapped in `<bdi>`, so `C++` keeps its signs. The page then gives the first three languages in each core peer, with how many languages pass GitHub's 100-developer threshold, and three notes, the first being that the counts can't be added up. "Methodology" links to `methodology#languages`.

## Topics

`djsite/pages/topics.py` (Phase 1.1, ticket #36) counts the repository topics GitHub publishes for each economy, those with 100 or more developers pushing. The first figure is an `HBarChart` of Algeria and the six core peers with `highlight='DZ'` and `change_kind='diff'`: only Algeria's bar is green, and the change is a count (+1), since a percentage of two topics would mislead. The second is the count every quarter since 2020 against the North African median and the peers. The ledes are computed: Algeria against the North African median, the three peers with the most topics, how long Algeria's count stayed the same, and which topics are new since a year earlier (the `topics` table carries the year-earlier figures). Topic names are monospace spans kept left to right, so `machine-learning` doesn't break in Arabic. Then the largest five topics in each peer, with the medians in the table footer, and four notes, the first being that topics count labels, not activity.

## Collaboration

`djsite/pages/collaboration.py` (Phase 1.1, ticket #37) reads GitHub's `economy_collaborators`: the git pushes sent and pull requests opened by developers in one economy to repositories owned in another. The `collaboration` table carries it both ways, `sent` (from developers in Algeria) and `received` (to repositories owned in Algeria). GitHub also lists the European Union as one economy, and its weight is always the sum of the members it lists (`tests/test_pipeline_publish.py` checks every quarter), so the table leaves its rank empty and the page leaves it out of bars and totals, with a note naming the members it sums. The two bar charts use `HBarChart(split=False)`: one green per bar, because a partner GitHub didn't list a year earlier was below its threshold, not at zero, so its change reads "new" instead of a gain drawn from zero. The third figure is the sum each way since 2020, and the table lists every economy both ways. Names of economies outside Africa are in the `world` strings, with `world_the` for the English names that take "the" in a sentence; a test checks every partner since 2020 has a name.

## Rankings

`djsite/pages/rankings.py` (Phase 1.1, ticket #38) shows GitHub's GDC26 ranking of African economies by pushes per 1,000 working-age people, a one-off GitHub dataset, from the `gdc26` table. Algeria isn't in it, so its bar is djazair.dev's estimate: `HBar(estimate=True)` draws an outline instead of a solid bar, the label says "estimate", and chart files that mix in an estimate get an `estimate` column. The page then shows the estimate step by step (four quarters of pushes, one of them repeating the latest while Q2 2026 isn't released, over the working-age population) and the same estimate for the ten economies GitHub lists, against GitHub's figures: it lands within 13% for nine of them, and far off for Eswatini, which the lede names. Every figure in a sentence is computed.

## Methodology and About

The words live in `content/methodology/<lang>.md` and `content/about/<lang>.md`, in a small Markdown subset that `djsite/markdown.py` renders with the standard library: `## Title {#id}` starts a numbered section (and an entry in the table of contents, sticky beside the text on wide screens and a disclosure on phones), `:::` blocks are drawn by `djsite/pages/methodology.py` with the page's components (callout, cards, the release timeline, formulas, the worked example, peer groups, limitations, update steps, logs, citation), and `{{name}}` values are computed from the derived data. Text is always escaped. `tests/test_methodology.py` checks that every formula matches `pipeline/indicators.py` and that the worked example, built from the counts in the published peers table, gives the published values.

`djsite/logs.py` builds the changelog (`content/changelog.json` plus one entry per published data quarter, from the manifests) and the corrections log (`content/corrections.json`); the Methodology page shows the latest entries and the Data page all of them. "Report an error" opens the `correction` issue form.

## Reports

`djsite/pages/report.py` draws each report in `content/reports/<yyyy-qN>/` like the Methodology page (numbered sections, table of contents) and gives its `:::` blocks their components: the headline figures, five charts from `figures.figure`, tables of the quarter against the previous one, the peer medians and the languages' ranks, the Hub numbers, the press kit and the citation. Its `{{name}}` figures are computed from the report's own quarter in `data/derived/`, so a report keeps its numbers when newer data arrives, and every claim its words make is listed in `report.json` and checked by `tests/test_reports.py`. The press kit is a zip of the five charts in both languages and themes, their CSV and JSON, the methodology summary and a README, with fixed names and timestamps so the same report gives the same file. A report whose `status` is `draft` says so at the top, carries `noindex` and stays out of the sitemap. The Reports page lists every report with its sections; Home shows the latest (`report.teaser`). [docs/reports.md](../docs/reports.md) explains how to write and publish one.

## Data and downloads

`djsite/pages/datapage.py` lists every derived table of the quarter with its CSV and JSON sizes (from the manifest), the data behind every chart, stable addresses for code (`/data/latest.json`, served with CORS), the full changelog and corrections log (`#changelog`, `#corrections`) and the licence and attribution. Charts are listed from `Site.charts`, which `figures.downloads` fills as pages register their files, so the route is marked `last=True` and the build renders it after every other page.

## Hub

`pages/hub.py` builds the Project Hub (ticket #27) from the snapshot the Hub sync writes (`data/derived/hub/`, see [hub/README.md](../hub/README.md#sync-issues-feed)): the projects whose health checks let them show, and their open `good first issue` and `help wanted` issues, newest first. Locally, `.github/scripts/hub-snapshot.sh` fetches the latest snapshot; without one the page shows its empty state. Cards show the title, labels (beginner labels first), the repository, its language, the *You'll need* line and the age at the last sync, and link to GitHub; nothing about who opened an issue is read (AC-HUB-5). Project ideas (ticket #39) live in GitHub Discussions; the Hub's Ideas section, with links to the category and its form, shows only when `config.HUB_IDEAS` is on, which waits for a maintainer to turn Discussions on ([docs/hub-ideas.md](../docs/hub-ideas.md)). Contributor counts (ticket #41) show as *The Hub in numbers*, a table by quarter, only when the snapshot has `metrics.json` ([hub/README.md](../hub/README.md#contributor-metrics)).

Without JavaScript the whole list shows. `hub.js` reveals the search, the label tabs (radio buttons) and the language, project and age filters (radio groups, with their counts from the build), hides the cards that don't match, and updates the count, a `role="status"` region, so screen readers hear it (after a pause while typing). Filters are kept in the address (`?lang=Python&kind=gfi`), so a filtered view can be shared; a project card's issue count links to its issues the same way. On phones the filters fold under *Filters*. Counted phrases use the CLDR plural categories (`fmt.plural`, `Intl.PluralRules` in the browser), so Arabic gets its zero, one, two, few and many forms.

`pages/localisation.py` builds the localisation page (`/hub/localisation/`, ticket #40, PRD HUB-08): teams that translate open-source software into Arabic and Tamazight on Pontoon, Weblate and Crowdin, grouped by language, how to start, and the note that this work doesn't show up in the Index (it is pushed from the platforms' servers). The teams come from `content/localisation.json`; `load()` stops the build if an entry has an unknown platform or language, a link that isn't https, or text missing in either language. The Hub page links to it in a short *Prefer words to code?* band.

## Holding page

`holding/` is the pre-launch page. Deploy it with no build command and `site/holding` as the output directory.
