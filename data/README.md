# data

| Folder | What it holds | Licence |
|---|---|---|
| `raw/<commit>/` | One archived GitHub Innovation Graph release per folder, named after the source commit | CC0 (as published by GitHub) |
| `derived/<yyyy-qN>/` | The Index: indicators computed by `pipeline/`, as CSV and JSON | CC0 ([LICENSE-data](../LICENSE-data)) |

Data: GitHub Innovation Graph (CC0).

## Raw archive

Each `raw/<commit>/` folder holds the eight files of the release exactly as GitHub published them, plus:

- `SHA256SUMS`: the SHA-256 of every file, in `sha256sum` format (`sha256sum -c SHA256SUMS` checks them);
- `release.json`: the source commit, its date and message, the data quarter (the latest quarter in `developers.csv`), and each file's size and checksum.

The pipeline only writes a release folder once and never changes it afterwards. Each new release adds about 10 MB of files, but releases repeat most of the previous release's rows, so git stores them compactly.
