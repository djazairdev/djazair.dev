# Instructions for coding agents

<!-- djazairdev-template: 1.5.2 -->

This file tells coding agents (Claude Code, Codex, Cursor, Copilot and others) how to work in this repository. People may find it useful too.

## The project

djazair.dev has two parts: the Algeria Developer Index, computed every quarter from GitHub Innovation Graph data by `pipeline/`, and the Project Hub, kept by `hub/` from [`projects.yml`](projects.yml). `site/` builds both into a static site, in English and Arabic, from the strings in `site/i18n/`. Everything is Python 3.12+ with the standard library only.

## Commands

```bash
python3 -m unittest discover -s tests   # the tests (CI runs them on Python 3.12 and 3.13)
python3 site/build.py                   # build the site into site/dist
python3 -m hub check-registry           # check projects.yml
```

There is nothing to install, no linter and no formatter.

## Rules

- Run the tests before you say a change is done, and say if they fail.
- Keep each change small and focused on one thing; match the code around it.
- Add a test when you change behaviour.
- **The standard library only.** Don't add a Python package, a JavaScript library or a build tool.
- **Real numbers only.** Every figure comes from the published data in `data/derived/`, or from a source the page names. Never make up or round off a statistic for a design or an example.
- **Both languages.** A string a page shows goes in `site/i18n/en.json` and `site/i18n/ar.json` under the same key. Arabic is right to left, but charts keep a left-to-right time axis and maps are never mirrored.
- **Accessible and light.** Pages work with a keyboard, a screen reader and 200% zoom, and without JavaScript; motion respects reduced motion ([docs/accessibility.md](docs/accessibility.md)). Stay within the budgets in [docs/performance.md](docs/performance.md).
- **The design system.** New pages and components follow the tokens and components in [docs/design/](docs/design/).
- Never commit secrets, tokens, `.env` files or personal data, including personal deploy addresses.
- Don't push, merge, publish, deploy, or change repository settings unless the maintainer asks. Never open an issue, a pull request or a comment on your own: a person reviews and submits them ([CONTRIBUTING.md](CONTRIBUTING.md#ai-assisted-contributions)).
- Don't change the licences.
