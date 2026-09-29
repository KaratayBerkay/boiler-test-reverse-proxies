#!/usr/bin/env bash
# proxy-bench.sh - closed-loop + open-loop benchmark of a reverse proxy from a container on its Docker network.
# Usage: proxy-bench.sh <docker-network> <base-url> [host-header] [seconds] [cpuset]
#   proxy-bench.sh pxlab http://proxy:8080 app.lab 15 10-13
# Needs the pxlab-loadgen image (reverse-proxies/shared/loadgen) or any image with oha + fortio on PATH (set IMAGE=).
set -euo pipefail
NET="${1:?network}"; BASE="${2:?base url}"; HOST="${3:-}"; SECS="${4:-15}"; CPUS="${5:-}"
IMAGE="${IMAGE:-pxlab-loadgen:latest}"
HH=(); [ -n "$HOST" ] && HH=(-H "Host: $HOST")
run() { docker run --rm --network "$NET" ${CPUS:+--cpuset-cpus "$CPUS"} --ulimit nofile=1048576:1048576 "$IMAGE" "$@"; }
oha_json() { run oha --no-tui --output-format json -w "${HH[@]}" "$@" 2>/dev/null; }
summ() { python3 -c '
import json,sys; d=json.load(sys.stdin); s=d["summary"]; p=d["latencyPercentiles"]
print(f"{s[\"requestsPerSec\"]:>10,.0f} rps  p50 {p[\"p50\"]*1000:6.2f} ms  p99 {p[\"p99\"]*1000:7.2f} ms  max {s[\"slowest\"]*1000:7.1f} ms  success {s[\"successRate\"]*100:5.1f}%")'; }
echo "warm-up 3 s"; oha_json -z 3s -c 64 "$BASE/small" >/dev/null || true
printf "%-26s" "h1 keep-alive c64:";      oha_json -z "${SECS}s" -c 64 "$BASE/small" | summ
printf "%-26s" "h1 no-keep-alive c64:";   oha_json -z "${SECS}s" -c 64 --disable-keepalive "$BASE/small" | summ
printf "%-26s" "1 MiB bodies c32:";        oha_json -z "${SECS}s" -c 32 "$BASE/bin/1048576" | python3 -c '
import json,sys; d=json.load(sys.stdin); s=d["summary"]; print(f"{s[\"sizePerSec\"]/1048576:>10,.1f} MB/s  {s[\"requestsPerSec\"]:,.0f} rps")'
if [[ "$BASE" == https://* ]]; then
  printf "%-26s" "TLS h2 16x8:"; run oha --no-tui --output-format json -w --http2 --insecure -z "${SECS}s" -c 16 -p 8 "$BASE/small" 2>/dev/null | summ
fi
printf "%-26s" "open loop 5000 rps c64:"; run fortio load -qps 5000 -c 64 -t "${SECS}s" -nocatchup -uniform "${HH[@]}" -json - -p 50,90,99,99.9 "$BASE/small" 2>/dev/null \
  | python3 -c '
import json,sys; d=json.load(sys.stdin); pc={p["Percentile"]:p["Value"]*1000 for p in d["DurationHistogram"]["Percentiles"]}
print(f"{d[\"ActualQPS\"]:>10,.0f} rps  p50 {pc[50]:6.2f} ms  p99 {pc[99]:7.2f} ms  codes {d.get(\"RetCodes\")}")'
echo "proxy CPU: read /sys/fs/cgroup/system.slice/docker-<id>.scope/cpu.stat before/after (usage_usec delta / seconds / 1e6 = cores)"
