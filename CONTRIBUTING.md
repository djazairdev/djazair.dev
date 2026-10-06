# Contributing

Thanks for helping. You can help in three ways.

## List a project in the Hub

The Hub lists active open-source projects with Algerian maintainers or a clear link to Algeria. A project must have all of these:

1. An OSI-approved open-source licence.
2. At least one commit in the last 90 days.
3. A README and a CONTRIBUTING file.
4. At least 3 open issues labelled `good first issue` or `help wanted`.
5. Maintainers who pledge to respond to newcomer pull requests within 7 days.
6. The GitHub topic `djazairdev` on the repository. Only maintainers can set topics, so this shows the listing is yours to ask for.
7. Algerian maintainers, or clear relevance to Algeria (local data, languages, payments, public services and so on).

A code of conduct is recommended. No djazair.dev account is needed.

To apply, add an entry at the end of [`projects.yml`](projects.yml) in a pull request:

```yaml
  - repository: owner/name       # the GitHub repository
    category: library            # app, library, tool or dataset
    tags: [arabic, payments]     # one to five tags from the table below
    maintainer_pledge: true      # you reply to newcomer pull requests within 7 days
    added: 2026-10-06            # today's date
```

Don't add the language, licence or activity: they're read from GitHub. CI checks the entry against [`hub/projects.schema.json`](hub/projects.schema.json) and names any field to fix; you can run the same check with `python3 -m hub check-registry`. Editors that read the `yaml-language-server` comment at the top of the file check it as you type.

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

## Review translations

Text is written in English and translated into Arabic. Nothing is published until a fluent speaker has reviewed it. If you can review Arabic, open an issue.

## Report a problem

Open an issue for wrong data, broken pages or unclear text. For security problems, follow [SECURITY.md](SECURITY.md) instead.

## Pull requests

- Keep each pull request to one change, and explain why it's needed.
- Never commit secrets, tokens or personal data.
- By contributing, you agree that your work is released under the matching licence: MIT for code, CC BY 4.0 for text and charts, CC0 for derived data.
