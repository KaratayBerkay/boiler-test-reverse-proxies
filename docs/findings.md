# Findings

What the numbers in [`../results/SUMMARY.md`](../results/SUMMARY.md) (and the interactive `report.html`) say, and why.
Setup: every proxy pinned to cpus 0-3 in front of the same Go backends (cpus 4-9,18-23) with the load generator on cpus
10-13,24-27 of one 28-core host; 15 s per scenario after a 3 s warm-up; CPU and memory from cgroup v2 per container.
Run of 2026-09-13/14 with the configs in `stacks/` (a few stacks were re-run after fixes noted below).

## 1. Capabilities: 69 probes x 12 proxies

| proxy | ✅ | ❌ | declared unsupported | what is missing (short) |
|---|---:|---:|---:|---|
| Caddy 2 (xcaddy) | 64 | 0 | 5 | mirroring, per-client concurrency limit, fault injection, bandwidth limit, Docker labels |
| NGINX 1.29 | 63 | 0 | 6 | active health checks (Plus), h2 to non-gRPC upstreams, PROXY protocol to upstreams, brotli/zstd, Docker labels |
| Envoy 1.39 | 62 | 1 | 6 | per-client concurrency, ACME, cache (alpha filter), Docker labels; ❌ bandwidth limiter bursts |
| OpenResty 1.27 | 62 | 0 | 7 | active health checks (needs a Lua healthchecker), h2/PROXY upstreams, brotli/zstd, OTel, Docker labels |
| APISIX 3.15 | 62 | 0 | 7 | h2/PROXY upstreams, SNI passthrough, ACME, stale-on-error, zstd, Docker labels |
| HAProxy 3.4 | 61 | 0 | 8 | UDP, mirroring, cache purge / stale, brotli/zstd, OTel, Docker labels |
| Kong 3.9 OSS | 57 | 0 | 12 | mirroring, h2/PROXY upstreams, mTLS and forward auth (Enterprise), h3, stale-on-error, brotli/zstd, concurrency limit, bandwidth, Docker labels |
| Traefik v3 | 57 | 0 | 12 | header hashing, per-server ejection, PROXY to HTTP upstreams, cache, `Forwarded`, request id, JWT, fault, bandwidth, static files |
| Pingora 0.9 (custom) | 54 | 0 | 15 | least-conn, mirroring, PROXY protocol both ways, UDP, SNI passthrough, h3, ACME, purge, stale, brotli, forward auth, bandwidth, OTel, Docker labels |
| Varnish 8 + hitch | 54 | 0 | 15 | least-conn, mirroring, h2 upstreams, L4, h3, gRPC, ACME, concurrency/bandwidth limits, brotli/zstd, OTel, Docker labels |
| Apache httpd 2.4 | 53 | 1 | 15 | header hashing, mirroring, PROXY to upstreams, L4, h3, purge, zstd, rate/concurrency limits, JWT, forward auth, OTel, Docker labels; ❌ `bybusyness` ≈ round-robin |
| Apache Traffic Server 9.2 | 42 | 0 | 27 | see `docs/configs/ats.md` - 9.x load balancing (no active checks, no weighted RR / least-conn / header hash / cookies), no h2c/h3/gRPC, no ACME/JWT/forward auth, no Prometheus/OTel |

Only Traefik discovers routes from Docker labels. ACME is built into 7 of 12 (nginx, HAProxy, Caddy, Traefik, Apache
mod_md, OpenResty lua-resty-acme, Kong). HTTP/3 in 7 (nginx, HAProxy, Caddy, Traefik, Envoy, OpenResty, APISIX). UDP
proxying in 7 (nginx, Caddy, Traefik, Envoy, OpenResty, Kong, APISIX). A working response cache with purge in 7 (Caddy,
Varnish, OpenResty, Kong, APISIX, ATS; nginx OSS can only refresh). The "unsupported" column is the honest part of the
matrix: every entry names the missing edition/module (`stacks/<key>/lab.yaml`).

The two ❌ are real: Apache's `lbmethod=bybusyness` sent the 100 ms `slow` backend a full third of the traffic (fast
backends are never "busy" long enough to matter), and Envoy's `bandwidth_limit` filter lets ~1 s of burst through before
throttling, so a 1 MiB body at "500 KB/s" finished in 1.1 s.

## 2. Throughput: plain HTTP/1.1, 64 keep-alive connections (`/small`, 117-byte JSON)

| proxy | req/s | proxy µs/req | p50 ms | p99 ms |
|---|---:|---:|---:|---:|
| NGINX | **66 841** | 60 | 0.50 | 5.7 |
| OpenResty | 52 081 | 77 | 1.17 | 2.1 |
| HAProxy | 31 887 | 125 | 1.98 | 3.1 |
| ATS | 27 938 | 135 | 2.12 | 4.5 |
| Pingora | 25 376 | 155 | 2.49 | 4.1 |
| Envoy | 18 582 | 215 | 3.43 | 5.9 |
| Apache | 12 858 | 306 | 4.59 | 11.7 |
| Traefik | 12 396 | 313 | 4.38 | 15.4 |
| Caddy | 11 299 | 345 | 4.70 | 18.1 |
| Varnish | 10 773 | 367 | 5.05 | 19.1 |
| APISIX | 10 546 | 352 | 5.82 | 19.0 |
| Kong | 10 394 | 385 | 5.35 | 16.8 |

Every proxy ran at ~4.0 cores, so this is a pure CPU-per-request ranking. Three tiers: the nginx core (60-77 µs),
the C/C++/Rust event loops (HAProxy, ATS, Pingora, Envoy: 125-215 µs), and the Go proxies and Lua gateways
(300-385 µs). wrk agrees within 5 % (nginx 68 018, HAProxy 35 051, ATS 31 729).

Kong and APISIX pay ~5x nginx per request for the plugin pipeline (both are OpenResty underneath: OpenResty alone with
Lua limiters does 52 081). Varnish's 367 µs includes creating a hit-for-miss object for every uncacheable response,
gzip decisions and the `varnishncsa` sidecar reading shared memory.

**No keep-alive** (new connection per request) is a different race: HAProxy 21 763 rps at 4 cores, nginx 13 385 at
1.8 cores (the generator's connection churn, not nginx, was the limit), everyone else 3.6-6.3k. Accept + close cost
2-4x the request itself; keep-alive to clients and to upstreams is the first optimisation everywhere.

## 3. TLS, HTTP/2, HTTP/3

| proxy | TLS h1 req/s | TLS h2 req/s (16x8) | h3 req/s (16x8) | h3 µs/req |
|---|---:|---:|---:|---:|
| NGINX | 48 844 | 59 485 | **66 414** | 58 |
| OpenResty | 34 143 | 44 219 | 57 012 | 67 |
| HAProxy | 27 703 | 27 945 | 30 221 | 126 |
| ATS | 21 403 | 24 182 | - | - |
| Pingora | 15 417 | 21 474 | - | - |
| Envoy | 17 336 | 21 090 | 10 252 | 389 |
| Traefik | 11 642 | 9 857 | 10 164 | 385 |
| Caddy | 11 037 | 9 113 | 9 456 | 412 |
| APISIX | 10 158 | 10 878 | 9 083 | 435 |
| Kong | 8 770 | 9 212 | - | - |
| Apache | 11 616 | 7 010 | - | - |
| Varnish + hitch | 7 525 | 5 985 | - | - |

* TLS record processing costs nginx 20 µs/req over plain HTTP (60 -> 81); HAProxy 19 µs; Traefik/Caddy ~0 (their
  plain-HTTP path is already the expensive part).
* HTTP/2 multiplexing is *cheaper* than h1 on nginx/OpenResty (fewer syscalls per request) and roughly neutral on
  HAProxy/Envoy; on the Go proxies and Apache it is slower (Apache's mod_http2 halves throughput).
* HTTP/3: nginx and HAProxy's kernel-assisted QUIC stacks run h3 at h2 cost; the Go (quic-go) and Envoy (quiche)
  implementations cost 3-4x more per request - budget cores accordingly before enabling h3 on a busy edge.
* The few hundred "http2 errors" reported for nginx/OpenResty/APISIX/Kong are GOAWAYs: `keepalive_requests`
  (10 000 here) closes h2 connections periodically and the in-flight streams count as client errors. Expected; size
  the limit for your traffic.
* Varnish's TLS numbers are hitch's: an extra process hop with PROXY-v2 between them (7.5k / 6k).

## 4. Bodies, compression, cache

* **1 MiB bodies** (32 connections): nginx 4.4 GB/s, OpenResty 4.2, ATS 3.7, Envoy 3.6, Varnish 3.6, Pingora 3.4,
  Caddy 3.0, Traefik 2.9, HAProxy 2.3, Apache 1.6, Kong 1.4, APISIX 1.0 GB/s. The copy path dominates: proxies that
  buffer per-request (Kong/APISIX Lua bodies, Apache) fall behind. Pingora's first run did 140 rps because its
  compression module gzipped the random `application/octet-stream` body at level 5 - the client (oha) advertises
  `Accept-Encoding` by default and the module compresses any `application/*` type; gating by content type fixed it.
* **gzip 64 KiB text** costs 300-450 µs/req on the fast proxies (Pingora 13 458 rps, HAProxy 12 847, Traefik/Caddy/nginx
  ~9 300, Envoy 8 832); Varnish 2 591 and ATS 5 794 spend far more per compressed response. Compressing is 5-7x the
  cost of proxying the same bytes: keep `min_length` high and levels at 4-5.
* **Cache hits** are the cheapest thing a proxy does: nginx 63 485 rps, HAProxy 56 216, OpenResty 53 032, ATS 52 600,
  Varnish 34 387, Pingora 26 860, Apache 19 537, APISIX 11 591, Kong 11 389 - and Caddy's Souin cache-handler
  **1 662 rps with a 199 ms p99** when 64 connections hit one hot key (its storage serialises concurrent hits).
  Caddy is a fine proxy and a poor cache in this configuration; use Varnish/nginx/ATS in front of it if you need one.
* ATS caveat found the hard way: concurrent requests for one URL *that is being fetched* wait on the writer
  (`read_while_writer_retry.delay` **50 ms**, then `open_read_retry_time` 10 ms). With defaults `/small` ran at 2 000
  rps and a 60 ms p90 while distinct URLs ran at 29 000 rps; both set to 1 ms gives 27 938 rps on the hot URL with
  every cache probe still green. A hot dynamic endpoint behind a default ATS behaves the same in production.

## 5. WebSocket, gRPC, open loop

* **WebSocket echo** (64 VUs, 500 messages each): 65k-105k messages/s everywhere at 30-60 µs of proxy CPU per message
  - once upgraded, a WebSocket is a byte pipe and every proxy is a good one (Apache's mod_proxy_wstunnel is the slowest).
* **gRPC** (Health/Check over TLS, 16 x 8 streams): HAProxy 20 341 and Envoy 19 294 rps; nginx 9 720 at only 1.03 cores
  and OpenResty 6 204 at 1.02 cores - `grpc_pass` funnels each stream through its own upstream connection and the
  backend, not the proxy, becomes the limit; Pingora 9 203, APISIX 9 213, Kong 7 711, Traefik 7 026, Caddy 6 947,
  Apache 6 928. For gRPC edges HAProxy/Envoy are twice as efficient as the rest.
* **Open loop at exactly 5 000 rps** (latency without coordinated omission): nginx and OpenResty p99 1.0 ms, HAProxy,
  Apache, Pingora 1.7 ms, Varnish 1.9, Envoy 3.7, Traefik/ATS 3.9, Caddy 5.2, Kong 9.4, APISIX 11.7 ms. At a
  realistic rate the fast proxies add under 2 ms to p99; the Lua gateways add 10 ms.

## 6. Rate limiting is not one thing

`/limited` = "10 requests per second per client", hammered at 200 rps for 10 s (2 000 requests):

| passed 2xx | proxies | semantics |
|---:|---|---|
| 114 | Envoy | token bucket 15 tokens, 10/s refill (per route) |
| 110 / 106 / 106 / 105 / 105 / 100 / 100 | Kong / APISIX / nginx / OpenResty / Traefik / Caddy / Pingora | leaky or token bucket with burst 5: ~10/s + the initial burst |
| **10** | HAProxy, Varnish | sliding-window *rate* counters that also count rejected requests: once the client exceeds 10/s it is locked out until it slows down |

Same config intent, an 11x difference in what a misbehaving client gets. Traefik's limiter also queued: p99 48.6 ms
versus ~1-3 ms elsewhere. Decide whether you want "smooth to 10/s" (buckets) or "punish the abuser" (HAProxy/Varnish
counters) before copying a snippet.

## 7. c10k: 10 000 idle-ish connections each holding a 500 ms request

| proxy | req/s | p99 ms | peak RSS growth per connection | notes |
|---|---:|---:|---:|---|
| NGINX | 19 008 | 861 | 41 KB | |
| HAProxy | 18 936 | 997 | 49 KB | |
| OpenResty | 18 552 | 1 014 | 20 KB | |
| Pingora | 13 670 | 1 070 | 66 KB | |
| ATS | 9 127 | 1 340 | 377 KB | per-connection buffers; 4.5 GB at 10k |
| Envoy | 8 576 | 1 856 | 151 KB | |
| Kong | 7 857 | 1 761 | 44 KB | (1 GB baseline for the DB-less LMDB map) |
| APISIX | 5 296 | 2 345 | 184 KB | max 22 s |
| Varnish | 5 025 | 21 079 | 308 KB | thread per connection: `thread_pool_max` 2 x 4 000 < 10 000 -> queueing, 21 s p99 |
| Traefik | 4 073 | 7 195 | 367 KB | 3.6 GB peak |
| Caddy | 3 761 | 6 257 | 220 KB | **5 466 x 502/503**: dials failed under the connection storm and passive health then marked every upstream down ("no upstreams available") |
| Apache | 464 | 61 412 | 29 KB | `MaxRequestWorkers 1024`: a proxied request occupies a thread, the other 9 000 connections queue behind `ListenBacklog`, 12 843 errors |

The event-loop proxies hold 10k connections for 20-70 KB each; Go proxies and ATS spend 150-370 KB. Thread-per-connection
designs (Varnish, Apache's event MPM for *in-flight* requests) need explicit sizing - `thread_pool_max`,
`MaxRequestWorkers` - or they do not survive a slowloris-shaped burst. Caddy needs `max_fails` raised (or passive health
off) before a dial storm can take the pool down.

## 8. Chaos: a backend killed under load, a reload under load

Backend `app2` stopped at 6 s and restarted at 14 s while fortio drove 1 000 rps and a 20 rps probe timeline ran:

| result | proxies |
|---|---|
| **0 errors** on 15-24k requests | nginx, OpenResty, HAProxy, Caddy, Apache, Varnish, Kong, APISIX, ATS, Envoy (after the fix below) |
| 1 error | Pingora |
| 12 x 502 | Traefik (retry middleware re-selects randomly and can hit the dead server again; no "previous hosts" predicate) |

What the first run taught: Envoy (208 x 503), Traefik (451 x 502) and Varnish (156 x 503) had retries configured only on
the demo host `retry.lab`, not on the production routes. Adding connection-level retries to the default routes fixed
Varnish; Envoy still returned 7-9 x 503 until `retry_host_predicate: previous_hosts` stopped it from retrying on the host
that had just failed. **Put retries where the traffic is, and never retry on the same host.**

Re-admission after app2 came back: Caddy 0.9 s, Traefik 0.7 s, ATS 0.4 s (after `parent_proxy.retry_time 5`; the default
300 s kept a recovered backend out for five minutes), Varnish 1.7 s, Apache 2.6 s, Pingora 3.1 s, APISIX 3.4 s, Kong 3.6 s,
Envoy 4.1 s, HAProxy 4.3 s, OpenResty 5.5 s, nginx 6.1 s (passive: `fail_timeout` 5 s + one probe). Max latency during
the stop = the connect timeout (3 s on all of them): lower it on a LAN.

Reload under 64 keep-alive connections: 0 failed timeline requests on every proxy. The SIGHUP family closes idle
keep-alive connections when the old workers retire - nginx 52, OpenResty 28, Apache 48, Pingora 37 client-side
"connection closed" errors out of ~150-950k requests - while API/file-watch reloads (Caddy, Traefik, Envoy, Kong, APISIX,
Varnish) and HAProxy's master-worker fd hand-over lost nothing. Clients behind nginx-style proxies must retry idle
connections; the proxies with a config API never make them.

## 9. Things that would have gone unnoticed without probes

* nginx: one 2 s timeout retried across a 3-member pool with `max_fails=1` took the whole pool down for 10 s.
* Kong: `kong reload` does not re-read DB-less config; `hash_on_header: X-User` silently hashes nothing (`x_user`).
* APISIX: a schema violation drops that route and nothing else fails.
* Caddy: a host-less TLS site pinned its certificate on every SNI, including the ACME-managed one.
* Envoy: health checks slow to `no_traffic_interval` (60 s) on an idle cluster; the alpha cache filter bypasses route
  behaviour for every route.
* Traefik: routers with `tls:` never match plain HTTP; HSTS only on TLS without `forceSTSHeader`.
* Apache: `LimitRequestBody` is not enforced for streamed proxy bodies; balancer URL params are not worker params.
* Pingora: lazily registered metrics were empty after a zero-downtime upgrade; the compression module compresses
  binary `application/*` bodies.
* ATS: `@strategy='app'` keeps the quotes; remap is first-match in file order and the port is part of the match.
* Everything: regenerating certificates requires restarting the backends too ("unable to verify the first certificate").

## 10. Recommendations distilled

1. Measure µs/request at saturation *and* p99 at a realistic open-loop rate; they rank the proxies differently
   (Envoy is mid-pack on the first, near the top on the second).
2. Configure retries and outlier ejection on production routes with a "not the same host" rule; keep connect timeouts
   short; re-admit with active checks.
3. Keep-alive everywhere; no-keep-alive traffic costs 2-4x per request on every proxy.
4. Compression and h3 are CPU products, not free features: size for them.
5. A cache in the proxy is the biggest throughput multiplier available (63k vs 67k rps for hits vs pass-through on
   nginx is not the point - the backend cores drop from 7.5 to 0.1).
6. Rate limiters differ in semantics more than in accuracy; test with a burst.
7. c10k-class connection counts need event-loop proxies or explicit thread sizing, and 20-370 KB per connection.
