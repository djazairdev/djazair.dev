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
| `djsite/data.py` | The Index data: the quarter `data/derived/latest.json` names, each file checked against its `manifest.json`, and the Hub's synced issues. The site reads no other data |
| `djsite/scorecard.py` | The six headline indicators as Home and the Index overview show them |
| `djsite/editorial.py` | Sentences tied to the data: computed facts (growth streaks) and the per-quarter headlines in `content/editorial/`, used only while their claims hold |
| `djsite/layout.py` | The page shell: head, skip link, header, Index sub-nav, notices, footer |
| `djsite/components.py` | Shared components: buttons, chips, chart controls, tiles, figure frame, source line, tables, disclosure, Hub issue rows, check panel, code sample |
| `djsite/charts.py` | Build-time SVG charts: line, bar and unit map, sparklines, rank strips; their CSV, JSON and SVG downloads |
| `djsite/figures.py` | A chart on a page: numbered label, wide and phone drawings, key, source line, downloads, data table |
| `djsite/unitmap.py`, `geo/algeria.json` | The unit map's layout inside Algeria's outline |
| `djsite/fmt.py` | Number, quarter and date formats for `en` and `ar-DZ` |
| `djsite/pages/` | One renderer per page; `root.py` is the language chooser at `/` |
| `djsite/i18n.py`, `i18n/*.json` | Interface strings (see below) |
| `djsite/markup.py` | HTML escaping: everything that isn't our own markup goes through `esc()` |
| `static/css/` | Stylesheets, concatenated in file-name order into one hashed file |
| `static/js/` | `site.js` (every page) and page-specific scripts |
| `static/fonts/` | Self-hosted Tajawal and JetBrains Mono woff2 subsets, with their licences (SIL OFL 1.1) |
| `tools/fetch_fonts.py` | Re-downloads the fonts and writes `static/css/05-fonts.css`; only needed to update them |
| `tools/make_outline.py` | Rebuilds `geo/algeria.json` from Natural Earth (public domain); only needed to change the outline |
| `djsite/palette.py` | Chart colours: dark (the page, equal to the tokens) and light, for downloads |
| `holding/` | The pre-launch page served at djazair.dev until launch |

## Design tokens

`static/css/00-tokens.css` holds every colour, type size, spacing step, radius and easing from the Foundations board ([docs/design/system-foundations.png](../docs/design/system-foundations.png)). Other stylesheets use only these custom properties; `tests/test_design_tokens.py` fails on a raw colour anywhere else and checks that text colours meet WCAG AA on every surface. With `prefers-reduced-motion: reduce`, nothing animates.

## Routes and languages

Pages live at `/en/<path>` and `/ar/<path>` with matching `lang`, `dir`, `hreflang` and canonical links. The language switcher keeps the reader on the same page.

`/` picks a language with a small inline script: the language the reader last chose with the switcher (kept in `localStorage`), otherwise the first Arabic or English entry in the browser's preferred languages, otherwise English. Without JavaScript, `/` is a plain bilingual chooser. Each language also has its own `404.html`; Cloudflare Pages serves the nearest one.

## Strings

English (`i18n/en.json`) is the source: a key a page uses but `en.json` lacks fails the build. A key missing from `ar.json` falls back to English, marked `lang="en"`, and the page says that some text isn't translated yet. Arabic is AI-drafted, so until a fluent reviewer signs it off (`_meta.reviewed` in `ar.json`), Arabic pages say the text is a draft (PRD D13).

## Numbers, quarters and dates

`djsite/fmt.py` formats numbers the way `Intl.NumberFormat` does for `en` (`586,990.5`) and `ar-DZ` (`586.990,5`, Western digits), with the typographic minus `−` for negative values. Quarters read "Q1 2026" or "الربع الأول 2026" in text and "2026 Q1" on axes and in tables; dates are Gregorian with Algerian month names in Arabic. Inside Arabic text, every figure goes through `num()`, which isolates it left to right so `+49,1%` keeps its sign on the left; `tests/test_i18n_format.py` checks every signed value on every Arabic page.

## Charts

Every chart is drawn at build time as SVG, so a page can be read without fetching data or running JavaScript. A chart is a language-neutral spec, `LineChart`, `BarChart` or `UnitMap` in `djsite/charts.py`: names and titles are `{'en': …, 'ar': …}` and formatters take `(value, lang)`. `figures.figure(ctx, chart, n, source=…)` puts it on a page with:

- a wide drawing and a phone drawing (they switch at 760 px), and a key on phones, where lines have no end labels;
- `role="img"` with a title and a description, and a data table with every value in a disclosure under the chart (AC-IDX-7);
- downloads (IDX-15): CSV and JSON (CC0, the same for both languages) at `/charts/<yyyy-qN>/<id>.csv` and `.json`, and SVG files in the dark and light palettes at `/charts/<yyyy-qN>/<lang>/<id>-dark.svg` and `-light.svg`, each with its title and credit line. PNG files are drawn from those SVG files in the browser, with the site's fonts embedded, so their menu items appear only with JavaScript.

Colours come from `djsite/palette.py`; on-page charts use the dark palette, which a test keeps equal to the CSS tokens. Time runs left to right in Arabic too; Arabic words are set right to left and figures left to right. End labels never overlap: labels that would collide form a group centred on their lines. The unit map fills Algeria's outline with one square per 1,000 accounts; the squares show quantity, never location, and the map is never mirrored. The same data always gives byte-identical files (`tests/test_charts.py`).

## Home

`djsite/pages/home.py` builds the hero (the account count, three stats, the unit map), the scorecard, the growth trend, the Hub teaser and the open-by-default links, all from the derived data. The count ticks up from the year-earlier value with CSS counters and no JavaScript; its rules depend on the data, so the builder generates them and adds them to the stylesheet (`ticker_css`). Readers who prefer reduced motion, and browsers without registered custom properties, see the plain number. The trend headline comes from `content/editorial/<yyyy-qN>.json` when the file exists and every claim it lists still holds; otherwise the section uses computed text.

The build also publishes the derived data as it is in `data/derived/`: `/data/<yyyy-qN>/<table>.csv` and `.json`, with `manifest.json` and `README.md`, and `/data/latest.json`.

Motion: Algeria's line draws as the chart scrolls into view (scroll-driven animations where the browser has them; elsewhere `site.js` draws charts below the fold over one second when they arrive), then the end dot and notes pop in, and unit-map squares appear in bands from Algiers. With `prefers-reduced-motion: reduce`, nothing moves.

## Holding page

`holding/` is the pre-launch page. Deploy it with no build command and `site/holding` as the output directory.
