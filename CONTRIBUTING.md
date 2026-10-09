# Contributing

Thanks for helping. You can help in three ways.

## List a project in the Hub

The Hub lists active open-source projects with Algerian maintainers or a clear link to Algeria. A project must have all of these:

1. An OSI-approved open-source licence.
2. At least one commit in the last 90 days.
3. A README and a CONTRIBUTING file.
4. Issues turned on, with the label `good first issue` or `help wanted` (GitHub adds both to new repositories). No number of open issues is required, but label a few: they are how newcomers find the project in the Hub.
5. Maintainers who pledge to respond to newcomer pull requests within 7 days.
6. The GitHub topic `djazairdev` on the repository. Only maintainers can set topics, so this shows the listing is yours to ask for.
7. Algerian maintainers, or clear relevance to Algeria (local data, languages, payments, public services and so on).

A code of conduct is recommended. Datasets may use an open data licence instead (CC0, CC BY 4.0, CC BY-SA 4.0, ODbL, ODC-By or PDDL). No djazair.dev account is needed.

You can apply in two ways:

- **Issue form**, if you'd rather not use git: [List a project in the Hub](https://github.com/djazairdev/djazair.dev/issues/new?template=hub-listing.yml).
- **Pull request**: add an entry at the end of [`projects.yml`](projects.yml). The pull request template lists the seven checks.

Either way, a bot runs checks 1 to 6 on GitHub within a minute and comments with the result (`listing-check · 6 of 7 passed, 1 waits for a reviewer`): what it found, and how to fix anything that fails. After fixing something, edit the issue or the pull request description to run the checks again. A person checks 7 and reviews the request within 7 days. You can run the same checks yourself with `python3 -m hub check-project owner/name --pledge`.

An entry looks like this:

```yaml
  - repository: owner/name       # the GitHub repository
    category: library            # app, library, tool or dataset
    tags: [arabic, payments]     # one to five tags from the table below
    maintainer_pledge: true      # you reply to newcomer pull requests within 7 days
    added: 2026-10-06            # today's date
```

Don't add the language, licence or activity: they're read from GitHub. CI checks the entry against [`hub/projects.schema.json`](hub/projects.schema.json) and names any field to fix; you can run the same check with `python3 -m hub check-registry`. Editors that read the `yaml-language-server` comment at the top of the file check it as you type.

**Staying listed.** Every 6 hours the Hub refreshes each project's beginner issues and checks its health. A project with no commit in 90 days is flagged, and hidden after 14 days if nothing changes; it comes back as soon as it's fixed. A project with no open beginner issues stays listed, with nothing in the issue feed until it labels one. Removing the `djazairdev` topic takes a project off the Hub at the next refresh. The [health report](https://github.com/djazairdev/djazair.dev/blob/hub-data/HEALTH.md) lists every flagged project, why, and since when. To help newcomers, add a line such as `You'll need: Python, pytest` to an issue; the Hub shows it on the issue's card.

**Categories:** `app` (something people use), `library` (code other programs use), `tool` (something developers use) or `dataset`.

**Tags** say how the project relates to Algeria:

| Tag | Use it when the project… |
|---|---|
| `algerian-maintainers` | is maintained by developers in or from Algeria |
| `arabic` | supports Arabic: right-to-left interfaces, Arabic text or speech |
| `darija` | works with Algerian Arabic (Darija) |
| `tamazight` | works with Tamazight languages or the Tifinagh script |
| `localisation` | translates or adapts software for people in Algeria |
| `open-data` | publishes or uses open data about Algeria |
| `public-services` | helps people use Algerian public services |
| `payments` | works with Algerian payment systems, such as CIB and Edahabia cards |
| `education` | serves Algerian schools, universities or learners |
| `maps` | covers Algeria's geography: wilayas, communes, addresses |
| `health` | serves health and healthcare in Algeria |
| `transport` | serves transport and mobility in Algeria |
| `agriculture` | serves farming and food in Algeria |
| `accessibility` | makes software usable by people with disabilities |
| `community` | supports Algeria's developer community: events, learning, this site |

If no tag fits, propose a new one in your pull request (add it to the schema and to this table).

## Propose a project idea

Have an idea for an open-source project that would help people in Algeria, but no repository yet? Ideas will live in GitHub Discussions, in an **Ideas** category with a short form: the problem, who benefits, a champion who will lead it, and the skills it needs. Anyone with a GitHub account can upvote an idea. Every quarter, djazair.dev adopts the idea with the most votes among those with a champion and at least 10 votes, and gives it a repository in the djazairdev organisation. Discussions isn't on yet: [docs/hub-ideas.md](docs/hub-ideas.md) explains the vote and how it starts. Until then, open an issue.

## Add a translation team

The Hub's [localisation page](https://djazair.dev/en/hub/localisation/) links to teams that translate open-source software into Arabic or Tamazight on Pontoon, Weblate or Crowdin. To add one, edit [`content/localisation.json`](content/localisation.json): the project's name, its platform, one sentence in English and Arabic on what is translated there, and the link to each language team. List public teams that welcome new translators, and link to the team's page for the language, not the project's home page. The *Link check* workflow opens every link each Monday.

## Review translations

Text is written in English and translated into Arabic. Nothing is published until a fluent speaker has reviewed it. If you can review Arabic, open an issue: [docs/arabic-review.md](docs/arabic-review.md) explains what to check, the terms already used, and how to review every string in a spreadsheet. Quarterly reports follow their own checklist, including a second reader for every number: see [docs/reports.md](docs/reports.md).

## Report a problem

Open an issue for wrong data, broken pages or unclear text. For security problems, follow [SECURITY.md](SECURITY.md) instead.

## Pull requests

- Keep each pull request to one change, and explain why it's needed.
- Never commit secrets, tokens or personal data.
- Changes to pages keep them usable with a keyboard, a screen reader and zoom, in both languages. The tests check the markup; [docs/accessibility.md](docs/accessibility.md) lists the checks to make by hand.
- By contributing, you agree that your work is released under the matching licence: MIT for code, CC BY 4.0 for text and charts, CC0 for derived data.
