#!/usr/bin/env bash
# Puts the Hub snapshot from the hub-data branch in data/derived/hub/, where the site build
# and the next sync read it (ticket #25). Without the branch (before the first sync, or in a
# fork) the folder stays empty: the Hub shows no issues and the build still passes. If the
# branch can't be reached, this fails, so a deploy never drops the Hub by accident.
set -euo pipefail

dest=data/derived/hub
branch=hub-data

set +e
git ls-remote --exit-code --heads origin "$branch" > /dev/null
found=$?
set -e

case "$found" in
  0)
    git fetch --quiet --depth=1 origin "$branch"
    rm -rf "$dest"
    mkdir -p "$dest"
    git archive FETCH_HEAD | tar -x -C "$dest"
    echo "Hub snapshot $(git rev-parse --short FETCH_HEAD) from the ${branch} branch."
    ;;
  2)
    echo "::notice::No ${branch} branch yet: the site builds without Hub issues until the first sync."
    ;;
  *)
    echo "::error::Could not reach the ${branch} branch, so the Hub snapshot is missing." >&2
    exit 1
    ;;
esac
