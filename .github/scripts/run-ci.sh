#!/usr/bin/env bash
# run_ci REF: start CI on REF by hand and wait for it; returns non-zero if CI fails. Pull
# requests, merges and pushes made with the workflow token start no workflow by themselves.
# Sourced by data-pr.sh and hub-publish.sh. Needs GH_TOKEN and the usual GITHUB_* variables.
#
# run_pr_ci SHA: wait for CI on a pull request this workflow opened. GitHub holds that run for
# approval because a bot opened it, and main's required checks only count once it has run, so
# approve it (the token's actions: write allows that) and wait; returns non-zero if CI fails.
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

run_pr_ci() {
  local sha="$1" found='' id
  for _ in $(seq 1 30); do
    sleep 10
    found="$(gh run list --workflow ci.yml --commit "$sha" --event pull_request --limit 1 --json databaseId,conclusion \
               --jq '.[0] | select(.) | "\(.databaseId) \(.conclusion)"')"
    [ -n "$found" ] && break
  done
  if [ -z "$found" ]; then
    echo "CI did not start on the pull request." >&2
    return 1
  fi
  id="${found%% *}"
  if [ "${found#* }" = 'action_required' ]; then
    gh api -X POST "repos/${GITHUB_REPOSITORY}/actions/runs/${id}/approve" > /dev/null
    for _ in $(seq 1 30); do
      [ "$(gh run view "$id" --json status --jq .status)" != 'completed' ] && break
      sleep 5
    done
  fi
  echo "CI on the pull request: ${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${id}"
  gh run watch "$id" --exit-status --interval 20 > /dev/null
}
