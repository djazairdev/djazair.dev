#!/usr/bin/env bash
# run_ci REF: start CI on REF by hand and wait for it; returns non-zero if CI fails. Pull
# requests, merges and pushes made with the workflow token start no workflow by themselves.
# Sourced by data-pr.sh and hub-publish.sh. Needs GH_TOKEN and the usual GITHUB_* variables.
set -euo pipefail

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

