# Performance

Many readers in Algeria are on phones and mobile data, so pages stay small and show fast on a slow connection (PRD §11, ticket [#30](https://github.com/djazairdev/djazair.dev/issues/30)).

## Budgets

| Budget | Applies to | Checked by |
| --- | --- | --- |
| Largest Contentful Paint (LCP) ≤ 2.5 s on a mid-range Android phone over 4G | The Index Overview, both languages; other pages are reported | `site/tools/perf.py`, in CI |
| ≤ 300 KB transferred per page, compressed, fonts apart | Every page | `tests/test_performance.py` and `site/tools/perf.py` |
| Nothing blocks the first paint but the page itself | Every page | `tests/test_performance.py` |

## Measuring load times

```bash
python3 site/build.py
python3 site/tools/perf.py
```

`site/tools/perf.py` serves `site/dist` gzipped, as the live site is, and loads each page cold in Chrome the way Lighthouse's mobile preset does: a 412 px phone screen, a CPU four times slower and slow 4G (562 ms per request, 1.5 Mbit/s). It reports the median LCP and First Contentful Paint (FCP) of three loads, the bytes transferred and the element that was the LCP. It uses the installed Chrome and the Python standard library only; set `CHROME` to Chrome's path if it isn't found. `--cpu 8` simulates a slower phone.

CI runs it on every pull request and push in the *Measure load times* job, and prints the table in the job summary. Lab numbers are an estimate: real phones and networks vary. Lighthouse itself isn't used because it needs Node, which the project doesn't (decision D21).

## Results

Measured on 7 October 2026 with the Q1 2026 data and the local Hub snapshot, median of three loads at four times slower CPU:

| Page | LCP | FCP | Bytes without fonts | Fonts |
| --- | --- | --- | --- | --- |
| `/en/` Home | 1.33 s | 1.01 s | 34.8 KB | 70.3 KB |
| `/en/index/` Overview | 0.94 s | 0.94 s | 27.4 KB | 80.1 KB |
| `/en/index/trends/` | 0.93 s | 0.93 s | 64.5 KB | 80.1 KB |
| `/en/hub/` | 0.93 s | 0.93 s | 28.0 KB | 70.3 KB |
| `/ar/` Home | 1.52 s | 1.10 s | 35.9 KB | 88.5 KB |
| `/ar/index/` Overview | 1.03 s | 1.03 s | 28.2 KB | 107.1 KB |
| `/ar/index/trends/` | 0.99 s | 0.99 s | 65.8 KB | 107.1 KB |
| `/ar/hub/` | 1.03 s | 1.03 s | 28.9 KB | 97.3 KB |

At eight times slower CPU, the Overview's LCP was 1.80 s before the stylesheet was inlined. The network, not the CPU, sets these times.

## What keeps pages fast

- **The stylesheet is inlined** in every page (about 15 KB compressed), so nothing waits for a second file before the first paint. This took the Overview's LCP from 1.58 s to 0.94 s. A visitor reading several pages downloads it again with each one, which costs less than the round trip it saves on the first.
- **Fonts are subset and swap in.** Tajawal comes in separate Latin and Arabic files per weight (about 10 KB each), and the browser only fetches the ones a page uses. JetBrains Mono is one variable file of 31 KB. Each page preloads the two the first screen needs, and text shows at once in a system font while they load (`font-display: swap`).
- **Scripts only enhance**, load with `defer` and are under 10 KB each (2 to 4 KB compressed). Nothing on the page waits for them.
- **Charts are drawn at build time** as inline SVG, so no chart library is downloaded. The unit map on Home is 587 squares, grouped by the year they joined: 42 KB of markup that compresses to under 5 KB.
- **Home's replay is CSS made for Home.** Its rules depend on the data, so the builder adds them to Home's inlined stylesheet only (about 1.7 KB compressed), and the loop rests while it is scrolled out of view, so it doesn't keep a phone busy further down the page.
- **Hashed files are cached for a year** (`_headers`): scripts and fonts download once.

## Known trade-offs

- **Trends has about 3,800 elements**, more than Lighthouse's 1,400 guideline, because all eight chart views and their tables are in the page so that it works without JavaScript. Its LCP is still under 1 s.
- **Home's LCP comes 0.3 to 0.4 s after its first paint.** The hero text fades in from transparent, and Chrome counts it only at the next repaint, when the web fonts arrive. Without the fade, LCP would equal FCP; it stays because it is part of the agreed motion design and the page is well within budget.
- **Font files keep their names** under `/assets/fonts/` and are cached for a year. If a font file ever changes, give it a new name.
