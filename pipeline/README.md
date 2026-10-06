# pipeline

Turns each [GitHub Innovation Graph](https://github.com/github/innovationgraph) release into the Algeria Developer Index (PRD §9). Python 3.12+, standard library only. GitHub Actions runs it daily; you can run every step by hand:

```sh
python3 -m pipeline fetch      # archive the latest release if it is new
```

## Steps

1. **Fetch** (`fetch`): finds the latest commit that touches `data/` in `github/innovationgraph`. If it isn't archived yet, it downloads the eight files (`developers`, `git_pushes`, `repositories`, `organizations`, `languages`, `topics`, `licenses`, `economy_collaborators`, about 10 MB), checks each against the git hash GitHub lists for it, and archives them in `data/raw/<commit>/` with `SHA256SUMS` and `release.json`. The folder appears complete or not at all, an archived release is never overwritten, and running `fetch` again changes nothing.

Every later step reads the archive through `release.Archive`, which checks each file against `SHA256SUMS` before using it.

Set `GITHUB_TOKEN` to raise the GitHub API rate limit; it's optional for a run by hand. In GitHub Actions, `fetch` also writes `new`, `commit` and `quarter` to `$GITHUB_OUTPUT`.

## Tests

`tests/test_pipeline_*.py`. They use a small made-up release (`tests/igfixture.py`) served by a fake GitHub, so they never touch the network, plus the archived Q1 2026 release.
