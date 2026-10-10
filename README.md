<p align="center">
  <img src="site/holding/mark.svg" width="96" height="96" alt="">
</p>

<h1 align="center">djazair.dev</h1>

<p align="center"><em>Growing Algeria's developer ecosystem</em></p>

<p align="center">
  <a href="https://github.com/djazairdev/djazair.dev/actions/workflows/ci.yml"><img src="https://github.com/djazairdev/djazair.dev/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/djazairdev/djazair.dev/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22"><img src="https://img.shields.io/github/issues/djazairdev/djazair.dev/good%20first%20issue?label=good%20first%20issues&color=7057ff" alt="Good first issues"></a>
  <a href="https://github.com/djazairdev/djazair.dev/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement+sort%3Areactions-%2B1-desc"><img src="https://img.shields.io/github/issues/djazairdev/djazair.dev/enhancement?label=improvements&color=a2eeef" alt="Improvements"></a>
</p>

djazair.dev helps Algerian developers find their first open-source contribution, and shows how Algeria's developer community is growing:

- **Project Hub**: open-source projects by Algerian developers, or relevant to Algeria, with beginner-friendly issues to start on.
- **Algeria Developer Index**: Algeria's GitHub activity compared with similar countries, updated every quarter from [GitHub Innovation Graph](https://github.com/github/innovationgraph) data.

**Status:** pre-launch, planned for 30 November 2026 ([#1](https://github.com/djazairdev/djazair.dev/issues/1)). The site is in English first. Arabic comes with the community's help: [#62](https://github.com/djazairdev/djazair.dev/issues/62).

## Run it locally

Python 3.12+ and its standard library are all you need:

```sh
python3 site/build.py                                                # build the site into site/dist
python3 -m http.server 4322 --bind 127.0.0.1 --directory site/dist   # preview at http://localhost:4322/
python3 -m unittest discover -s tests                                # run the tests
```

Everything else is in [`docs/`](docs/).

## Make your first contribution

1. Pick an issue labelled [good first issue](https://github.com/djazairdev/djazair.dev/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
2. Comment on it to say you're working on it.
3. Follow [CONTRIBUTING.md](CONTRIBUTING.md) to set up, test and open a pull request.
4. We reply to newcomers' pull requests within 7 days. A review or a merge may take longer.

You can help without writing code, too: translating the site into Arabic ([#62](https://github.com/djazairdev/djazair.dev/issues/62)), testing with a screen reader, reporting wrong data, and [listing your project in the Hub](CONTRIBUTING.md#list-a-project-in-the-hub).

## Feedback

- [Ask a question](https://github.com/orgs/djazairdev/discussions/categories/q-a)
- [Report a bug](https://github.com/djazairdev/djazair.dev/issues/new?template=bug.yml), or [wrong data](https://github.com/djazairdev/djazair.dev/issues/new?template=correction.yml)
- [Suggest an improvement](https://github.com/djazairdev/djazair.dev/issues/new?template=idea.yml), or 👍 the [improvements](https://github.com/djazairdev/djazair.dev/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement+sort%3Areactions-%2B1-desc) you want most
- [Propose a new project](https://github.com/djazairdev/djazair.dev/discussions/categories/ideas) for Algeria, and vote for the ideas you want built
- Follow djazairdev on [Facebook](https://www.facebook.com/djazairdev) and [X](https://x.com/djazairdev) for news

Ask in Arabic, Tamazight, French or English. Code, docs and issue titles are in English, so everyone can search them. Report security problems [privately](https://github.com/djazairdev/djazair.dev/security/policy), never in an issue.

## Licence

Code: [MIT](LICENSE). Text and charts: [CC BY 4.0](LICENSE-content). Derived data: [CC0 1.0](LICENSE-data). The djazair.dev name and logo are not covered by these licences.

Data: GitHub Innovation Graph (CC0). djazair.dev is an independent community project. It is not affiliated with or endorsed by GitHub.

---

Part of [djazairdev](https://github.com/djazairdev): growing Algeria's open-source community through useful projects, welcoming first contributions and collaboration. Everyone follows our [code of conduct](https://github.com/djazairdev/.github/blob/main/CODE_OF_CONDUCT.md).
