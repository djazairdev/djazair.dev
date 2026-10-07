# Designs

Pictures of the djazair.dev pages, for the GitHub issues and for review. There are two kinds:

- **Board exports** come from the boards on the djazair.dev design canvas: Home, Overview, Trends, Hub, Methodology and the design system. The canvas stays their source of truth.
  - Desktop boards are 1440 px wide at 1×.
  - Phone boards are 390 px wide at 2× (Methodology at 1.5×).
- **Pictures of the built site** cover the pages that were built straight in the design system: Peers, Languages, Data, About, Reports, the report page, the 404 page, and the Arabic Trends, Hub and Methodology. `python3 site/tools/screens.py` takes them from `site/dist` (ticket [#17](https://github.com/djazairdev/djazair.dev/issues/17)).
  - Full pages are at 1×.
  - First screens are at 2× on phones.

Each `-top.png` is the first screen of its page, used as the preview in GitHub issues.

[Section 5 of the implementation plan](../implementation-plan.md#5-designs-and-their-tickets) lists which ticket builds each page. When a page changes, re-export it here under the same file name, so the issues always show the current design.
