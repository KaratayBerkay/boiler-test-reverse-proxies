# Step by step: testing everything in this lab

Every command below is run from this directory (`reverse-proxies/`). `uv run --project harness pxlab …` is the harness
CLI; `cd harness && uv run pxlab …` is the same thing.

## 0. What you need
- Docker Engine with Compose v2 (`docker compose version`), ~10 GB of disk for images, cgroup v2 (the harness reads
  `/sys/fs/cgroup/system.slice/docker-<id>.scope` for per-container CPU/memory) and a machine with **at least 28 CPUs
  if you want the published numbers to be comparable**: the proxy is pinned to cpus `0-3`, the backends to `4-9,18-23`,
  the load generator to `10-13,24-27` (`shared/compose.yaml`, `stacks/*/compose.yaml`, `harness/pxlab/dockerctl.py`).
  On a smaller machine edit those cpusets - everything still runs, the proxies just share cores.
- Python 3.12 and `uv` (https://docs.astral.sh/uv/).
- Free host ports 18080, 18082, 18443 (tcp+udp), 18444, 18445, 19000, 19001/udp, 19100, 19101, 19999, 16686, 4317/4318,
  18101-18108.

## 1. Install the harness (once)
```bash
uv sync --project harness
uv run --project harness pxlab --help
uv run --project harness pxlab list          # the twelve stacks, their images and how many probes each declares unsupported
uv run --project harness pxlab probes        # the 69 capability probes (id, group, what each proves)
uv run --project harness pxlab scenarios     # the 14 load scenarios
```

## 2. Pull and build the images (once)
```bash
scripts/pull-images.sh                       # every image referenced by stacks/*/compose.yaml, shared/compose.yaml and the Dockerfiles, via mirror.gcr.io
uv run --project harness pxlab build         # builds pxlab-backend + pxlab-loadgen, generates shared/certs (lab CA, app.lab, b.lab, backend, client) and extracts Pebble's CA
```
`pull-images.sh` routes Docker Hub images through Google's pull-through cache (anonymous Docker Hub allows 100 manifest
pulls per 6 h). Stacks with their own Dockerfile (caddy, openresty, varnish exporter, pingora, ats) are built on their
first `pxlab up` (Pingora compiles ~3 minutes the first time).

## 3. Start the shared backends (once per session)
```bash
uv run --project harness pxlab shared up     # app1..3, slow (100 ms), flaky, canary, shadow, b1, pebble (ACME), jaeger, static, whoami
uv run --project harness pxlab shared status
```
The backends stay up while you switch between proxy stacks. `pxlab shared down` removes them. If you regenerate the
certificates (`pxlab certs --force`) restart the backends: they load the TLS material at start.

## 4. Run one proxy end to end
```bash
uv run --project harness pxlab run nginx     # up -> capabilities -> load -> chaos -> down (5-8 min per proxy)
```
What happens, in order:

| phase | measures | typical time |
|---|---|---|
| `capabilities` | 69 probes against the contract (each returns `ok` / `fail` / `error` / `unsupported`); `lb_active_health` and `acme_auto_cert` wait for checks/issuance | 1-2 min |
| `load` | 14 scenarios, 15 s each after a 3 s warm-up, run from the `pxlab-loadgen` container on the Docker network: oha (h1/h2), wrk, h3load (QUIC), fortio (open-loop + gRPC), k6 (WebSocket); the proxy's cores/µs-per-request/memory, plus backend and loadgen cores, come from cgroup v2 | 4-5 min |
| `chaos` | fortio 1 000 rps + a 20 rps probing timeline while `pxlab-app2` is stopped at 6 s and restarted at 14 s (errors, fail window, re-admission time); then oha 64 connections for 15 s with the proxy's native reload at 5 s | 45 s |

Useful variations:
```bash
uv run --project harness pxlab run haproxy --phases capabilities --keep     # probes only, leave it running
uv run --project harness pxlab run haproxy --no-up --phases load --seconds 30 --only h1_keepalive,tls_h2
uv run --project harness pxlab run envoy --only cache_hit,cache_purge --phases capabilities --no-up --keep
uv run --project harness pxlab up kong --build                              # (re)build the image and start
uv run --project harness pxlab phase kong chaos                             # one phase against the running stack (merged into latest.json)
uv run --project harness pxlab probe kong lb_sticky_cookie                  # one probe with its details
uv run --project harness pxlab load kong --scenario c10k --seconds 20       # ad-hoc load, no result file
uv run --project harness pxlab info kong                                    # version, containers, declared unsupported list
uv run --project harness pxlab down kong
```
`pxlab up` always `--force-recreate`s the containers: compose does not recreate a container when only a mounted config
changed, and several stacks generate their config first (`pre_up` in `lab.yaml`: envoy `gen.py`, kong, apisix, ats).

## 5. Run everything
```bash
scripts/run-all.sh                                   # every stack, sequentially, ~75 min; logs in results/logs/<stack>.log
scripts/run-all.sh --phases capabilities nginx envoy # a subset
uv run --project harness pxlab report                # rebuild results/SUMMARY.md + results/summary.json
uv run --project harness python scripts/build-report.py      # rebuild docs/report.html from results/
uv run --project harness python scripts/measured-md.py       # refresh the numbers quoted by the load-testing skill
```
Sequential on purpose: only one proxy can own the published ports and two load tests would steal cores from each other.

## 6. Read the results
- `results/<stack>/latest.json` - everything: per-probe status/detail/seconds, per-scenario rps/p50/p90/p99/max/errors
  with the raw tool output, proxy/backends/loadgen CPU and memory, chaos timelines.
- `results/SUMMARY.md` - the proxies table, the 69 x 12 capability matrix, one table per load scenario, the chaos table,
  and per-proxy probe details with the declared reasons.
- `docs/findings.md` - what the numbers mean; `docs/configs/<stack>.md` - how each config implements the contract and the
  gotchas met; `docs/proxy-matrix.md` - the decision view; `docs/report.html` - interactive charts of the same data.

How to read a probe status: ✅ the probe verified the behaviour end to end; ❌ the proxy is configured for it but the probe's
threshold failed (e.g. Apache `bybusyness` behaves like round-robin, Envoy's bandwidth limiter bursts); 💥 the probe
crashed (a bug in the lab); `--` declared unsupported in `lab.yaml`, with the reason shown in the details table.

## 7. Poke at a running stack by hand
```bash
uv run --project harness pxlab up caddy
curl -s http://localhost:18080/ -H 'Host: app.lab' | jq .                          # echo: which instance, which headers arrived
curl -s http://localhost:18080/api/hello -H 'Host: weighted.lab'
curl -sk --resolve b.lab:18443:127.0.0.1 https://b.lab:18443/ -v 2>&1 | grep subject # SNI certificate
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:18080/limited -H 'Host: app.lab'   # repeat fast: 429
curl -s http://localhost:19100/metrics | head                                      # Prometheus
curl -s 'http://localhost:16686/api/services'                                      # Jaeger
docker logs pxlab-caddy --since 1m | tail -n 3                                     # JSON access log
docker run --rm --network pxlab pxlab-loadgen oha -z 10s -c 64 -H 'Host: app.lab' http://proxy:8080/small
```
Host header matters: the proxies route by it. From the host, `localhost:18080` reaches the default vhost (`app.lab`);
every other behaviour needs `-H 'Host: <name>.lab'` or `--resolve`.

## 8. Add a proxy
1. `mkdir stacks/<key>` with a `compose.yaml` (service `proxy`, `cpuset: "0-3"`, the port map from `docs/contract.md`,
   `networks.pxlab.aliases: [proxy, app.lab, a.lab, b.lab, acme.lab, redirect.lab]`, a healthcheck, mounts for
   `../../shared/certs`, `../../shared/auth`, `../../shared/static`).
2. Write the native config implementing the contract - start from the closest `docs/configs/<proxy>.md`.
3. Write `lab.yaml`: `display`, `image`, `family`, `category`, `container`, `version_cmd`, `reload_cmd` + `reload_kind`,
   `admin`, `metrics_path`, `tracing_service`, `cache_header`, `features` (`health_settle_s`, `purge`), `unsupported`
   with one honest sentence per probe, `notes`, `docs`. Optional: `pre_up` (generator), `build: true`, `containers`,
   `access_log` (file or another container).
4. `uv run pxlab run <key> --phases capabilities --keep`, then `pxlab probe <key> <id>` for every ❌ until the matrix is
   green or declared; then the full run; then `pxlab report`.

## 9. Troubleshooting
| symptom | cause / fix |
|---|---|
| `pxlab up` hangs at "waiting for healthy" | `docker logs pxlab-<stack>`; most images have no curl - healthchecks use bash `/dev/tcp` or the proxy's own CLI |
| a config edit is not picked up | single-file bind mounts keep the old inode after `sed -i`/editor saves: mount the directory (every stack does) and `pxlab up` again (force-recreate) |
| `tls_upstream` returns 502 "unable to verify" | certificates were regenerated: restart the shared backends |
| ACME probes fail | Pebble must be reachable on `https://pebble:14000/dir` and the proxy must trust `shared/certs/pebble-ca.pem`; HTTP-01 arrives on the proxy's port 80 |
| `lb_active_health` fails | the pool needs active checks with an interval <= 2 s; the probe waits up to 20 s (`health_settle_s`) |
| `no live upstreams` cascades (nginx family) | one slow request retried on every server with `max_fails=1` takes the pool down: `proxy_next_upstream off` on the slow route, looser `max_fails` |
| load numbers look low | check `docker stats`: other containers on cpus 0-3 (an old stack still running, `docker ps`), or the host is throttled |
| Docker Hub `toomanyrequests` | `scripts/pull-images.sh` (mirror.gcr.io) |
| ports already allocated | another proxy stack is still up: `docker ps --filter name=pxlab-` then `pxlab down <stack>` |
