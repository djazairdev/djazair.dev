# Arabic review

The Arabic text was drafted with AI and hasn't been checked by a fluent reader yet, so every Arabic page says it is a draft. Before launch, a fluent reviewer checks all of it and signs it off (PRD D13, ticket [#33](https://github.com/djazairdev/djazair.dev/issues/33)). No unreviewed machine translation ships.

## What to review

| What | Where it lives | How to review it |
| --- | --- | --- |
| Interface strings: navigation, headings, chart titles and labels, buttons, notes (962) | `site/i18n/ar.json` | In a spreadsheet (below), or on the pages |
| Methodology and About | `content/methodology/ar.md`, `content/about/ar.md` | On the pages; suggest changes in a pull request or an issue |
| Quarterly report #1 | `content/reports/2026-q1/ar.md` | On the page (`/ar/reports/2026-q1/`); its figures are filled in by the site ([reports.md](reports.md)) |
| Numbers, quarters and dates | `site/djsite/fmt.py` | On the pages: `586.990`, `49,1%`, `الربع الأول 2026`, `7 جويلية 2026` |
| The tagline | `site.tagline` | «نُنمّي منظومة المطوّرين في الجزائر» |
| The share images | `site/static/share/ar.png`, and the quarter's card in `site/static/share/<quarter>/ar.png` | The first takes its text from `share.*` and the tagline, the quarter's from Home's `home.*` strings; redraw them with `site/tools/share.py` after a change |

Pages to read, in Arabic: Home, the Index (Overview, Peers, Trends, Languages, Topics, Collaboration, Rankings), the Hub and its localisation page, Reports and report #1, Methodology, Data and About; and a chart embed (*تضمين* → *معاينة* under a chart). Run the site locally (see the [README](../README.md#run-it-locally)) and open `/ar/`, or use the pull request's preview link.

## Reviewing in a spreadsheet

```bash
python3 site/tools/strings.py export arabic-review.csv
```

This writes every string with its key, the English, and the current Arabic. Open it in any spreadsheet app, write corrections in the *Corrected Arabic* column (leave it empty where the Arabic is right) and questions in *Notes*. Keep every `{placeholder}` as it is: the site fills them with numbers and names. Then:

```bash
python3 site/tools/strings.py import arabic-review.csv
python3 site/build.py
```

The import applies only the corrections, refuses one that drops or adds a placeholder, and changes nothing else. Check the pages, then open a pull request.

## Terms already used

Keep these consistent, or change them everywhere:

| English | Arabic |
| --- | --- |
| Algeria Developer Index | مؤشر المطوّرين في الجزائر |
| Project Hub | مركز المشاريع |
| developer accounts | حسابات المطوّرين |
| peers, peer groups | النظراء، مجموعات المقارنة |
| median (North African) | الوسيط (وسيط شمال أفريقيا) |
| pushes per account | عمليات الدفع لكل حساب |
| public repositories | المستودعات العامة |
| organisations | المنظّمات |
| accounts per million people | الحسابات لكل مليون نسمة |
| year-on-year growth | النموّ السنوي |
| quarter (Q1 2026) | الربع (الربع الأول 2026) |
| issue (on GitHub) | مهمة، مهام |
| topic (on GitHub) | موضوع |
| label (on GitHub) | وسم |
| licence | ترخيص |

Numbers use Western digits, a full stop between thousands and a comma before decimals (`586.990`, `49,1%`), as `ar-DZ` does. Months use the Algerian names (جانفي، فيفري، مارس، أفريل، ماي، جوان، جويلية، أوت، سبتمبر، أكتوبر، نوفمبر، ديسمبر). Chart time axes run left to right, as in English.

## Sign-off

Record each page here, in the pull request that makes the corrections:

| Page | Reviewer | Date | Pull request |
| --- | --- | --- | --- |
| Home | | | |
| Index: Overview | | | |
| Index: Peers | | | |
| Index: Trends | | | |
| Index: Languages | | | |
| Hub | | | |
| Methodology | | | |
| Data | | | |
| About | | | |
| Charts, numbers and dates | | | |

When every row is signed, set `"reviewed": true` in the `_meta` block of `site/i18n/ar.json`, in the same pull request. The draft notice then disappears from the Arabic pages. New Arabic text added later needs the same check before it ships.
