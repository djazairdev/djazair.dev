#!/usr/bin/env bash
# Called by .github/workflows/hub.yml when a step fails. Nothing was saved, so the site keeps
# the last snapshot from the hub-data branch. Opens a "Hub sync failed" issue with what went
# wrong, or comments on the one already open (alert.sh); the next sync that succeeds closes it.
#
# Environment: GH_TOKEN, ALERT_ASSIGNEES, GITHUB_*, RUNNER_TEMP.
set -euo pipefail

run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
body="${RUNNER_TEMP}/issue.md"
{
  echo "The Hub sync failed in [run ${GITHUB_RUN_ID}](${run_url}) on $(date -u '+%Y-%m-%d %H:%M UTC')."
  echo "Nothing was saved: the site keeps the last snapshot from the \`hub-data\` branch. This issue closes itself after the next sync that works."
  echo
  if [ -s "${RUNNER_TEMP}/failure-notes.md" ]; then cat "${RUNNER_TEMP}/failure-notes.md"; echo; fi
  if [ -s "${RUNNER_TEMP}/hub-sync-errors.txt" ]; then
    echo '```'
    tail -n 20 "${RUNNER_TEMP}/hub-sync-errors.txt"
    echo '```'
  else
    echo "See the run log for the failing step."
  fi
} > "$body"

"$(dirname "$0")/alert.sh" open 'Hub sync failed' 'area: hub' "$body"
