# The proxy contract

Every stack under `stacks/<key>/` is a different reverse proxy configured to behave the same way, so that one set of
probes (`harness/pxlab/probes.py`), one set of load scenarios (`harness/pxlab/phases/load.py`) and one chaos phase apply
to all of them. The contract is deliberately opinionated: a hostname selects a *behaviour*, a path under the default
vhost selects a *feature*. A proxy that cannot implement something declares it in `lab.yaml` under `unsupported:` with a
one-line reason - the matrix then shows `--` (with the reason) instead of a red cross.

To add a proxy: implement this contract in its native config, write `lab.yaml`, run `uv run pxlab run <key>`.

## Network

| item | value |
|---|---|
| docker network | `pxlab` (external, `10.77.0.0/24`, gateway `10.77.0.1`) |
| proxy service | network alias `proxy` (+ `app.lab a.lab b.lab acme.lab redirect.lab`), pinned to CPUs `0-3` |
| backends | `app1 10.77.0.11`, `app2 .12`, `app3 .13`, `slow .14` (100 ms), `flaky .15`, `canary .16`, `shadow .17`, `b1 .18`, pinned to CPUs `4-9,18-23`, admin toggles on host ports `18101..18108` |
| ACME test CA | `pebble` (`10.77.0.30`, directory `https://pebble:14000/dir`, HTTP-01 on port 80, CA in `shared/certs/pebble-ca.pem`) |
| tracing sink | `jaeger` (`10.77.0.31`, OTLP gRPC 4317 / HTTP 4318, query API on host port 16686) |
| static origin | `static` (`10.77.0.33`, nginx serving `shared/static`; error page and ACME directory shim on :14001) |
| label-discovered app | `whoami` (`10.77.0.32`, Traefik labels for `whoami.lab`) |
| client IP seen by the proxy | `10.77.0.1` for probes from the host (docker-proxy / bridge gateway) |
| load generator | `pxlab-loadgen` container on the same network, pinned to CPUs `10-13,24-27` |

## Listeners (container port -> host port)

| port | host | what |
|---|---|---|
| 8080 (+80) | 18080 | HTTP/1.1, plus cleartext HTTP/2 (prior knowledge) where the proxy can; port 80 exists for ACME HTTP-01 |
| 8443 | 18443 (tcp+udp) | TLS: HTTP/1.1 + HTTP/2 via ALPN, HTTP/3 over UDP where the proxy can; certificate selected by SNI |
| 8444 | 18444 | TLS with a **required client certificate** (lab CA); `X-Client-Cert-CN` forwarded when possible |
| 8445 | 18445 | L4 TLS passthrough by SNI (`passthrough.lab` -> `app1:8443`, the client sees CN=backend.lab) |
| 8082 | 18082 | HTTP listener that **accepts PROXY protocol** from the client |
| 9000 | 19000 | L4 TCP proxy -> `app1:8080` |
| 9001/udp | 19001/udp | L4 UDP proxy -> `app1:9002` (echo) |
| 9100 | 19100 | Prometheus `/metrics` (native or exporter sidecar) |
| 9101 | 19101 | admin / stats / config API (`lab.yaml: admin`) |

## Hostnames

| host | behaviour |
|---|---|
| `app.lab` (default vhost, also `localhost`, `proxy`, anything unknown) | pool **app** = app1, app2, app3 round-robin; all path features below |
| `a.lab` | host routing -> pool app + request header `X-Route: a` |
| `b.lab` | host routing -> `b1`, served with its **own certificate** (CN=b.lab) on :8443 |
| `redirect.lab` | plain HTTP -> `301 https://redirect.lab/...` |
| `weighted.lab` | weighted round-robin app1:3, app2:1 |
| `leastconn.lab` | least-connections over app1, app2, slow |
| `hash.lab` | consistent hashing on header `X-User` (fallback client IP) |
| `sticky.lab` | cookie stickiness: first response sets `lab_sticky`, later requests land on the same backend |
| `retry.lab` | pool app1, app2 + a dead member (`app3:8099`): retries on connect failure hide it |
| `cb.lab` | pool app1, app2, flaky: passive health / outlier detection ejects flaky after a few 5xx |
| `health.lab` | pool app1..3 with **active** health checks (`GET /healthz` every 1-2 s) |
| `canary.lab` | traffic split 90 % pool app / 10 % canary |
| `mirror.lab` | pool app + every request mirrored to `shadow` |
| `pp.lab` | proxy sends PROXY protocol v2 to `app1:8081` |
| `h2.lab` | proxy talks HTTP/2 (h2c) to `app1:8080` |
| `tls.lab` | proxy re-encrypts to `app1:8443` and verifies it against the lab CA (SNI backend.lab) |
| `auth.lab` | forward auth: `GET app1:8080/auth` first (`X-Auth-Token: lab-secret` -> 200 + `X-Auth-User`) |
| `jwt.lab` | HS256 JWT required (`Authorization: Bearer`, secret in `shared/auth/jwt.secret`) |
| `acme.lab` | certificate obtained automatically from Pebble (:8443) |
| `mtls.lab` | on :8444 |
| `passthrough.lab` | on :8445 |
| `whoami.lab` | discovered from Docker labels (Traefik) |

## Paths under the default vhost

| path | feature |
|---|---|
| `/` | echo (pool app) |
| `/api/<x>` | prefix route, **strips** `/api` (upstream sees `/<x>`), `X-Route: api`; `DELETE /api/*` -> 405 from the proxy |
| `/v<n>/<x>` | regex route `^/v[0-9]+/`, `X-Route: versioned` |
| `/old/<x>` | rewrite -> `/new/<x>`, `X-Route: rewritten` |
| `/redirect-me` | `301 /landing` issued by the proxy |
| `?beta=1` / `X-Canary: 1` | query / header routing -> canary |
| `/ws` | WebSocket echo |
| `/sse` | server-sent events (must not be buffered) |
| `/grpc.health.v1.Health/*` | gRPC -> `app1:9090` (h2c) |
| `/limited` | rate limit 10 r/s (burst 5) per client -> 429/503 |
| `/conn-limited` | max 3 concurrent connections per client (upstream `/delay/1000`) |
| `/allowed` / `/denied` | IP allow (only 10.77.0.1) / deny (10.77.0.0/24 -> 403) |
| `/basic` | basic auth `lab:lab-pass` (`shared/auth/htpasswd*`) |
| `/upload` | request body > 1 MiB -> 413 |
| `/timeout` | upstream `/delay/5000` with a 2 s read timeout -> 5xx after ~2 s |
| `/fault` | fault injection: ~20 % immediate 503 |
| `/bw` | bandwidth limit 500 KB/s on `/bin/1048576` |
| `/static/index.html` | served from the proxy itself (`shared/static`) |
| `/error-page` | upstream `/status/503` replaced by the proxy's custom page (`X-Error-Page: custom`) |
| `/cors` | preflight answered by the proxy (`Access-Control-Allow-Origin`) |
| `/secure` | HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` added |
| `/cacheable/*` | response cache (origin sends `max-age=60`), `PURGE` invalidates |
| `/cacheable-short/*` | `max-age=2` + serve stale when the origin returns 503 |
| `/compressible` | 64 KiB text: gzip / brotli / zstd by `Accept-Encoding` |
| `/small`, `/bin/<n>`, `/delay/<ms>`, `/status/<code>` | load-test targets (pass-through to the backend) |

## Headers every upstream should see

`X-Forwarded-For` (client IP appended), `X-Forwarded-Proto`, `X-Forwarded-Host`, `X-Real-IP`, RFC 7239 `Forwarded`,
`X-Request-ID` (generated when absent), `X-Lab-Proxy: <name>`. Responses lose `X-Powered-By`.

## What the backend offers (shared/backend)

`/` echo JSON (instance, pool, listener, proto, tls, proxy_protocol, headers...), `/healthz` (toggle with
`/admin/health?state=up|down`), `/admin/fail?rate=`, `/admin/delay?ms=`, `/admin/stats`, `/admin/reset`, `/delay/<ms>`,
`/status/<code>`, `/size/<n>` (text), `/bin/<n>` (random bytes), `/small`, `/cacheable/<k>` (max-age 60, `X-Backend-Counter`,
`X-Fail: 1` -> 503), `/cacheable-short/<k>` (max-age 2), `/upload`, `/auth`, `/ws`, `/sse`; listeners `:8080` (h1 + h2c),
`:8081` (PROXY protocol), `:8443` (TLS, h2), `:9090` (gRPC health + reflection), `:9002/udp` (echo).
