# Load balancing and resilience - construct per proxy

Probe ids: `lb_round_robin`, `lb_weighted`, `lb_least_conn`, `lb_hash_header`, `lb_sticky_cookie`,
`lb_retry_dead_member`, `lb_outlier_ejection`, `lb_active_health`, `lb_canary_split`, `lb_mirror`,
`lb_upstream_keepalive`. Measured behaviour: `reverse-proxies/results/SUMMARY.md`.

## Pools and algorithms (`lb_round_robin`, `lb_weighted`, `lb_least_conn`)
- **nginx / OpenResty**: `upstream pool { server app1:8080 weight=3; server app2:8080; least_conn; keepalive 64; }` (round-robin default; `least_conn`; `random two least_conn` for p2c).
- **HAProxy**: `backend be { balance roundrobin|leastconn|source|uri|hdr(X); server app1 app1:8080 weight 3 check maxconn 20000 }`.
- **Caddy**: `reverse_proxy a b c { lb_policy round_robin | weighted_round_robin 3 1 | least_conn | random | first | ip_hash }`.
- **Traefik**: `loadBalancer.servers: [{url, weight: 3}]`; `strategy: p2c` for a least-connections approximation (3.x); no true least-conn.
- **Envoy**: cluster `lb_policy: ROUND_ROBIN | LEAST_REQUEST | RING_HASH | MAGLEV | RANDOM`; weights via `load_balancing_weight` per endpoint.
- **Apache**: `<Proxy "balancer://x"> BalancerMember ... loadfactor=3; ProxySet lbmethod=byrequests|bytraffic|bybusyness`. `bybusyness` behaved like round-robin with fast backends (❌ in the lab).
- **Varnish**: `directors.round_robin()`, `directors.random()` with weights (`add_backend(app1, 3.0)`), `directors.shard()`, `fallback`; **no least-connections director**.
- **Kong**: `upstreams: algorithm: round-robin | least-connections | consistent-hashing | latency`, target `weight`.
- **APISIX**: `type: roundrobin | least_conn | chash | ewma`, node weights `nodes: { "app1:8080": 3 }`.
- **Pingora**: `LoadBalancer<RoundRobin>` with `Backend::new_with_weight`; ketama via `LoadBalancer<KetamaHashing>`; least-conn = custom `BackendSelection` (not in the lab).
- **ATS**: `strategies.yaml` `policy: rr_strict | rr_ip | first_live | latched | consistent_hash`; **weights only apply to `consistent_hash`** (no weighted RR in 9.x), no least-conn.

## Consistent hashing on a header (`lb_hash_header`)
- nginx: `hash $http_x_user consistent;` · HAProxy: `balance hdr(X-User)` + `hash-type consistent` · Caddy: `lb_policy header X-User` · Traefik: **unsupported** (wrr/p2c/sticky only) · Envoy: `RING_HASH` cluster + route `hash_policy: [{ header: { header_name: X-User } }, { connection_properties: { source_ip: true } }]` · Apache: **unsupported** · Varnish: `hash.backend(by = KEY, key = hash.key(req.http.X-User))` (shard director) · Kong: `algorithm: consistent-hashing, hash_on: header, hash_on_header: x_user` (nginx spelling!), `hash_fallback: ip` · APISIX: `type: chash, hash_on: header, key: x-user` · Pingora: `hash.select(key.as_bytes(), 256)` · ATS: **unsupported** (`hash_key` is url/path/cache_key/hostname only).

## Cookie stickiness (`lb_sticky_cookie`)
- nginx OSS (`sticky` is Plus): `add_header Set-Cookie "lab_sticky=$upstream_addr"`, `map $cookie_lab_sticky $sticky_target { "~^(?<a>10\.77\.0\.1[1-3]:8080)$" $a; }`, `proxy_pass $target`.
- HAProxy: `cookie lab_sticky insert indirect nocache httponly` + `server app1 ... cookie a1`.
- Caddy: `lb_policy cookie lab_sticky`.
- Traefik: `loadBalancer.sticky.cookie: { name: lab_sticky, httpOnly: true }`.
- Envoy: `hash_policy: [{ cookie: { name: lab_sticky, ttl: 3600s, path: / } }]` on a `RING_HASH` cluster - Envoy generates the cookie.
- Apache: `ProxySet stickysession=lab_sticky` + `BalancerMember route=a1` + `Header add Set-Cookie "lab_sticky=.%{BALANCER_WORKER_ROUTE}e" env=BALANCER_ROUTE_CHANGED`.
- Varnish: `cookie.get("lab_sticky")` -> exact backend; set the cookie in `vcl_deliver` from the backend's identity header.
- Kong: `hash_on: cookie, hash_on_cookie: lab_sticky, hash_on_cookie_path: /` (Kong sets the cookie).
- APISIX: `traffic-split` rules on `cookie_lab_sticky` -> single-node upstreams + `serverless-post-function` setting `Set-Cookie`.
- Pingora: parse the cookie in `request_filter`, `Set-Cookie` in `response_filter`.
- ATS: **unsupported** (`cookie_remap` routes on cookies but never sets one).

## Retries on connect failure (`lb_retry_dead_member`)
- nginx: `proxy_next_upstream error timeout; proxy_next_upstream_tries 3` (default retries connection errors). · HAProxy: `retries 3`, `option redispatch`, `retry-on conn-failure empty-response` (`retry-on all-retryable-errors` for L7). · Caddy: `lb_retries 3  lb_try_duration 3s  lb_try_interval 50ms`. · Traefik: `retry: { attempts: 3, initialInterval: 50ms }` middleware. · Envoy: `retry_policy: { retry_on: "connect-failure,refused-stream,reset", num_retries: 3 }`. · Apache: member `retry=30` (a failed member is skipped for 30 s after the first failure). · Varnish: `vcl_backend_error { if (bereq.retries < 3) { return (retry); } }`. · Kong: service `retries: 3`. · APISIX: upstream `retries: 3`. · Pingora: `fail_to_connect` -> `e.set_retry(true)` while `tries < 3`. · ATS: `connect_attempts_rr_retries` + strategy `failover.max_simple_retries`; a host marked down stays out for `proxy.config.http.parent_proxy.retry_time` (**300 s** default - set it to seconds).

## Passive health / outlier ejection (`lb_outlier_ejection`)
- nginx: `max_fails=3 fail_timeout=10s` + `proxy_next_upstream ... http_500 http_502 http_503` (5xx counts as a failure only when listed). · HAProxy: `server ... observe layer7 error-limit 3 on-error mark-down` + `retry-on all-retryable-errors`. · Caddy: `fail_duration 10s  max_fails 3  unhealthy_status 5xx` (+ `lb_retries`). · Traefik: **unsupported** per server (`circuitBreaker` opens the whole service). · Envoy: `outlier_detection: { consecutive_5xx: 3, base_ejection_time: 10s, max_ejection_percent: 100 }`. · Apache: `ProxySet failonstatus=500,502,503` + `retry=10`. · Varnish: `saintmode.saintmode(backend, 5)` wrappers + `saintmode.denylist(10s)` in `vcl_backend_response`. · Kong: `healthchecks.passive.unhealthy: { http_statuses: [500,502,503,504], http_failures: 3 }` (+ active to re-admit). · APISIX: `checks.passive` the same way. · Pingora: hand-written counter map consulted in `select_with`. · ATS: `markdown_codes` did not eject in 9.2.3 - **unsupported**.

## Active health checks (`lb_active_health`)
- nginx OSS: **unsupported** (`health_check` is Plus) · OpenResty: **unsupported** in the lab (lua-resty-upstream-healthcheck can do it) · HAProxy: `option httpchk GET /healthz` + `http-check expect status 200` + `server ... check inter 1s fall 2 rise 2` · Caddy: `health_uri /healthz  health_interval 1s  health_passes 2  health_fails 2` · Traefik: `loadBalancer.healthCheck: { path: /healthz, interval: 1s, timeout: 1s }` · Envoy: cluster `health_checks: [{ http_health_check: { path: /healthz }, interval: 1s, unhealthy_threshold: 2, healthy_threshold: 2, no_traffic_interval: 1s }]` (without `no_traffic_interval` an idle cluster is re-checked every 60 s) · Apache: `BalancerMember ... hcmethod=GET hcuri=/healthz hcinterval=1 hcfails=2 hcpasses=2 hcexpr=ok` (mod_proxy_hcheck + mod_watchdog) · Varnish: `probe hc { .url = "/healthz"; .interval = 1s; .window = 3; .threshold = 2; }` · Kong: `healthchecks.active: { http_path: /healthz, healthy: { interval: 1, successes: 2 }, unhealthy: { interval: 1, http_failures: 2 } }` · APISIX: `checks.active` · Pingora: `HttpHealthCheck` + `health_check_frequency` on a `LoadBalancer` run as a background service · ATS 9: **unsupported** (ATS 10 adds active origin checks).

## Canary split and mirroring (`lb_canary_split`, `lb_mirror`)
- nginx: `split_clients "${request_id}canary" $pool { 10% pool_canary; * pool_app; }` + `proxy_pass http://$pool`; mirror: `mirror /_mirror; mirror_request_body on;` + internal location.
- HAProxy: split = weights (30/30/30/10) in one backend; mirror **unsupported** (SPOE / tee).
- Caddy: `lb_policy weighted_round_robin 30 30 30 10`; mirror **unsupported**.
- Traefik: `weighted.services: [{name: app, weight: 90}, {name: canary, weight: 10}]`; `mirroring: { service: app, mirrorBody: true, mirrors: [{ name: shadow, percent: 100 }] }`.
- Envoy: `weighted_clusters`; `request_mirror_policies: [{ cluster: shadow, runtime_fraction: { default_value: { numerator: 100 } } }]`.
- Apache: `loadfactor` weights; mirror **unsupported**.
- Varnish: `directors.random()` weights; mirror **unsupported**.
- Kong: target weights (30/30/30/10); mirror **unsupported** in OSS.
- APISIX: `traffic-split: { rules: [{ weighted_upstreams: [{ upstream_id: canary, weight: 10 }, { weight: 90 }] }] }`; `proxy-mirror: { host: "http://shadow:8080", sample_ratio: 1 }`.
- Pingora: weights on the RR pool; mirror = second request by hand (not in the lab).
- ATS: split **unsupported** (weights only for consistent hash); mirror: `@plugin=multiplexer.so @pparam=shadow:8080` (copies arrive with `Host: shadow:8080` - add a remap rule for it).

## Upstream keep-alive / connection pooling (`lb_upstream_keepalive`)
- nginx: `keepalive 64;` in the upstream **and** `proxy_http_version 1.1; proxy_set_header Connection "";` · HAProxy: `http-reuse always` (+ `option http-keep-alive`) · Caddy: `transport http { keepalive 90s  keepalive_idle_conns 64  max_conns_per_host N }` · Traefik: `serversTransport.maxIdleConnsPerHost: 200` · Envoy: `common_http_protocol_options: { idle_timeout: 90s }` (pooled by default) · Apache: `BalancerMember ... keepalive=On max=2000` (event MPM) · Varnish: pooled by default (`.max_connections`) · Kong: `KONG_UPSTREAM_KEEPALIVE_POOL_SIZE`, `..._MAX_REQUESTS` · APISIX: `nginx_config.http.upstream.keepalive: 320` · Pingora: `peer.options.idle_timeout` (connection pool built in) · ATS: `server_session_sharing.pool STRING thread` + `.match STRING both`.

## Timeouts per route (`timeout_upstream`)
- nginx: `proxy_read_timeout 2s` in the location (**and** `proxy_next_upstream off` or the timeout is retried on every server) · HAProxy: `http-request set-timeout server 2s if { path /timeout }` **in the backend** · Caddy: `transport http { response_header_timeout 2s }` on that `reverse_proxy` · Traefik: a second service with `serversTransport: { forwardingTimeouts: { responseHeaderTimeout: 2s } }` · Envoy: `route: { timeout: 2s }` · Apache: a dedicated worker URL with `timeout=2 retry=0` (workers are shared per URL; `balancer://` params are balancer params) · Varnish: a backend with `.first_byte_timeout = 2s` · Kong: a service with `read_timeout: 2000, retries: 0` · APISIX: an upstream with `timeout: { read: 2 }, retries: 0` · Pingora: `peer.options.read_timeout` from ctx · ATS: `@plugin=conf_remap.so @pparam=proxy.config.http.transaction_no_activity_timeout_out=2`.
