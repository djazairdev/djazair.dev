# Accessibility

djazair.dev aims for [WCAG 2.1](https://www.w3.org/TR/WCAG21/) level AA on every page, in English and in Arabic (PRD §11, ticket [#29](https://github.com/djazairdev/djazair.dev/issues/29)). This page says what is tested automatically, what was checked by hand and when, and what still needs people.

## How the site is built for it

- **Language and direction.** Every page sets `lang` and `dir` on `<html>`. Latin text inside Arabic pages (code, repository names, labels) is wrapped in `dir="ltr"` or `<bdi>`, so it isn't reordered.
- **Structure.** A skip link is the first link on every page and moves focus to `<main>`. The header, navigation, main content and footer are landmarks, and each navigation has its own name. Each page has one `<h1>` and headings don't skip levels.
- **Charts.** Every chart is an SVG with `role="img"`, a title and a description in the page's language, and a data table under it. On screens wider than 760 px, the Trends chart can be read with the keyboard (Left, Right, Home, End); each move is announced in a live region, for example "Q2 2025: Algeria 422,835, N. Africa median 333,356". Time axes run left to right in both languages and maps are never mirrored.
- **Controls.** Choices are real radio buttons and links, so they work without JavaScript and with the keyboard. The Hub's filter count is a live region with the plural forms of each language, updated once after typing stops.
- **Focus.** Everything that takes focus shows a 2 px mint ring (`:focus-visible`), at least 3:1 against every surface. Radio buttons drawn as chips or tabs pass their ring to their label.
- **Colour.** One dark theme. Text colours reach at least 4.5:1 on every surface, including the tinted badges and chips. Chart lines reach 3:1, except the peers dimmed while another peer is brought forward; their values stay in the table.
- **Motion.** With *Reduce motion* turned on in the operating system, nothing animates: charts and the unit map show fully drawn at once. Home's hero replays the years in a loop, so a button beside the year pauses it (WCAG 2.2.2). The button is a checkbox, so it works with the keyboard and without JavaScript. The loop also rests while it is scrolled out of view.

## Tested on every pull request

`tests/test_accessibility.py` builds the site and runs [`tests/a11y.py`](../tests/a11y.py) over every page in both languages. The checker uses the Python standard library only, like the rest of the project, so it checks what can be decided from the markup:

- `lang` and `dir`, a title, one `<main>` and a skip link;
- unique ids, and references (`aria-labelledby`, `aria-describedby`, `aria-controls`, `<label for>`, `#` links) that point to them;
- known ARIA roles, no positive `tabindex`, nothing focusable inside `aria-hidden`;
- names for images, SVGs, links, buttons, form fields, tables, field groups, regions and navigation landmarks;
- table headers with a scope, and one `<h1>` with no skipped heading levels.

The same file checks contrast from the colour tokens (`site/static/css/00-tokens.css`), that no style removes the focus ring, and that styles and scripts respect reduced motion. To run it:

```bash
python3 -m unittest discover -s tests -p test_accessibility.py
```

Tools like axe or Pa11y need Node and a browser in CI, which the project doesn't use. What they would add (layout, rendered contrast) is in the manual checks below.

## Checked by hand

Last full pass: 6 October 2026, in Chrome, on every page in both languages.

| Check | How | Result |
| --- | --- | --- |
| Keyboard | Tab through every page at 1280 px, and the phone menu at 375 px | Every stop shows the focus ring, none is hidden under the sticky header, the order follows the page, and there are no traps. The phone menu opens with Enter and closes with Escape, back on its button. |
| Trends chart | Arrow keys, Home and End on the chart, in both languages | The readout moves in the direction of the key. Quarters are announced in words ("Q2 2025", "الربع الثاني 2025"). |
| Reflow (zoom) | Every page at 320 px and 640 px wide, the same as 400% and 200% zoom of a 1280 px window | No page scrolls sideways. Wide tables scroll inside their own frame. |
| Text spacing | Line height 1.5, letter spacing 0.12 em, word spacing 0.16 em and paragraph spacing 2 em, at 390 px and 1280 px | Nothing overflows or is cut off. |
| Reduced motion | The home page with reduced motion on, captured 0.15 s after loading | The unit map and the headline figure show complete at once. Without reduced motion they are still animating at that point. |
| Hero replay | Home in both languages at 1440 px and 375 px, on 7 October 2026: the pause button with the mouse and with Tab and Space, scrolling the hero out of view, and Home without its replay rules | The button pauses and resumes the count, the year and the map, and shows the focus ring. The loop rests out of view and resumes when the hero is back. Without the rules, the latest quarter and the plain number show, and no button. |
| Unit map | Its name and description in both languages | "One square, 1,000 developer accounts", then what the squares mean and where the data table is. The Arabic text says the same. |

Run the manual checks again after changes to layout, navigation or a chart.

## Still needs people

- **Screen readers** (NVDA, JAWS, VoiceOver on macOS and iOS, TalkBack), in both languages: the Hub filters and count ([#47](https://github.com/djazairdev/djazair.dev/issues/47)) and the Trends chart and its table ([#49](https://github.com/djazairdev/djazair.dev/issues/49)).
- **Arabic figures read aloud.** Arabic pages group thousands with a full stop (`1.234`), following the site's number style. #49 asks how screen readers read them.
- **The phone chart** on Trends is read by dragging. On screens narrower than 760 px, keyboard and screen-reader users get the same values from the data table under it.

## Reporting a problem

Open an issue with the [`accessibility` label](https://github.com/djazairdev/djazair.dev/labels/accessibility). Say which page and language, what you used (browser, screen reader, zoom level) and what happened.
