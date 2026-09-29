# Apache Traffic Server 9.2 - config walkthrough

Stack: `stacks/ats/` - custom image `pxlab-ats:latest` (Ubuntu 24.04 packages `trafficserver` +
`trafficserver-experimental-plugins`; there is no official ATS image). Runs `traffic_manager --nosyslog` so that
`traffic_ctl` (reload, metrics) works. ATS is a CDN-grade **caching** proxy; the reverse-proxy side is a set of files:

| file | purpose |
|---|---|
| `records.config` | global settings (9.x format; 10.x uses `records.yaml`) |
| `remap.spec` -> `gen.py` -> `remap.config` | the routing table (from-URL -> to-URL + plugin params) |
| `strategies.yaml` | NextHop strategies = load-balancing pools referenced by `@strategy=` |
| `sni.yaml` | per-SNI TLS behaviour (mTLS, blind tunnel) |
| `ssl_multicert.config` | certificates (SNI by SAN) |
| `plugin.config` | global plugins |
| `compress.config`, `hdr/*.conf`, `logging.yaml`, `storage.config`, `ip_allow.yaml` | plugin / log / cache settings |

Read this next to those files.

## `records.config`

```
proxy.config.http.server_ports STRING 80 8080 8082:pp 8443:ssl 8444:ssl 8445:ssl   # pp = PROXY protocol accepted
proxy.config.exec_thread.autoconfig INT 0 / exec_thread.limit INT 4                # 4 worker threads
proxy.config.reverse_proxy.enabled INT 1 / url_remap.remap_required INT 1          # only remapped requests are served
proxy.config.url_remap.pristine_host_hdr INT 1                                     # origin sees the client's Host
proxy.config.http.insert_squid_x_forwarded_for INT 1
proxy.config.http.proxy_protocol_allowlist STRING 10.77.0.0/24,127.0.0.1
proxy.config.http.connect_attempts_timeout INT 3 / connect_attempts_rr_retries INT 2   # retry next host on connect failure
proxy.config.http.parent_proxy.retry_time INT 5                                    # strategies mark a failed host down for 300 s by default
proxy.config.http.server_session_sharing.pool STRING thread / .match STRING both   # origin keep-alive pool
proxy.config.http.cache.http INT 1, cache.required_headers INT 2, ram_cache.size 256 MiB, negative_revalidating
proxy.config.cache.read_while_writer_retry.delay INT 1 + http.cache.open_read_retry_time INT 1   # readers of an in-flight URL poll every ms, not 50/10 ms (gotcha 8)
proxy.config.ssl.server.multicert.filename STRING ssl_multicert.config, TLS 1.2/1.3 only, http2.max_concurrent_streams_in 256
proxy.config.ssl.client.verify.server.policy STRING ENFORCED + client.CA.cert.filename ca.crt   # verify origins (tls.lab)
proxy.config.ssl.client.sni_policy STRING remap                                    # SNI = remap target host, not client Host
proxy.config.http.connect_ports STRING 443 563 8443                                # CONNECT/tunnel allowed to 8443
logging_enabled 3, diags/error logs to stderr
```

## `remap.spec` and the generator

ATS compares the request URL - scheme, host **and port** taken from the `Host` header (else the listening port) -
with the from-URL of each `map` rule, and takes the **first match in file order**. `gen.py` therefore expands every
spec line into `http://host/`, `http://host:8080/`, `http://host:18080/` (and the https variants for 8443/18443; plus
8444/18444 for mtls.lab), sorts rules longest-path first, adds `ws://`/`wss://` rules (WebSocket requests are
remapped with the ws scheme) and `localhost`/`proxy` catch-alls. Edit `remap.spec`, not `remap.config`.

| spec line | what it demonstrates |
|---|---|
| `a.lab / http://app1:8080/ @strategy=app @plugin=header_rewrite.so @pparam=.../route-a.conf` | host route + NextHop pool + per-remap header_rewrite (`X-Route: a`) |
| `weighted.lab ... @strategy=weighted`, `retry.lab ... @strategy=retry`, `cb.lab ... @strategy=cb`, `canary.lab ... @strategy=canary` | pools from `strategies.yaml` |
| `mirror.lab ... @plugin=multiplexer.so @pparam=shadow:8080` + `shadow / http://shadow:8080/ @mirror-target` | request mirroring (the copies arrive with `Host: shadow:8080`, hence the extra rule) |
| `tls.lab / https://app1:8443/` | TLS to the origin, verified (`sni_policy remap` -> SNI app1) |
| `app.lab /api/ http://app1:8080/ ... api.conf` | prefix strip (to-URL path replaces the from path); `api.conf` also answers `DELETE` with `set-status 405` |
| `app.lab /old/ http://app1:8080/new/` | rewrite by remap |
| `app.lab /limited ... @plugin=rate_limit.so @pparam=--limit=3 --queue=0 --error=429` | `rate_limit.so` caps **concurrency** per remap (declared unsupported for per-client rps) |
| `app.lab /conn-limited ... rate_limit.so --limit=3` | concurrency limit -> 429 |
| `/allowed`, `/denied`, `/basic`, `/upload`, `/fault`, `/cors`, `/secure` | `header_rewrite.so` per-remap files (`hdr/*.conf`, see below) |
| `app.lab /timeout http://app1:8080/delay/5000 @plugin=conf_remap.so @pparam=proxy.config.http.transaction_no_activity_timeout_out=2 ...` | per-remap records override (2 s read timeout, no retries) |
| `app.lab /static/index.html http://app1:8080/ @plugin=statichit.so @pparam=--file-path=/static/index.html --mime-type=text/html --disable-exact` | a file served by ATS (statichit needs the remapped path to be empty -> to-URL `/` + `--disable-exact`) |
| `app.lab /grpc.health.v1.Health/ http://app1:9090/...` | present but unsupported (no h2 to origins) |
| `app.lab / http://app1:8080/ @strategy=app @plugin=header_rewrite.so @pparam=.../app-root.conf` | the default route (versioned marker; the header/query `set-destination` in it is overridden by the strategy -> `route_header`/`route_query` unsupported) |
| `redirect.lab / https://redirect.lab/ @redirect` | `redirect` rule (http -> https 301) |
| `app.lab /redirect-me ... redirect.conf` | `set-redirect 301 "http://app.lab/landing"` in `REMAP_PSEUDO_HOOK` |

## `strategies.yaml` (NextHop)

Hosts are declared once with `health_check_url`, grouped with weights, and each strategy picks a `policy`:
`app`/`retry`/`cb` use `rr_strict` with `failover { max_simple_retries, ring_mode: exhaust_ring, response_codes:
[502,503,504], health_check: [passive] }` (`cb` adds `markdown_codes`, which did not take the flaky host out of rotation
in 9.2.3 -> `lb_outlier_ejection` unsupported); `weighted` and `canary` use `consistent_hash` with `hash_key: url` -
weights only apply to consistent hashing in ATS 9, so weighted round-robin / canary splits are declared unsupported
(same URL -> same host).

## `header_rewrite` files

Global instance (`plugin.config`: `header_rewrite.so hdr/global.conf`) hooks `READ_REQUEST_HDR_HOOK` (adds
`X-Lab-Proxy`, `X-Real-IP %{IP:CLIENT}`, `X-Forwarded-Proto %{CLIENT-URL:SCHEME}`, `X-Forwarded-Host`, RFC 7239
`Forwarded`, `X-Request-ID %{ID:UNIQUE}` when absent), `READ_RESPONSE_HDR_HOOK` (`rm-header X-Powered-By`) and
`SEND_RESPONSE_HDR_HOOK` (`set-header X-Cache %{CACHE}`). Per-remap files run in `REMAP_PSEUDO_HOOK`:

| file | rule |
|---|---|
| `api.conf` | `cond %{METHOD} =DELETE` -> `set-status 405`; `set-header X-Route "api"` |
| `allowed.conf` / `denied.conf` | `cond %{IP:CLIENT} ="10.77.0.1" [NOT]` / `cond %{IP:CLIENT} /^10\.77\.0\./` -> `set-status 403` |
| `basic.conf` | `cond %{CLIENT-HEADER:Authorization} ="Basic bGFiOmxhYi1wYXNz" [NOT]` -> 401 + `WWW-Authenticate` |
| `upload.conf` | `cond %{CLIENT-HEADER:Content-Length} >1048576` -> 413 |
| `fault.conf` | `cond %{RANDOM:100} <20` -> 503 |
| `cors.conf` | OPTIONS -> 204; response hook adds the `Access-Control-*` headers |
| `secure.conf` | response hook adds HSTS / nosniff / DENY / referrer-policy |
| `app-root.conf` | `cond %{CLIENT-URL:PATH} /^v[0-9]+\//` -> `X-Route: versioned` |
| `mtls.conf` | placeholder; the client certificate subject comes from `sslheaders.so` (`X-Client-Cert-Subject=client.subject`) |

## TLS

`ssl_multicert.config`: `dest_ip=* ssl_cert_name=app.lab.fullchain.crt ...` (default) and `b.lab` (SNI by SAN).
`sni.yaml`: `mtls.lab` -> `verify_client: STRICT` (client CA = the global `proxy.config.ssl.CA.cert.filename`; a
per-fqdn `verify_client_ca_certs` broke the handshake in 9.2.3); `passthrough.lab` -> `tunnel_route: app1:8443` (a blind
TLS tunnel, the only L4 feature).

## Other plugins

`compress.so compress.config` (gzip; the Ubuntu build has no brotli), `stats_over_http.so` (`/_stats` JSON - the
compose healthcheck and admin probe use it; no Prometheus format), `xdebug.so --header=X-Debug` (`X-Cache` diagnostics
on demand), `sslheaders.so` (client cert subject/issuer into headers), `logging.yaml` (JSON format with `%<cqtq>`,
`%<chi>`, `%<cqhm>`, `%<cqup>`, `%<{Host}cqh>`, `%<pssc>`, `%<pscl>`, `%<ttms>`, `%<crc>`, `%<shn>` to
`/var/log/trafficserver/access.log`).

## Operations

Reload: `traffic_ctl config reload` (remap/records/plugins re-read; log config changes need a restart). Metrics:
`traffic_ctl metric get proxy.process.http.current_active_client_connections`.

## Unsupported here (and why)

27 probes - see `lab.yaml`. The big ones: no active health checks or least-conn/weighted-RR/cookie stickiness in
9.x strategies, no header/query routing (remap has no conditions and the strategy overrides `set-destination`), no h2
to origins (so no gRPC), no h2c, no HTTP/3 in the Ubuntu build, no ACME client, no JWT, `authproxy.so` forwards the
original path (does not fit the contract), origin error bodies pass through, `fq_pacing.so` needs the fq qdisc, no
Prometheus exporter, no OpenTelemetry.

## Gotchas we hit

1. `@strategy='app'` - the quotes become part of the name; write `@strategy=app`.
2. `sslheaders.so` as a remap plugin parses its params as URLs -> global plugin.
3. `header_rewrite` global hooks must be `READ_REQUEST_HDR_HOOK` etc.; `%{PATH}` does not exist (`%{CLIENT-URL:PATH}`).
4. `%<pqsn>` is not a valid log field in 9.2 -> `%<{Host}cqh>`; `logging.yaml` changes need a restart.
5. Remap = first match in file order -> generator sorts longest path first; duplicate `:80` rules are rejected.
6. `set-redirect` must run in `REMAP_PSEUDO_HOOK`; WebSocket needs `ws://` from-URLs; statichit needs an empty
   remapped path.
7. Origin TLS: `sni_policy remap` + `connect_ports 8443`; the client's Host would otherwise be used as SNI.
8. **Concurrent requests for one uncacheable URL serialize on the cache write lock**: the first transaction holds the
   lock while it fetches, every other one retries every 10 ms - `/small` with 64 connections ran at 2 000 rps with a
   60 ms p90 (xdebug milestones showed `CACHE-OPEN-READ` taking 50-60 ms) while distinct URLs ran at 29 000 rps.
   Readers of a key that is being written wait `proxy.config.cache.read_while_writer_retry.delay` (**50 ms** default)
   and then `open_read_retry_time` (10 ms) before looking again. Setting both to 1 ms gives 28 000 rps on the same URL
   with every cache probe still passing. (`max_open_write_retries 0` + `open_write_fail_action 0` also gives 29 000 rps
   but then a sequential miss -> hit no longer works: the second request arrives while the writer is still finishing.)
   It is not a benchmark artefact: a hot dynamic URL behaves the same in production.
