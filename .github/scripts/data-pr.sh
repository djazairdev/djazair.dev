#!/usr/bin/env bash
# Called by .github/workflows/data.yml after the new data passed validation, the tests and
# the build. Commits data/ on a branch, opens a pull request, runs CI on it, merges it when
# CI passes, then runs CI on main, which deploys the site (PRD §9.5, AC-IDX-4).
#
# A release that revises past values waits for editorial review: the pull request stays
# open, and merging it by hand deploys as any push to main does.
#
# Environment: QUARTER (2026-Q2), COMMIT (source release), REVISIONS (true/false), GH_TOKEN,
# and the usual GITHUB_* and RUNNER_TEMP variables.
set -euo pipefail

short="${COMMIT:0:12}"
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
notes="${RUNNER_TEMP}/failure-notes.md"         # read by data-failed.sh if a later step fails

if [ -z "$(git status --porcelain -- data)" ]; then
  echo "No file in data/ changed: nothing to publish."
  exit 0
fi

branch="data/$(echo "$QUARTER" | tr '[:upper:]' '[:lower:]')-${short}"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git switch -c "$branch"
git add -- data
git commit -q -m "Publish ${QUARTER} data from Innovation Graph ${short}" \
  -m "Source: https://github.com/github/innovationgraph/commit/${COMMIT}" -m "Run: ${run_url}"
git push -q --force origin "HEAD:refs/heads/${branch}"

body="${RUNNER_TEMP}/pull-request.md"
{
  echo "GitHub Innovation Graph published release [\`${short}\`](https://github.com/github/innovationgraph/commit/${COMMIT}) with ${QUARTER} data."
  echo "It passed validation, and the tests and the site build passed with the new data in [this run](${run_url})."
  echo
  echo "## Revisions"
  echo
  if [ -s "${RUNNER_TEMP}/revisions.md" ]; then cat "${RUNNER_TEMP}/revisions.md"; else echo "Nothing to compare with."; fi
  echo
  echo "## Validation"
  echo
  cat "${RUNNER_TEMP}/validation.md"
} > "$body"

pr="$(gh pr list --head "$branch" --state open --json number --jq '.[0].number // empty')"
if [ -z "$pr" ]; then
  if ! url="$(gh pr create --base main --head "$branch" --title "Publish ${QUARTER} data (Innovation Graph ${short})" \
                --body-file "$body" --label 'area: pipeline')"; then
    {
      echo "The new data is on the branch \`${branch}\`, but the workflow could not open a pull request."
      echo "Allow it once in *Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and"
      echo "approve pull requests*, or [open the pull request yourself](${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/compare/main...${branch}?expand=1)."
    } > "$notes"
    exit 1
  fi
  pr="${url##*/}"
else
  gh pr edit "$pr" --body-file "$body" > /dev/null
fi
echo "Pull request #${pr}"
echo "Pull request #${pr} is open for this release." > "$notes"

# Pull requests and merges made with the workflow token start no workflow, so start CI by hand.
run_ci() {
  local ref="$1" since id=''
  since="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  gh workflow run ci.yml --ref "$ref"
  for _ in $(seq 1 30); do
    sleep 10
    id="$(gh run list --workflow ci.yml --branch "$ref" --event workflow_dispatch --limit 5 --json databaseId,createdAt \
            --jq "map(select(.createdAt >= \"${since}\")) | .[0].databaseId // empty")"
    [ -n "$id" ] && break
  done
  if [ -z "$id" ]; then
    echo "CI did not start on ${ref}." >&2
    return 1
  fi
  echo "CI on ${ref}: ${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${id}"
  gh run watch "$id" --exit-status --interval 20 > /dev/null
}

run_ci "$branch"

if [ "${REVISIONS}" = 'true' ]; then
  gh pr comment "$pr" --body "This release changes past values (listed above). Review them, then merge: merging deploys the site."
  echo "::notice::The release revises past values: pull request #${pr} waits for editorial review."
  exit 0
fi

gh pr merge "$pr" --squash --delete-branch
echo "Pull request #${pr} was merged, but CI on \`main\` did not pass, so the site was not deployed." > "$notes"
touch "${RUNNER_TEMP}/merged"
run_ci main
echo "::notice::${QUARTER} data published: pull request #${pr} merged and CI on main passed."
