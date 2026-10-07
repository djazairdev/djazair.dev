#!/usr/bin/env bash
# Called by .github/workflows/links.yml when a step fails. Opens a "Broken links" issue with
# the links that broke, or comments on the one already open (alert.sh); the next check that
# passes closes it.
#
# Environment: GH_TOKEN, ALERT_ASSIGNEES, GITHUB_*, RUNNER_TEMP.
set -euo pipefail

run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
body="${RUNNER_TEMP}/issue.md"
{
  echo "The link check failed in [run ${GITHUB_RUN_ID}](${run_url}) on $(date -u '+%Y-%m-%d %H:%M UTC')."
  echo "Fix or remove each link in \`content/localisation.json\` and update \`checked\`. This issue closes itself after the next check that passes."
  echo
  if [ -s "${RUNNER_TEMP}/failure-notes.md" ]; then cat "${RUNNER_TEMP}/failure-notes.md"; echo; fi
  if [ -s "${RUNNER_TEMP}/links.md" ]; then
    cat "${RUNNER_TEMP}/links.md"
  else
    echo "See the run log for the failing step."
  fi
} > "$body"

"$(dirname "$0")/alert.sh" open 'Broken links' 'area: content' "$body"
