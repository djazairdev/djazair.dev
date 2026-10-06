# pipeline

Turns each [GitHub Innovation Graph](https://github.com/github/innovationgraph) release into the Algeria Developer Index (PRD §9). Python 3.12+, standard library only. The `Data` workflow runs it daily and publishes new data through a pull request ([docs/deploy.md](../docs/deploy.md#data-updates)); you can run every step by hand:

```sh
python3 -m pipeline fetch      # archive the latest release if it is new
python3 -m pipeline validate   # check the latest archived release (--release <commit> for another)
python3 -m pipeline publish    # validate it, then write data/derived/<yyyy-qN>/ from it
python3 -m pipeline population # refresh the World Bank population cache (once a year is enough)
python3 -m pipeline revisions  # past values the latest release changed, against the release before it
```

## Steps

1. **Fetch** (`fetch`): finds the latest commit that touches `data/` in `github/innovationgraph`. If it isn't archived yet, it downloads the eight files (`developers`, `git_pushes`, `repositories`, `organizations`, `languages`, `topics`, `licenses`, `economy_collaborators`, about 10 MB), checks each against the git hash GitHub lists for it, and archives them in `data/raw/<commit>/` with `SHA256SUMS` and `release.json`. The folder appears complete or not at all, an archived release is never overwritten, and running `fetch` again changes nothing.

2. **Validate** (`validate`): before anything is computed, checks every file's columns, value types, economy codes and duplicate rows, and that the quarterly series run from 2020 Q1 to the release's quarter without gaps. Algeria must have every series in every quarter, and every economy the Index reports on (North Africa and the core peers) must have its account counts. GitHub leaves out small values, so a peer may miss a quarter of another series; that is a warning, and medians and ranks for that quarter use the members with data. A sharp fall in a running total is flagged too. If any check fails, nothing later runs: the last good derived data and the live site stay as they are, and the scheduled run opens an issue with the report (`--report FILE` writes it as Markdown).

3. **Compute** (`indicators.Index`): the PRD §9.2 indicators for every economy and quarter: developer accounts, year-on-year growth, growth since 2020, pushes per account (and its 4-quarter average), public repositories and organisations per account, accounts per million people and topics above GitHub's threshold, plus each economy's languages and collaboration partners. An indicator is missing, never zero, when an input is missing. Medians use the peer-group members with data; ranks are in descending order and ties share a rank. The groups (§9.3): North Africa (7), the core peers (6) and the Africa ranking group, every African economy with at least 20,000 accounts a year earlier, which therefore starts in 2021 Q1.

4. **Publish** (`publish`): validates the release, then writes `data/derived/<yyyy-qN>/`: eleven tables, each as CSV and as JSON (overview, peers, peer groups, ranks, quarterly trends, languages, Algeria's languages over time, topics, collaboration partners, every economy and quarter, and revised past values), a README, and `manifest.json` with the source release and every file's checksum. `data/derived/latest.json` then points at the newest quarter. Every file carries the CC0 licence and the attribution, output is stable for diffs, and publishing the same release again changes nothing. The site builds only from these files; [data/README.md](../data/README.md) documents every column.

5. **Check** (`revisions`, and `tests/test_baseline.py`): the pipeline must still reproduce PRD Appendix A from the Q1 2026 release: Algeria's headline figures, the peer table, the group medians, growth and ratio ranks, languages and partners. The appendix used 2024 population, so the baseline test pins that year. A new release is also compared with the previous archived one for every quarter that release covered: any changed, added or removed value in the four quarterly series is a *revision*, listed in a report for editorial review rather than passing silently.

Accounts per million use World Bank population (`SP.POP.TOTL`), each economy's latest year, from `data/population.json`. The file keeps every year since 2015 and the published data records the year used.

Every step reads the archive through `release.Archive`, which checks each file against `SHA256SUMS` before using it.

Set `GITHUB_TOKEN` to raise the GitHub API rate limit; it's optional for a run by hand. In GitHub Actions, `fetch` also writes `new`, `commit` and `quarter` to `$GITHUB_OUTPUT`, and `publish` writes `quarter` and `folder`.

## Tests

`tests/test_pipeline_*.py`. They use a small made-up release (`tests/igfixture.py`) served by a fake GitHub, so they never touch the network, plus the archived Q1 2026 release.
