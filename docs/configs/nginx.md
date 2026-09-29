# NGINX 1.29 (open source) - config walkthrough

Stack: `stacks/nginx/` - image `nginx:1.29-otel` (ships the njs, OpenTelemetry and ACME dynamic modules), plus a
`nginx/nginx-prometheus-exporter` sidecar on :9100. Config file: `nginx.conf` (mounted as the directory
`/etc/nginx/lab`, started with `nginx -c /etc/nginx/lab/nginx.conf`).

Read this next to `stacks/nginx/nginx.conf`; every heading maps to a section of the file and to the probe ids in
`harness/pxlab/probes.py`.

## Process model and modules

```nginx
load_module modules/ngx_http_js_module.so;      # njs - JWT (auth_jwt is Plus-only)
load_module modules/ngx_otel_module.so;         # OpenTelemetry -> Jaeger
load_module modules/ngx_http_acme_module.so;    # native ACME client (1.29 preview)
worker_processes auto;                          # follows the cpuset (4 workers)
events { worker_connections 32768; multi_accept on; }
```

`worker_processes auto` counts the CPUs the container is allowed to use, so the cpuset in compose gives 4 workers.
`worker_rlimit_nofile` + the compose `ulimits.nofile` are needed for the c10k scenario.

## L4: the `stream {}` block

| listener | directive | probe |
|---|---|---|
| `:9000` | `proxy_pass 10.77.0.11:8080` | `tcp_l4` |
| `:9001 udp` | `proxy_pass 10.77.0.11:9002; proxy_responses 1` | `udp_l4` |
| `:8445` | `ssl_preread on; map $ssl_preread_server_name ...` | `tls_passthrough` |

`ssl_preread` reads the ClientHello without terminating TLS, so the client sees the backend's certificate
(CN=backend.lab). The `map` is where per-SNI routing would go.

## L7 basics (`http {}`)

* `resolver 127.0.0.11 valid=10s` - Docker's embedded DNS. Needed by the ACME client and by every `proxy_pass` that
  contains a variable (variables force runtime resolution; static upstreams are resolved at startup).
* `log_format json escape=json ...` + `access_log /dev/stdout json buffer=64k flush=1s` - one JSON line per request,
  read by the `access_log_json` probe through `docker logs`.
* Tracing: `otel_exporter { endpoint jaeger:4317; }`, `otel_service_name nginx`, and a **parent-based sampler** built
  with a map on `traceparent` - only requests whose incoming trace is flagged sampled (`-01`) create spans. Tracing 100 % of
  requests cost ~15 % of the proxy's CPU in the first load runs; the map keeps the load paths untraced.
* `proxy_http_version 1.1` + `proxy_set_header Connection ""` (in the snippet) are what make upstream keep-alive work
  together with `keepalive N` in the upstream blocks.
* `proxy_next_upstream error timeout; proxy_next_upstream_tries 3` - retries only on connection-level failures.
* `gzip on` (built in). Brotli/zstd need third-party modules -> `compress_brotli` / `compress_zstd` unsupported.
* `proxy_cache_path ... keys_zone=lab:16m` + `proxy_cache_lock on` (collapses concurrent misses).
* `limit_req_zone $binary_remote_addr zone=req_per_ip:10m rate=10r/s` / `limit_conn_zone` - per-client limits.
* `set_real_ip_from 10.77.0.0/24; real_ip_header proxy_protocol;` - the PROXY-protocol source address becomes
  `$remote_addr` on the :8082 listener, but only from the lab network.

### Maps: the nginx way of writing "if"

```nginx
map $http_upgrade $connection_upgrade { default upgrade; "" close; }
map $http_x_request_id $req_id { default $http_x_request_id; "" $request_id; }   # pass through or generate
map $http_x_canary $pool_by_header { default pool_app; "1" pool_canary; }         # header routing
map $arg_beta $pool_default { default $pool_by_header; "1" pool_canary; }         # query routing (chained map)
map $cookie_lab_sticky $sticky_target { default ""; "~^(?<a>10\.77\.0\.1[1-3]:8080)$" $a; }  # sticky cookie -> address
split_clients "${request_id}" $fault_503 { 20% "1"; * ""; }                       # fault injection
split_clients "${request_id}canary" $pool_canary_split { 10% pool_canary; * pool_app; }   # traffic split
```

`proxy_pass http://$pool_default` selects an upstream block by name at runtime - this is how header/query routing and the
canary split work without `if`.

### Upstream pools

```nginx
upstream pool_app { server app1:8080 max_fails=5 fail_timeout=5s; ... keepalive 64; }
upstream pool_weighted  { server app1:8080 weight=3; server app2:8080 weight=1; }
upstream pool_leastconn { least_conn; ... }
upstream pool_hash      { hash $http_x_user consistent; ... }          # ketama ring
upstream pool_retry     { server app1:8080; server app2:8080; server app3:8099; }   # dead member
upstream pool_cb        { server ... max_fails=3 fail_timeout=10s; }  # passive circuit breaker
upstream pool_grpc      { server app1:9090; keepalive 256; }
```

`max_fails=5 fail_timeout=5s` on the main pool is deliberate: with the defaults (`max_fails=1`, 10 s) one 2 s read
timeout on `/timeout` retried across all three servers marked the whole pool down ("no live upstreams") for 10 s.

## Default vhost `app.lab`

```nginx
listen 80 default_server; listen 8080 default_server;
listen 8443 ssl default_server; listen 8443 quic reuseport;   # h3
http2 on;                                                     # h2 on TLS, h2c prior-knowledge on the plain listeners
add_header Alt-Svc 'h3=":8443"; ma=86400';
```

| contract path | how |
|---|---|
| `/api/` strip prefix | `proxy_pass http://pool_app/;` (a URI part on `proxy_pass` replaces the matched prefix); `if ($request_method = DELETE) { return 405; }` |
| `~ ^/v[0-9]+/` | regex location |
| `/old/` -> `/new/` | `rewrite ^/old/(.*)$ /new/$1 break;` |
| `/redirect-me` | `return 301 /landing;` |
| `/ws` | `snippets/proxy-headers-ws.conf` sets `Upgrade` + `Connection $connection_upgrade`; `proxy_read_timeout 300s` |
| `/sse` | `proxy_buffering off; proxy_cache off;` |
| `/grpc.health.v1.Health/` | `grpc_pass grpc://pool_grpc` (h2c to the backend, `keepalive 256`) |
| `/limited` | `limit_req zone=req_per_ip burst=5 nodelay; limit_req_status 429;` |
| `/conn-limited` | `limit_conn conn_per_ip 3; limit_conn_status 429;` |
| `/allowed`, `/denied` | `allow 10.77.0.1; deny all;` / `deny 10.77.0.0/24; allow all;` |
| `/basic` | `auth_basic` + `auth_basic_user_file /auth/htpasswd` |
| `/upload` | `client_max_body_size 1m` -> 413 |
| `/timeout` | `proxy_read_timeout 2s; proxy_next_upstream off;` -> 504 |
| `/fault` | `if ($fault_503) { return 503; }` (split_clients) |
| `/bw` | `limit_rate 500k` |
| `/static/` | `alias /static/;` (served by nginx itself) |
| `/error-page` | `proxy_intercept_errors on; error_page 500 502 503 504 /_error.html;` internal location adds `X-Error-Page: custom` |
| `/cors` | `if ($request_method = OPTIONS) { add_header ...; return 204; }` |
| `/secure` | `add_header ... always` x4 |
| `/cacheable/` | `proxy_cache lab; proxy_cache_use_stale ... http_503; proxy_cache_background_update on; add_header X-Cache $upstream_cache_status` |
| `PURGE /cacheable/x` | `if ($request_method = PURGE) { return 418; } error_page 418 = @purge;` -> `@purge` loops back into nginx (`proxy_pass http://127.0.0.1:8080$uri` with `X-Refresh: 1`, which `proxy_cache_bypass $http_x_refresh` turns into a refetch that replaces the entry). Real purge = NGINX Plus `proxy_cache_purge` or the ngx_cache_purge module. |
| `/cacheable-short/` | same cache, stale-if-error via `proxy_cache_use_stale` |
| `/compressible` | `proxy_pass http://pool_app/size/65536` + global gzip |

## Other vhosts

* `a.lab` / `b.lab` - separate `server` blocks; b.lab has **its own certificate** (`ssl_certificate /certs/b.lab...`) selected by SNI.
* `redirect.lab` - `return 301 https://$host$request_uri;`.
* `weighted.lab`, `leastconn.lab`, `hash.lab`, `retry.lab` - one line each, pointing at the pools above.
* `cb.lab` - `proxy_next_upstream error timeout http_500 http_502 http_503;` so a 5xx counts as a failure for `max_fails`.
* `health.lab` - plain pool; **active health checks are NGINX Plus only** (declared unsupported).
* `sticky.lab` - the OSS pattern: `add_header Set-Cookie "lab_sticky=$upstream_addr"` on the response, and
  `if ($sticky_target != "") { set $target http://$sticky_target; } proxy_pass $target;` on the next request.
* `canary.lab` - `proxy_pass http://$pool_canary_split` (split_clients 10 %).
* `mirror.lab` - `mirror /_mirror; mirror_request_body on;` + an internal location that `proxy_pass`es to `shadow`.
* `tls.lab` - `proxy_ssl_verify on; proxy_ssl_trusted_certificate /certs/ca.crt; proxy_ssl_name backend.lab; proxy_pass https://pool_tls;`.
* `h2.lab`, `pp.lab` - fall back to plain HTTP/1.1 (`proxy_pass` cannot speak h2 or PROXY protocol; declared unsupported).
* `auth.lab` - `auth_request /_auth;` + `auth_request_set $auth_user $upstream_http_x_auth_user;` and an internal
  location that calls `app1:8080/auth` with `proxy_pass_request_body off`.
* `jwt.lab` - `auth_request /_jwt;` -> `js_content lab.jwt` (`njs/lab.js`: HS256 HMAC check with `crypto`, `exp`/`nbf`,
  returns `X-JWT-Sub` which the outer location copies with `auth_request_set $jwt_sub $sent_http_x_jwt_sub`).
* `mtls.lab` on :8444 - `ssl_client_certificate /certs/ca.crt; ssl_verify_client on;` and `X-Client-Cert-CN $ssl_client_s_dn`.
* `acme.lab` - `acme_certificate pebble; ssl_certificate $acme_certificate; ssl_certificate_key $acme_certificate_key;`
  with the issuer declared once at http level (`acme_issuer pebble { uri https://pebble:14000/dir; ssl_trusted_certificate
  /certs/pebble-ca.pem; state_path ...; accept_terms_of_service; }`). The module answers HTTP-01 on the `listen 80` of the
  same server block.
* `:8082 proxy_protocol` - accepts PROXY protocol; together with `real_ip_header proxy_protocol` the original client IP
  ends up in `X-Forwarded-For`.
* `:9101` - `stub_status` (scraped by the exporter sidecar) and `/healthz` for the compose healthcheck.

## Snippets

`snippets/proxy-headers.conf` is included in **every** proxied location because nginx does not merge `proxy_set_header`
across levels: a single `proxy_set_header` in a location discards all inherited ones. It sets Host, XFF, XFP, XFH,
X-Real-IP, RFC 7239 `Forwarded`, `X-Request-ID` (`$req_id` map), `X-Lab-Proxy` and `Connection ""`, and hides
`X-Powered-By`. `proxy-headers-ws.conf` is the same with the Upgrade headers. `tls.conf` = TLS 1.2/1.3, session cache,
no tickets.

## Operations

* Reload: `nginx -c /etc/nginx/lab/nginx.conf -s reload` (SIGHUP). Under load: 0 failed timeline requests, ~50 keep-alive
  connections closed by the retiring workers (`connection error` in oha) - clients must retry idle connections.
* Metrics: exporter sidecar (`--nginx.scrape-uri=http://proxy:9101/nginx_status`) - only the stub_status counters;
  per-upstream metrics are NGINX Plus.
* Failover: `docker stop app2` under 1000 rps -> 0 errors (connect failures retried by `proxy_next_upstream`).

## Unsupported here (and why)

`lb_active_health` (Plus), `h2_upstream` (only for gRPC), `proxy_protocol_upstream` (stream only), `compress_brotli`,
`compress_zstd` (third-party modules), `docker_label_discovery` (no provider). See `lab.yaml`.

## Gotchas we hit

1. **Retries multiplied timeouts**: `/timeout` with default `proxy_next_upstream` retried the 2 s timeout on all three
   servers and `max_fails=1` took the pool down. Fix: `proxy_next_upstream off` on that location and looser `max_fails`.
2. **PURGE via subrequest** does not populate the cache when the subrequest is answered from njs; the loopback
   `proxy_pass http://127.0.0.1:8080$uri` with `X-Refresh` does.
3. **Single-file bind mount**: `sed -i nginx.conf` on the host replaces the inode and the container keeps the old file.
   The whole directory is mounted instead.
4. **h2 `Host` vs `:authority`**: nginx rejects an `h2` request whose `Host` header differs from `:authority`; the load
   generator sends h2 requests without a `Host` header.
5. **Tracing cost**: `otel_trace on` for every request took ~15 % CPU; sample parent-based.
6. **gRPC throughput** through `grpc_pass` is bounded by one upstream connection per stream (~8k rps here even with
   `keepalive 256`).
