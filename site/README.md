# site

The static website, in English and Arabic (right to left), built by a small Python builder that uses only the standard library (decision D21 in the PRD). Output is plain HTML, one stylesheet and a small script that only enhances: every page works without JavaScript. Hosted on Cloudflare Pages.

## Build and preview

Needs Python 3.12 or later, nothing else.

```sh
python3 site/build.py                                         # writes site/dist
python3 -m http.server 4322 --bind 127.0.0.1 --directory site/dist
```

Then open <http://localhost:4322/>.

## How it's organised

| Path | What it holds |
|---|---|
| `build.py` | Entry point |
| `djsite/routes.py` | Every page and its path under `/en/` and `/ar/` |
| `djsite/layout.py` | The page shell: head, skip link, header, Index sub-nav, notices, footer |
| `djsite/components.py` | Shared components (buttons, eyebrow, page head…) |
| `djsite/pages/` | One renderer per page; `root.py` is the language chooser at `/` |
| `djsite/i18n.py`, `i18n/*.json` | Interface strings (see below) |
| `djsite/markup.py` | HTML escaping: everything that isn't our own markup goes through `esc()` |
| `static/css/` | Stylesheets, concatenated in file-name order into one hashed file |
| `static/js/` | `site.js` (every page) and page-specific scripts |
| `static/fonts/` | Self-hosted Tajawal and JetBrains Mono woff2 subsets, with their licences (SIL OFL 1.1) |
| `tools/fetch_fonts.py` | Re-downloads the fonts and writes `static/css/05-fonts.css`; only needed to update them |
| `djsite/palette.py` | Chart colours for downloaded SVG and PNG files (dark and light) |
| `holding/` | The pre-launch page served at djazair.dev until launch |

## Design tokens

`static/css/00-tokens.css` holds every colour, type size, spacing step, radius and easing from the Foundations board ([docs/design/system-foundations.png](../docs/design/system-foundations.png)). Other stylesheets use only these custom properties; `tests/test_design_tokens.py` fails on a raw colour anywhere else and checks that text colours meet WCAG AA on every surface. With `prefers-reduced-motion: reduce`, nothing animates.

## Routes and languages

Pages live at `/en/<path>` and `/ar/<path>` with matching `lang`, `dir`, `hreflang` and canonical links. The language switcher keeps the reader on the same page.

`/` picks a language with a small inline script: the language the reader last chose with the switcher (kept in `localStorage`), otherwise the first Arabic or English entry in the browser's preferred languages, otherwise English. Without JavaScript, `/` is a plain bilingual chooser. Each language also has its own `404.html`; Cloudflare Pages serves the nearest one.

## Strings

English (`i18n/en.json`) is the source: a key a page uses but `en.json` lacks fails the build. A key missing from `ar.json` falls back to English, marked `lang="en"`, and the page says that some text isn't translated yet. Arabic is AI-drafted, so until a fluent reviewer signs it off (`_meta.reviewed` in `ar.json`), Arabic pages say the text is a draft (PRD D13).

## Holding page

`holding/` is the pre-launch page. Deploy it with no build command and `site/holding` as the output directory.
