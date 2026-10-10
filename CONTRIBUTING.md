# Contributing

<!-- djazairdev-template: 1.5.2 -->

Thanks for helping. Newcomers are welcome: you don't need to be an expert, and no question is too small. You can help with the site's code and data, with Arabic, or by listing a project in the Hub.

## Find something to work on

- Issues labelled [good first issue](https://github.com/djazairdev/djazair.dev/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) are small and well described. [help wanted](https://github.com/djazairdev/djazair.dev/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) issues need more context but are ready for anyone.
- Comment on the issue to say you're working on it, so no one else starts the same thing. If you stop, say so.
- For anything bigger than a small fix, open an issue first and agree on the approach.

## Set up

Everything is Python 3.12+ with the standard library only, so there's nothing to install.

```sh
git clone https://github.com/djazairdev/djazair.dev
cd djazair.dev
python3 site/build.py                                                # build the site into site/dist
python3 -m http.server 4322 --bind 127.0.0.1 --directory site/dist   # preview at http://localhost:4322/
```

## Run the checks

CI runs the same commands on every pull request, on Python 3.12 and 3.13, then builds the site and measures its load times:

```sh
python3 -m unittest discover -s tests   # the tests
python3 site/build.py                   # the build
python3 -m hub check-registry           # projects.yml, if you changed it
```

## Follow the rules

- Keep each pull request to one change, and explain why it's needed.
- Pages stay usable with a keyboard, a screen reader and zoom, in both languages. The tests check the markup; [docs/accessibility.md](docs/accessibility.md) lists the checks to make by hand.
- Every figure comes from the published data. Never make up a number, even for an example.
- No new dependencies: the code uses Python's standard library, and the pages plain HTML, CSS and JavaScript.
- Never commit secrets, tokens or personal data.

[AGENTS.md](AGENTS.md) has the full list, for people and for coding agents.

## Send a pull request

1. Fork the repository and create a branch from `main`.
2. Make one change per pull request, with a test when you change behaviour.
3. Run the checks above.
4. Open the pull request, say what it changes and why, and link the issue (`Closes #12`).
5. Give it a short title in the [Conventional Commits](https://www.conventionalcommits.org) form, such as `fix(hub): show issues with no labels` or `feat(site): add the Topics page`.

## Review

- A maintainer reviews every pull request; we may ask for changes, which is normal.
- **CI on a pull request from a fork waits until a maintainer approves the run.** That's a safety setting, not a judgement on your change.
- Answer review comments with new commits rather than a force-push, so the conversation stays readable. The squash merge tidies the history.
- A maintainer merges once CI passes and every conversation is resolved.
- Nothing is closed automatically. If a pull request goes quiet for a long time, we ask before we close it.

## AI-assisted contributions

You're welcome to use AI coding tools, on these terms:

- **You are the author.** Understand every line you submit, and be ready to explain it in review. "The model wrote it" doesn't answer a review comment.
- **Say so.** Tick the AI box in the pull request template, and name the tool and what it did. A commit may credit it in a `Co-Authored-By:` or `Assisted-by:` trailer.
- **Run the checks yourself,** and report the results you actually got.
- **Point your agent at [AGENTS.md](AGENTS.md).** Most coding agents read it on their own, and its rules bind them as they bind you.
- **No autonomous agents.** A person writes or reviews every issue, pull request and comment; an agent may not open them on its own.
- **Check what a tool finds** before you report it, and report security problems privately. An unchecked report is closed.
- **Keep private things out of AI tools:** unpublished security reports, other people's personal data, and any secret.
- Maintainers may close a low-effort generated pull request or issue without a detailed review.

## Our pledge

The maintainers reply to every newcomer's pull request within 7 days, even if only to say when we'll review it.

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

Have an idea for an open-source project that would help people in Algeria, but no repository yet? Propose it in the [Ideas board](https://github.com/djazairdev/djazair.dev/discussions/categories/ideas), with its short form: the problem, who benefits, a champion who will lead it, and the skills it needs. Anyone with a GitHub account can upvote an idea. Every quarter, djazair.dev adopts the idea with the most votes among those with a champion and at least 10 votes, and gives it a repository in the djazairdev organisation. [docs/hub-ideas.md](docs/hub-ideas.md) explains the vote.

## Add a translation team

The Hub's [localisation page](https://djazair.dev/en/hub/localisation/) links to teams that translate open-source software into Arabic or Tamazight on Pontoon, Weblate or Crowdin. To add one, edit [`content/localisation.json`](content/localisation.json): the project's name, its platform, one sentence in English and Arabic on what is translated there, and the link to each language team. List public teams that welcome new translators, and link to the team's page for the language, not the project's home page. The *Link check* workflow opens every link each Monday.

## Translate the site into Arabic

The site is in English first, and the community brings it to Arabic: [#62](https://github.com/djazairdev/djazair.dev/issues/62) lists the pages and how to help. Nothing in Arabic is published until a fluent speaker has reviewed it: [docs/arabic-review.md](docs/arabic-review.md) explains what to check, the terms already used, and how to review every string in a spreadsheet. Quarterly reports follow their own checklist, including a second reader for every number: see [docs/reports.md](docs/reports.md).

## Report a problem

[Report a bug](https://github.com/djazairdev/djazair.dev/issues/new?template=bug.yml) for a broken page or unclear text, or [wrong data](https://github.com/djazairdev/djazair.dev/issues/new?template=correction.yml). Ask questions in [djazairdev's discussions](https://github.com/orgs/djazairdev/discussions/categories/q-a).

## Conduct and security

Everyone follows the [code of conduct](https://github.com/djazairdev/.github/blob/main/CODE_OF_CONDUCT.md). Report security problems privately, as [SECURITY.md](SECURITY.md) says, never in a public issue.

## Licence

djazair.dev uses three licences: MIT for code ([LICENSE](LICENSE)), CC BY 4.0 for text and charts ([LICENSE-content](LICENSE-content)), and CC0 1.0 for derived data ([LICENSE-data](LICENSE-data)). By submitting a contribution, you agree that it's released under the matching licence, as section D.6 of [GitHub's Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) provides, and that you have the right to submit it. Don't submit work you didn't create unless its licence allows that, and say where it came from.
