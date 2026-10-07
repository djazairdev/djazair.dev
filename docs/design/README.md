# Designs

Pictures of the djazair.dev pages, for the GitHub issues and for review. There are three kinds:

- **Board exports** come from the boards on the djazair.dev design canvas: Home, Overview, Trends, Hub, Methodology and the design system. The canvas stays their source of truth.
  - Desktop boards are 1440 px wide at 1×.
  - Phone boards are 390 px wide at 2× (Methodology at 1.5×).
- **Pictures of the built site** cover the pages that were built straight in the design system: Peers, Languages, Topics, Collaboration, Rankings, Data, About, Reports, the report page, the 404 page, the Hub's localisation page, Meetups, and the Arabic Trends, Hub and Methodology. `python3 site/tools/screens.py` takes them from `site/dist` (ticket [#17](https://github.com/djazairdev/djazair.dev/issues/17)). The same pages are on the canvas as boards, made from the built site.
  - Full pages are at 1×.
  - First screens are at 2× on phones.
- **Pictures of parts of pages**, for tickets that add to a page rather than make one:
  - `hub-ideas-en-*.png`: the Hub's Ideas section ([#39](https://github.com/djazairdev/djazair.dev/issues/39)), taken from a build with `HUB_IDEAS` on.
  - `embed-en-desktop.png` and `embed-ar-phone.png`: a chart with its Embed panel open ([#42](https://github.com/djazairdev/djazair.dev/issues/42)).
  - `embed-pages.png`: chart embeds inside iframes on another site, dark and light, wide and narrow.

  The quarter's share cards are in `site/static/share/<quarter>/` (`site/tools/share.py --release`).

Each `-top.png` is the first screen of its page, used as the preview in GitHub issues.

[Section 5 of the implementation plan](../implementation-plan.md#5-designs-and-their-tickets) lists which ticket builds each page. When a page changes, re-export it here under the same file name, so the issues always show the current design.
