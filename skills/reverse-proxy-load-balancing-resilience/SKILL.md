---
name: reverse-proxy-load-balancing-resilience
description: Design and tune load balancing and resilience on a reverse proxy or gateway - round-robin/weighted/least-connections/consistent-hash/sticky sessions, active health checks, passive outlier ejection, retries and their blast radius, per-route timeouts, canary and weighted traffic splits, request mirroring, upstream keep-alive pools, and zero-downtime reloads - for NGINX, HAProxy, Caddy, Traefik, Envoy, Apache, Varnish, OpenResty, Kong, APISIX, Pingora and ATS, backed by measured failover and reload-under-load results. Use whenever a task involves upstream pools, backend failures, 502/504 storms, "no live upstreams", canary releases, blue/green, sticky sessions, health checks, retries, circuit breakers or graceful reloads.
---

# Load balancing and resilience

The reverse-proxies lab drove every proxy through 11 load-balancing probes and a chaos phase (a backend killed and
restarted under 1 000 rps; a config reload under 64-connection load). Construct-per-proxy tables:
`reverse-proxy-capability-mapping/references/load-balancing.md`. This page is the design guidance those runs support.

## Pick the algorithm by what varies

| backends are... | use | note |
|---|---|---|
| identical, fast | round-robin (default everywhere) | simplest, no state |
| different sizes | weighted RR (`weight=`, `loadfactor=`, `load_balancing_weight`) | not in ATS 9 (weights only on consistent hash) |
| variable latency (slow node, GC pauses) | least-connections / least-request / p2c | Apache `bybusyness` behaved like RR with fast backends; Traefik has p2c, Varnish/Pingora/ATS none |
| cache locality per user / session affinity without cookies | consistent hash on a header or IP (`hash ... consistent`, ring hash, `chash`, shard) | Traefik/Apache/ATS cannot hash on a header |
| real session affinity | cookie stickiness (proxy-issued cookie) | nginx OSS needs the map trick; Kong/Envoy/Caddy/HAProxy/Traefik issue the cookie themselves |

## Health: use both kinds, and know what each proves

- **Active checks** (`/healthz` every 1-2 s, 2 rises / 2 falls) remove a backend that *answers* but says it is
  unhealthy - the only way to drain before deploys. Missing in nginx OSS (Plus), OpenResty (needs
  lua-resty-upstream-healthcheck), ATS 9. Interval x fall count = detection time; the lab measured re-admission in
  2-6 s after the backend came back (interval x rise count).
- **Passive detection** (`max_fails`, `observe layer7`, `outlier_detection`, `failonstatus`, saintmode, passive
  healthchecks) reacts to real traffic failures; combine with retries so the request that discovered the failure still
  succeeds. Traefik's circuit breaker is per service, not per server (it cannot eject one bad node).
- Envoy: health checks slow to `no_traffic_interval` (60 s default) on idle clusters - set it to seconds or a pool that
  only sees bursts will keep a dead node for a minute.
- Backends must expose a health endpoint that reflects dependencies but never does heavy work; the lab's origin
  toggles it (`/admin/health?state=down`) so the probes could observe ejection and re-admission.

## Retries: bound them or they amplify outages

- Retry **only** connection-level failures by default (`error timeout`, `conn-failure`, `connect-failure,refused-stream,reset`).
  Retrying 5xx is safe only for idempotent methods and with a budget.
- **The cascade the lab hit** (nginx family: nginx, OpenResty, Kong, APISIX): a slow route with a 2 s read timeout,
  retried on every server, plus `max_fails=1` -> the whole pool marked down for `fail_timeout` -> "no live upstreams"
  for every client. Fixes: `proxy_next_upstream off` (or `retries: 0`) on slow routes, `max_fails` >= 3-5 with a short
  `fail_timeout`, per-route timeouts on a dedicated upstream/worker (Apache: a distinct worker URL; Kong/APISIX: a
  distinct service/upstream with `retries: 0`).
- Cap total tries (3), add `per_try_timeout` (Envoy) / `lb_try_duration` (Caddy) / `timeout connect` (HAProxy) so a dead
  member costs one connect timeout, not one per request.
- **Never retry on the host that just failed.** Envoy needs `retry_host_predicate: previous_hosts` +
  `host_selection_retry_max_attempts` (plain retries still returned 7-9 x 503 in the lab; with the predicate 0);
  HAProxy `option redispatch` and nginx `proxy_next_upstream` move on by design; Traefik's `retry` re-selects at random
  and kept 12 x 502 of 23k during an 8 s backend outage - the only residual failures in the chaos run.
- Idempotency: Envoy/HAProxy/Caddy retry POSTs only when told (`retry_on` + budgets, `retry-on`, `lb_retries`); nginx
  retries non-idempotent methods only with `non_idempotent`. Keep it that way.

## Failover under load - what the chaos phase showed
- With connection retries on the *production routes*, stopping a backend for 8 s under 1 000 rps produced **0 non-2xx**
  on 10 of 12 proxies (Pingora 1, Traefik 12); the first run had 156-451 errors on Envoy, Traefik and Varnish because
  retries were only configured on the demo host; the price was a latency spike equal to the connect timeout (3 s in the lab) on the requests
  that hit the dead member first - lower `connect_timeout` (1 s) when backends are on a LAN.
- Re-admission after the backend returned took interval x rise (0.4-6 s). Passive-only proxies re-admit after
  `fail_timeout` (nginx 5-10 s) and re-test with live traffic; ATS keeps a marked-down host out for
  `parent_proxy.retry_time` (**300 s** default) - set it to seconds.
- Stopping a container is the *easy* failure (RST immediately). A hung backend (accepts, never answers) is only
  caught by timeouts and active checks - set `proxy_read_timeout`/`timeout server`/`route.timeout` deliberately.

## Reloads - measured behaviour
| model | proxies | effect under 64-connection load |
|---|---|---|
| new workers + old drain (SIGHUP) | nginx, OpenResty, Apache graceful | 0 failed timeline requests; idle keep-alive connections closed -> clients see a few `connection closed` errors and must retry |
| master-worker fd hand-over | HAProxy (SIGUSR2) | 0 errors, connections kept |
| API / file watch | Caddy, Traefik, Envoy xDS, Kong `POST /config`, APISIX mtime, Varnish `varnishreload` | 0 errors, sockets untouched |
| socket transfer to a new process | Pingora `-u` + SIGQUIT | 0 errors when the new process is started *before* signalling the old one |
| `traffic_ctl config reload` | ATS | remap/records re-read without drops; logging config needs a restart |
Kong: `kong reload` does **not** re-read DB-less config. Traefik: editing the dynamic file *is* the reload. Envoy:
write + rename into the watched directory (inotify MOVED_TO).

## Canary, blue/green, mirroring
- Weighted split between *pools* (Traefik weighted services, Envoy weighted_clusters, APISIX traffic-split, nginx
  split_clients) beats weighted members in one pool when the canary has its own health/timeouts.
- Header/query overrides (`X-Canary: 1`, `?beta=1`) let testers hit the canary deterministically; keep them out of
  production hostnames or gate them by IP.
- Mirroring (nginx `mirror`, Traefik `mirroring`, Envoy `request_mirror_policies`, APISIX `proxy-mirror`, ATS
  multiplexer) copies requests fire-and-forget: the shadow's responses and errors are ignored, bodies are buffered
  (`mirror_request_body on`), and the shadow sees the same `Host` unless rewritten (ATS copies arrive with the target's
  host). Not available in HAProxy, Caddy, Apache, Varnish, Kong OSS, Pingora (hand-written).

## Upstream connection pools
Always enable keep-alive to upstreams (nginx `keepalive N` + `proxy_http_version 1.1` + `Connection ""`; HAProxy
`http-reuse always`; Caddy `keepalive_idle_conns`; Envoy idle_timeout; Kong/APISIX keepalive pool sizes; Apache
`keepalive=On max=N`; ATS session sharing). The lab's probe counts new TCP connections at the backends over 60 requests
(<= 12 expected); without pooling the no-keep-alive load scenario numbers apply to *every* request.
