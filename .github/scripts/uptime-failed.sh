#!/usr/bin/env bash
# Called by .github/workflows/uptime.yml when the site is down: opens a "Site down" issue, or
# comments on the one already open (alert.sh). The next check that passes closes it.
#
# Environment: GH_TOKEN, ALERT_ASSIGNEES, GITHUB_*, RUNNER_TEMP.
set -euo pipefail

run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
body="${RUNNER_TEMP}/issue.md"
{
  echo "djazair.dev didn't answer the uptime check in [run ${GITHUB_RUN_ID}](${run_url}) on $(date -u '+%Y-%m-%d %H:%M UTC')."
  echo "The check runs from GitHub Actions every 30 minutes; this issue closes itself when the site answers again."
  echo
  if [ -s "${RUNNER_TEMP}/failure-notes.md" ]; then cat "${RUNNER_TEMP}/failure-notes.md"; echo; fi
  if [ -s "${RUNNER_TEMP}/uptime.md" ]; then cat "${RUNNER_TEMP}/uptime.md"; fi
} > "$body"

"$(dirname "$0")/alert.sh" open 'Site down' 'area: infra' "$body"
