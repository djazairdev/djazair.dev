#!/usr/bin/env bash
# One open issue per problem (ticket #32), for the scheduled workflows:
#
#   alert.sh open TITLE LABEL BODY_FILE   opens an issue titled TITLE, or comments on the open
#                                         one with that exact title, so a failure is never
#                                         silent and never repeats as a new issue;
#   alert.sh close TITLE MESSAGE          comments and closes it once the problem is gone.
#
# New issues are assigned to ALERT_ASSIGNEES (GitHub usernames, comma-separated: the founder
# and the second admin, docs/deploy.md#alerts), so GitHub notifies them.
#
# Environment: GH_TOKEN, ALERT_ASSIGNEES (optional).
set -euo pipefail

open_issue() {
  gh issue list --state open --search "\"$1\" in:title" --json number,title \
    --jq "map(select(.title == \"$1\")) | .[0].number // empty"
}

case "${1:-}" in
  open)
    title="$2" label="$3" body="$4"
    existing="$(open_issue "$title")"
    if [ -n "$existing" ]; then
      gh issue comment "$existing" --body-file "$body"
    else
      args=(--title "$title" --body-file "$body" --label "$label")
      if [ -n "${ALERT_ASSIGNEES:-}" ]; then
        args+=(--assignee "$ALERT_ASSIGNEES")
      fi
      gh issue create "${args[@]}"
    fi
    ;;
  close)
    title="$2" message="$3"
    existing="$(open_issue "$title")"
    if [ -n "$existing" ]; then
      gh issue close "$existing" --comment "$message"
    fi
    ;;
  *)
    echo 'usage: alert.sh open TITLE LABEL BODY_FILE | alert.sh close TITLE MESSAGE' >&2
    exit 2
    ;;
esac
