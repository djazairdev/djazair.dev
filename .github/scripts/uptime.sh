#!/usr/bin/env bash
# Called by .github/workflows/uptime.yml: checks that each address in UPTIME_URLS
# (space-separated; default the home page) answers 200 with "djazair" in the page. An address
# gets three tries, 30 seconds apart, before it counts as down. Writes what it found to
# $RUNNER_TEMP/uptime.md and fails if anything is down.
#
# Environment: UPTIME_URLS, RUNNER_TEMP.
set -euo pipefail

report="${RUNNER_TEMP}/uptime.md"
: > "$report"
down=0
for url in ${UPTIME_URLS:-https://djazair.dev/}; do
  ok=0 code=''
  for attempt in 1 2 3; do
    page="$(mktemp)"
    code="$(curl -sS -L --max-time 20 -o "$page" -w '%{http_code}' -A 'djazair.dev uptime check' "$url" 2>/dev/null || true)"
    if [ "$code" = 200 ] && grep -q 'djazair' "$page"; then
      ok=1
    fi
    rm -f "$page"
    if [ "$ok" = 1 ]; then break; fi
    if [ "$attempt" -lt 3 ]; then sleep 30; fi
  done
  if [ "$ok" = 1 ]; then
    echo "- ${url}: up" >> "$report"
  else
    echo "- ${url}: **down** (HTTP ${code:-000} after 3 tries)" >> "$report"
    down=1
  fi
done
cat "$report"
exit "$down"
