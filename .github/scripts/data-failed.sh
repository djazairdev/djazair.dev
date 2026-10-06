#!/usr/bin/env bash
# Called by .github/workflows/data.yml when a step fails. The site only deploys after CI
# passes on main, so the live site still shows the last good data. Opens an issue with what
# went wrong, or comments on the one already open (alert.sh), so a failure is never silent and
# never repeats as a new issue every day. The next run that succeeds closes it.
#
# Environment: VALIDATION (the outcome of the publish step), GH_TOKEN, ALERT_ASSIGNEES,
# GITHUB_*, RUNNER_TEMP.
set -euo pipefail

title='Data update failed'
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
body="${RUNNER_TEMP}/issue.md"
{
  echo "The data update failed in [run ${GITHUB_RUN_ID}](${run_url}) on $(date -u '+%Y-%m-%d %H:%M UTC')."
  if [ ! -e "${RUNNER_TEMP}/merged" ]; then echo "Nothing was merged into \`main\`."; fi
  echo "The live site still shows the last good data: it only deploys after CI passes on \`main\`."
  echo
  if [ -s "${RUNNER_TEMP}/failure-notes.md" ]; then cat "${RUNNER_TEMP}/failure-notes.md"; echo; fi
  if [ "${VALIDATION:-}" = 'failure' ] && [ -s "${RUNNER_TEMP}/validation.md" ]; then
    cat "${RUNNER_TEMP}/validation.md"
  else
    echo "See the run log for the failing step."
  fi
} > "$body"

"$(dirname "$0")/alert.sh" open "$title" 'area: pipeline' "$body"
