# Methodology details

## The load-generator image (`reverse-proxies/shared/loadgen/Dockerfile`)
`debian:trixie-slim` (glibc: the oha binary needs it) with binaries copied from official images -
`fortio/fortio:latest`, `grafana/k6:latest`, `ghcr.io/hatoo/oha:latest` - plus `wrk`, `curl`, and two Go builds
(`golang:1.26-alpine` stage): **h3load** (a ~150-line HTTP/3 loader on `quic-go` - there is no packaged h3 load tool
that reports percentiles) and `grpcurl`. One image = one set of tool versions for every proxy.

The k6 WebSocket script (`shared/loadgen/k6/ws.js`) opens a socket per VU, sends N text messages, measures echo RTT as a
Trend (`ws_echo_rtt_ms`) and counts messages; run with `--summary-export` and parse the JSON (quote `p(90)` - the
parentheses are shell syntax).

## Running a tool
```
docker run --rm --name lg-<scenario> --network pxlab --cpuset-cpus 10-13,24-27 --ulimit nofile=1048576:1048576 \
  -v shared/certs:/certs:ro -v shared/loadgen/k6:/k6:ro pxlab-loadgen <command>
```
Run detached, then a sampler thread reads the generator's cgroup every second **while it runs**: the cgroup vanishes
when the container exits, so "read after" loses the data. Split stdout/stderr: fortio writes progress to stderr and JSON
to stdout; mixing them breaks the parser.

## cgroup v2 accounting (`harness/pxlab/dockerctl.py`)
Per container: `/sys/fs/cgroup/system.slice/docker-<full id>.scope/` -> `cpu.stat` (`usage_usec`), `memory.current`,
`memory.peak`, `cpuset.cpus.effective` (limit = number of listed CPUs). Snapshot before and after each scenario:
`cores = Δusage_usec / (window_s * 1e6)`, `cpu_pct_of_limit = cores / allowed_cores`, `cpu_us_per_request =
cores * 1e6 / rps`, `rps_per_core = rps / cores`. Sum the proxy's containers (proxy + sidecars), the backends and the
generator separately - the summary shows all three so a low proxy number is never mistaken for efficiency when the
backend was the wall.

## Parsing quirks
- **oha** JSON: `summary.requestsPerSec`, `summary.successRate`, `latencyPercentiles.p50/p99/p99.9`, `statusCodeDistribution`, `errorDistribution` (the messages tell you what failed: `connection closed before message completed` = reload/keep-alive drop, `connection error` = refused/reset). Use `-w` so requests in flight at the deadline are awaited instead of counted as errors. Use `--http2` with no `Host` header (nginx rejects `Host` != `:authority`); the default vhost serves the container name.
- **wrk**: text; parse `Requests/sec`, the latency distribution lines, `Non-2xx or 3xx responses` and `Socket errors`.
- **fortio** `-json -`: `ActualQPS`, `DurationHistogram.Percentiles`, `RetCodes`; `-nocatchup -uniform` for a true open loop; `-grpc -health` for gRPC health checks (`-cacert` for a private CA).
- **k6**: `--summary-export` JSON -> `metrics.ws_echo_rtt_ms.values`, `ws_messages`, `ws_sessions`.
- **h3load**: prints one JSON line (`rps`, `p50/p90/p99`, `errors`, `bytes`).

## Pitfalls seen in the lab
| symptom | cause | fix |
|---|---|---|
| every h2 request 4xx on nginx | `Host` header differs from `:authority` | drop `-H Host:` for h2 runs |
| proxy at 100 % but rps low | tracing/logging on every request (nginx OTel took ~15 %) | parent-based sampling, buffered logs |
| gRPC ~8k rps on nginx while h1 does 60k+ | `grpc_pass` opens ~one upstream connection per stream | expected; measure per proxy |
| oha reports errors at the end of a clean run | in-flight requests cut at the deadline | `-w` |
| rps drops 40 % when testing from the host | docker-proxy userland forwarding | test from inside the network |
| numbers change run to run | another container on the proxy's cpuset, or a previous stack still running | `docker ps`, `docker stats` |
| c10k: `Too many open files` in the generator | its own ulimit | `--ulimit nofile=1048576:1048576` on the generator too |
| fortio JSON parse error | stderr mixed into stdout | capture streams separately |
| ratelimit scenario shows more 2xx than the limit | burst (token bucket) semantics, per-worker counters | read the proxy's limiter model; APISIX/nginx `nodelay` vs delay |
| WebSocket run hangs on Envoy | compression/buffer filters in the upgrade path | router-only `upgrade_configs` filter chain |
| ATS: 2k rps, p90 60 ms, CPU idle | all connections hit ONE uncacheable URL: concurrent misses serialize on the cache write lock (`CACHE-OPEN-READ` 50 ms in the xdebug milestones) | `proxy.config.cache.read_while_writer_retry.delay 1` + `proxy.config.http.cache.open_read_retry_time 1` (defaults 50/10 ms), or vary the URL (`--rand-regex-url`) to measure the proxy path instead of the lock |
| Pingora: 1 MiB bodies at 140 rps, 4 cores busy | the compression module compresses `application/octet-stream` when the client sends Accept-Encoding (oha does by default) | gate compression by content type in `response_filter`; or `--disable-compression` on the client |
| nginx-family h2/h3 runs report a few hundred "http2 error" | `keepalive_requests` (10 000 here) closes the connection with GOAWAY; in-flight streams are counted as errors | expected - size the limit, or count them as reconnects |
