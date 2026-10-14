#!/usr/bin/env bash
# Puts the Hub snapshot from the hub-data branch in data/derived/hub/, where the site build
# and the next sync read it (ticket #25). A fork doesn't copy that branch, so without it on
# origin the snapshot comes from the main repository (HUB_UPSTREAM; empty turns that off).
# Without the branch anywhere (before the first sync) the folder stays empty: the Hub shows no
# issues and the build still passes. If the branch can't be reached, this fails, so a deploy
# never drops the Hub by accident.
set -euo pipefail

dest=data/derived/hub
branch=hub-data
source=origin
upstream=${HUB_UPSTREAM-https://github.com/djazairdev/djazair.dev.git}

set +e
git ls-remote --exit-code --heads "$source" "$branch" > /dev/null
found=$?
if [ "$found" = 2 ] && [ -n "$upstream" ]; then
  source=$upstream
  git ls-remote --exit-code --heads "$source" "$branch" > /dev/null
  found=$?
fi
set -e

case "$found" in
  0)
    git fetch --quiet --depth=1 "$source" "$branch"
    rm -rf "$dest"
    mkdir -p "$dest"
    git archive FETCH_HEAD | tar -x -C "$dest"
    echo "Hub snapshot $(git rev-parse --short FETCH_HEAD) from the ${branch} branch of ${source}."
    ;;
  2)
    echo "::notice::No ${branch} branch yet: the site builds without Hub issues until the first sync."
    ;;
  *)
    echo "::error::Could not reach the ${branch} branch, so the Hub snapshot is missing." >&2
    exit 1
    ;;
esac
