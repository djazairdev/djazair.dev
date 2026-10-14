# List a project in the Hub: the details

[CONTRIBUTING.md](../CONTRIBUTING.md#list-a-project-in-the-hub) gives the seven checks and the two ways to apply. This page has the rest: the `projects.yml` entry, how djazairdev's own repositories join, how a project stays listed, and the categories and tags.

## The entry

```yaml
  - repository: owner/name       # the GitHub repository
    category: library            # app, library, tool or dataset
    tags: [arabic, payments]     # one to five tags from the table below
    maintainer_pledge: true      # you reply to newcomer pull requests within 7 days
    added: 2026-10-06            # today's date
```

Don't add the language, licence or activity: they're read from GitHub. CI checks the entry against [`hub/projects.schema.json`](../hub/projects.schema.json) and names any field to fix; you can run the same check with `python3 -m hub check-registry`. Editors that read the `yaml-language-server` comment at the top of the file check it as you type.

## djazairdev's repositories

**Projects in the djazairdev organisation need no entry.** A [djazairdev](https://github.com/djazairdev) repository joins the Hub at the next refresh once its topics, under *About → Topics*, give all three:

- `djazairdev`;
- its category: one of `app`, `library`, `tool` or `dataset`;
- one to five tags from the table below, such as `arabic` or `open-data`.

Forks and archived repositories are left out. An entry in `projects.yml` wins over the topics. If a repository carries `djazairdev` but its category or tags are missing, the [health report](https://github.com/djazairdev/djazair.dev/blob/hub-data/HEALTH.md) says what to add. djazairdev's repositories follow its [project template](https://github.com/djazairdev/project-template), whose CONTRIBUTING file makes the maintainer pledge, and only the organisation's maintainers can create them or set their topics.

## Staying listed

Every 6 hours the Hub refreshes each project's beginner issues and checks its health. A project with no commit in 90 days is flagged, and hidden after 14 days if nothing changes; it comes back as soon as it's fixed. A project with no open beginner issues stays listed, with nothing in the issue feed until it labels one. Removing the `djazairdev` topic takes a project off the Hub at the next refresh. The [health report](https://github.com/djazairdev/djazair.dev/blob/hub-data/HEALTH.md) lists every flagged project, why, and since when. To help newcomers, add a line such as `You'll need: Python, pytest` to an issue; the Hub shows it on the issue's card.

## Categories and tags

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
