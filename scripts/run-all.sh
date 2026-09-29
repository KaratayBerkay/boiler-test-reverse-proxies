#!/usr/bin/env bash
# Run the full harness (capabilities + load + chaos) for a list of stacks SEQUENTIALLY - only one proxy can own the
# published ports, and two load tests on one host would steal cores from each other. Logs -> results/logs/<stack>.log.
# Usage: scripts/run-all.sh [--phases capabilities,load,chaos] [--seconds 15] stack1 stack2 ...
#   with no stacks: every configured stack (harness/pxlab list).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PHASES="capabilities,load,chaos"; SECONDS_OPT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --phases) PHASES="$2"; shift 2 ;;
    --seconds) SECONDS_OPT="--seconds $2"; shift 2 ;;
    *) break ;;
  esac
done
mkdir -p "$ROOT/results/logs"
cd "$ROOT/harness"
STACKS=("$@")
if [ ${#STACKS[@]} -eq 0 ]; then mapfile -t STACKS < <(uv run pxlab list | awk '{print $1}'); fi
uv run pxlab shared up >/dev/null 2>&1 || true
for s in "${STACKS[@]}"; do
  echo "=== $(date +%H:%M:%S) $s ==="
  timeout 5400 uv run pxlab run "$s" --phases "$PHASES" $SECONDS_OPT > "$ROOT/results/logs/$s.log" 2>&1
  echo "exit=$? failures=$(grep -cE '❌|💥|FAILED' "$ROOT/results/logs/$s.log")"
  docker compose -f "$ROOT/stacks/$s/compose.yaml" -p "pxlab-$s" down -t 10 >/dev/null 2>&1 || true
done
uv run pxlab report >/dev/null 2>&1 && echo "report rebuilt: results/SUMMARY.md"
