#!/usr/bin/env bash
# Called by .github/workflows/hub.yml after a sync: saves data/derived/hub/ as a new commit on
# the hub-data branch, which holds only the snapshot, then runs CI on main, which builds the
# site with it and deploys (ticket #25). main itself never changes.
#
# Environment: GH_TOKEN, SUMMARY (the sync's log line), and the usual GITHUB_* and
# RUNNER_TEMP variables.
set -euo pipefail
# shellcheck source=run-ci.sh
source "$(dirname "$0")/run-ci.sh"

src=data/derived/hub
branch=hub-data
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

parent=''
if git ls-remote --exit-code --heads origin "$branch" > /dev/null; then
  git fetch --quiet --depth=1 origin "$branch"
  parent="$(git rev-parse FETCH_HEAD)"
fi

# Commit the folder as it is, with its own index, without touching the checkout.
git_dir="$(git rev-parse --absolute-git-dir)"
index="${RUNNER_TEMP}/hub-index"
rm -f "$index"
(cd "$src" && GIT_DIR="$git_dir" GIT_WORK_TREE=. GIT_INDEX_FILE="$index" git add --all .)
tree="$(GIT_INDEX_FILE="$index" git write-tree)"

if [ -n "$parent" ] && [ "$(git rev-parse "${parent}^{tree}")" = "$tree" ]; then
  echo "The snapshot didn't change: nothing to save or deploy."
  exit 0
fi

commit="$(git -c user.name='github-actions[bot]' -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
            commit-tree "$tree" ${parent:+-p "$parent"} -m "Sync the Hub" -m "${SUMMARY:-}" -m "Run: ${run_url}")"
git push --quiet origin "${commit}:refs/heads/${branch}"
echo "Snapshot ${commit:0:12} saved on ${branch}."

run_ci main
echo "::notice::Hub synced: CI on main passed with the new snapshot."
