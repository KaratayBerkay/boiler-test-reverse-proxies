# reverse-proxies — cross-proxy results

Generated 2026-09-13T21:07:03+00:00 from `results/<stack>/latest.json`. Every proxy runs on the same 4 pinned cores (cpuset 0-3) in front of the same backends (cpus 4-9) with the load generator on cpus 10-13; numbers are therefore comparable across proxies but bounded by this one host.

## Proxies

| stack | proxy | version | image | image size | startup s | capabilities ✅ | ❌ | 💥 | -- |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| apisix | Apache APISIX 3.15 | 3.15.0 | `apache/apisix:3.15.0-debian` | 559 MB | 2.8 | 62 | 0 | 0 | 7 |
| apache | Apache httpd 2.4 | Server version: Apache/2.4.68 (Unix) | `httpd:2.4` | 175 MB | 3.3 | 53 | 1 | 0 | 15 |
| ats | Apache Traffic Server 9.2 | Traffic Server 9.2.3 Feb 12 2026 02:40:38 localhost | `pxlab-ats:latest` | 235 MB | 6.1 | 42 | 0 | 0 | 27 |
| caddy | Caddy 2 | v2.11.4 h1:XKxkMTgNSizEvKG6QHue6cAsFOteU2qA61w2tKkCWi0= | `pxlab-caddy:latest` | 160 MB | 3.4 | 64 | 0 | 0 | 5 |
| envoy | Envoy 1.39 | envoy  version: b579d07d3ad7ee11d32b105e91a5a39ad24718d7/1.39.1/Clean/RELEASE/BoringSSL | `envoyproxy/envoy:v1.39-latest` | 293 MB | 2.9 | 62 | 1 | 0 | 6 |
| haproxy | HAProxy 3.4 | HAProxy version 3.4.4-7f03ae6 2026/08/27 - https://haproxy.org/ | `haproxy:lts` | 185 MB | 2.9 | 61 | 0 | 0 | 8 |
| kong | Kong Gateway 3.9 | 3.9.3 | `kong:3.9` | 528 MB | 4.4 | 57 | 0 | 0 | 12 |
| nginx | NGINX 1.29 | nginx version: nginx/1.29.8 | `nginx:1.29-otel` | 250 MB | 3.4 | 63 | 0 | 0 | 6 |
| openresty | OpenResty 1.27 | nginx version: openresty/1.27.1.2 | `pxlab-openresty:latest` | 634 MB | 3.4 | 62 | 0 | 0 | 7 |
| pingora | Pingora (Rust, custom) | pingora-lab 0.1.0 (pingora 0.9) | `pxlab-pingora:latest` | 180 MB | 3.3 | 54 | 0 | 0 | 15 |
| traefik | Traefik v3 | Version:      3.7.13 | `traefik:v3` | 252 MB | 2.9 | 57 | 0 | 0 | 12 |
| varnish | Varnish 8 + hitch | varnishd (varnish-8.0.2 revision fb46a7bb50531f1a86e17173aa64116fd98a8b86) | `varnish:8.0` | 458 MB | 4.7 | 54 | 0 | 0 | 15 |

## Capability matrix

✅ verified by the probe · ❌ configured/attempted but the probe failed · 💥 probe error · -- declared unsupported (reason in the stack's lab.yaml and docs/configs/<stack>.md)

| group | capability | Apache APISIX 3.15 | Apache httpd 2.4 | Apache Traffic Server 9.2 | Caddy 2 | Envoy 1.39 | HAProxy 3.4 | Kong Gateway 3.9 | NGINX 1.29 | OpenResty 1.27 | Pingora (Rust, custom) | Traefik v3 | Varnish 8 + hitch |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| routing | `route_host` Host-based routing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `route_path_prefix` Path prefix route + strip prefix | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `route_path_regex` Regex path route | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `route_rewrite` URL rewrite (regex capture) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `route_redirect` Redirect issued by the proxy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `route_header` Header-based routing | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `route_query` Query-parameter routing | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `route_method` Method-based rule | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| routing | `redirect_https` HTTP -> HTTPS redirect | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| load-balancing | `lb_round_robin` Round-robin over 3 backends | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| load-balancing | `lb_weighted` Weighted round-robin (3:1) | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| load-balancing | `lb_least_conn` Least-connections | ✅ | ❌ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ | -- |
| load-balancing | `lb_hash_header` Consistent hashing on a header | ✅ | -- | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| load-balancing | `lb_sticky_cookie` Cookie stickiness | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| load-balancing | `lb_retry_dead_member` Retry on connect failure | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| load-balancing | `lb_outlier_ejection` Passive health / outlier ejection | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| load-balancing | `lb_active_health` Active health checks | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | -- | -- | ✅ | ✅ | ✅ |
| load-balancing | `lb_canary_split` Weighted traffic split (canary) | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| load-balancing | `lb_mirror` Request mirroring / shadowing | ✅ | -- | ✅ | -- | ✅ | -- | -- | ✅ | ✅ | -- | ✅ | -- |
| load-balancing | `lb_upstream_keepalive` Upstream connection pooling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| protocols | `http2_tls` HTTP/2 (TLS, ALPN) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| protocols | `h2c_frontend` HTTP/2 cleartext (prior knowledge) on :8080 | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| protocols | `http3` HTTP/3 (QUIC) | ✅ | -- | -- | ✅ | ✅ | ✅ | -- | ✅ | ✅ | -- | ✅ | -- |
| protocols | `websocket` WebSocket proxying | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| protocols | `sse_streaming` Server-sent events (no response buffering) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| protocols | `grpc` gRPC proxying (h2 -> upstream h2c :9090) | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- |
| protocols | `h2_upstream` HTTP/2 to the upstream (h2c) | -- | ✅ | -- | ✅ | ✅ | ✅ | -- | -- | -- | ✅ | ✅ | -- |
| protocols | `tls_upstream` TLS re-encryption to the upstream (verified) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| protocols | `proxy_protocol_upstream` PROXY protocol v2 to the upstream | -- | -- | -- | ✅ | ✅ | ✅ | -- | -- | -- | -- | -- | ✅ |
| protocols | `proxy_protocol_accept` Accept PROXY protocol from clients (:8082) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ | ✅ |
| protocols | `tcp_l4` TCP (L4) proxying | ✅ | -- | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- |
| protocols | `udp_l4` UDP proxying | ✅ | -- | -- | ✅ | ✅ | -- | ✅ | ✅ | ✅ | -- | ✅ | -- |
| protocols | `tls_passthrough_sni` TLS passthrough by SNI (L4) | -- | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ | -- |
| tls | `tls_termination` TLS termination | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| tls | `tls13` TLS 1.3 negotiated | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| tls | `tls_legacy_refused` TLS 1.0/1.1 refused | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| tls | `mtls_client_cert` Mutual TLS (client certificate required) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ |
| tls | `sni_multi_cert` Multiple certificates selected by SNI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| tls | `acme_auto_cert` Automatic certificate via ACME (Pebble) | -- | ✅ | -- | ✅ | -- | ✅ | ✅ | ✅ | ✅ | -- | ✅ | -- |
| caching | `cache_hit` Response caching | ✅ | ✅ | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| caching | `cache_purge` Cache purge | ✅ | -- | ✅ | ✅ | -- | -- | ✅ | ✅ | ✅ | -- | -- | ✅ |
| caching | `cache_stale_on_error` Serve stale on upstream error | -- | ✅ | ✅ | ✅ | -- | -- | -- | ✅ | ✅ | -- | -- | ✅ |
| compression | `compress_gzip` gzip compression | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| compression | `compress_brotli` Brotli compression | ✅ | ✅ | -- | ✅ | ✅ | -- | -- | -- | -- | -- | ✅ | -- |
| compression | `compress_zstd` Zstandard compression | -- | -- | -- | ✅ | ✅ | -- | -- | -- | -- | ✅ | ✅ | -- |
| headers | `xff_headers` X-Forwarded-* headers | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| headers | `forwarded_rfc7239` RFC 7239 Forwarded header | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| headers | `header_add_remove` Header manipulation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| headers | `request_id` Request ID generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| security | `rate_limit` Request rate limiting | ✅ | -- | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| security | `connection_limit` Concurrent connection limit | ✅ | -- | ✅ | -- | -- | ✅ | -- | ✅ | ✅ | ✅ | ✅ | -- |
| security | `ip_allow_deny` IP allow / deny lists | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| security | `basic_auth` HTTP basic authentication | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| security | `jwt_auth` JWT validation (HS256) | ✅ | -- | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| security | `forward_auth` External authorization (forward auth / auth_request / ext_authz) | ✅ | -- | -- | ✅ | ✅ | ✅ | -- | ✅ | ✅ | -- | ✅ | ✅ |
| security | `cors` CORS preflight answered by the proxy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| security | `security_headers` Security response headers | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| security | `body_size_limit` Request body size limit | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| security | `upstream_timeout` Upstream read timeout | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| security | `fault_injection` Fault injection | ✅ | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| security | `bandwidth_limit` Bandwidth limiting | ✅ | ✅ | -- | -- | ❌ | ✅ | -- | ✅ | ✅ | -- | -- | -- |
| operations | `static_files` Static file serving | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | -- | ✅ |
| operations | `custom_error_page` Custom error page | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| operations | `hot_reload` Configuration reload without restart | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| operations | `access_log_json` Structured (JSON) access log | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| operations | `metrics_prometheus` Prometheus metrics | ✅ | ✅ | -- | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| operations | `admin_api` Admin / stats / runtime API | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| operations | `tracing_otel` Distributed tracing (OpenTelemetry -> Jaeger) | ✅ | -- | -- | ✅ | ✅ | -- | ✅ | ✅ | -- | -- | ✅ | -- |
| operations | `docker_label_discovery` Service discovery from Docker labels | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | ✅ | -- |

## Load scenarios (requests/s unless noted; p99 in ms; proxy CPU = average cores used of the 4 allowed)

### `h1_keepalive` — HTTP/1.1 keep-alive, 64 connections, /small

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 10,546 | 5.82 | 19.02 | 51.15 | 0/0 | 3.71 (92.9%) | 352.3 | 201 |
| Apache httpd 2.4 | 12,858 | 4.59 | 11.68 | 51.96 | 0/0 | 3.93 (98.2%) | 305.5 | 73 |
| Apache Traffic Server 9.2 | 27,938 | 2.12 | 4.46 | 35.31 | 0/0 | 3.78 (94.4%) | 135.2 | 195 |
| Caddy 2 | 11,299 | 4.70 | 18.08 | 40.99 | 0/0 | 3.90 (97.4%) | 344.9 | 49 |
| Envoy 1.39 | 18,582 | 3.43 | 5.91 | 36.34 | 0/0 | 3.99 (99.8%) | 214.9 | 34 |
| HAProxy 3.4 | 31,887 | 1.98 | 3.10 | 22.34 | 0/0 | 3.99 (99.6%) | 125.0 | 306 |
| Kong Gateway 3.9 | 10,394 | 5.35 | 16.78 | 61.14 | 0/0 | 4.00 (99.9%) | 384.5 | 1036 |
| NGINX 1.29 | 66,841 | 0.50 | 5.71 | 30.48 | 0/0 | 3.98 (99.6%) | 59.6 | 442 |
| OpenResty 1.27 | 52,081 | 1.17 | 2.09 | 19.85 | 0/0 | 4.00 (99.9%) | 76.7 | 82 |
| Pingora (Rust, custom) | 25,376 | 2.49 | 4.13 | 18.58 | 0/0 | 3.94 (98.6%) | 155.4 | 24 |
| Traefik v3 | 12,396 | 4.38 | 15.42 | 39.47 | 0/0 | 3.88 (97.0%) | 313.1 | 52 |
| Varnish 8 + hitch | 10,773 | 5.04 | 19.10 | 47.13 | 0/0 | 3.95 (98.8%) | 366.9 | 281 |

### `h1_no_keepalive` — HTTP/1.1 new connection per request, 64 in flight

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 3,662 | 17.11 | 41.14 | 67.70 | 0/0 | 1.75 (43.6%) | 476.5 | 201 |
| Apache httpd 2.4 | 3,743 | 16.36 | 41.35 | 73.34 | 0/0 | 1.53 (38.3%) | 409.7 | 77 |
| Apache Traffic Server 9.2 | 4,507 | 13.49 | 41.79 | 75.83 | 0/0 | 1.20 (29.9%) | 265.7 | 216 |
| Caddy 2 | 3,719 | 15.15 | 44.62 | 73.22 | 0/0 | 1.98 (49.5%) | 532.5 | 43 |
| Envoy 1.39 | 6,270 | 9.74 | 24.64 | 47.74 | 0/0 | 1.95 (48.7%) | 311.0 | 40 |
| HAProxy 3.4 | 21,763 | 2.88 | 5.70 | 18.38 | 0/0 | 3.97 (99.3%) | 182.5 | 307 |
| Kong Gateway 3.9 | 3,653 | 16.02 | 46.48 | 82.05 | 0/0 | 1.86 (46.6%) | 509.9 | 1029 |
| NGINX 1.29 | 13,385 | 2.14 | 32.53 | 68.45 | 0/0 | 1.81 (45.1%) | 134.9 | 445 |
| OpenResty 1.27 | 5,983 | 3.08 | 38.15 | 68.00 | 0/0 | 0.99 (24.7%) | 165.1 | 83 |
| Pingora (Rust, custom) | 4,194 | 13.86 | 37.66 | 63.83 | 0/0 | 1.44 (36.0%) | 343.8 | 27 |
| Traefik v3 | 3,751 | 15.03 | 44.16 | 77.79 | 0/0 | 1.98 (49.5%) | 528.2 | 48 |
| Varnish 8 + hitch | 4,187 | 13.60 | 39.73 | 62.70 | 0/0 | 2.09 (52.2%) | 498.4 | 286 |

### `wrk_h1` — wrk reference: 8 threads, 64 connections, /small

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 11,329 | 5.49 | 17.11 | 43.04 | 0/0 | 3.93 (98.2%) | 346.6 | 204 |
| Apache httpd 2.4 | 19,574 | 3.07 | 6.77 | 17.30 | 0/0 | 3.92 (98.0%) | 200.3 | 78 |
| Apache Traffic Server 9.2 | 31,729 | 1.81 | 19.99 | 25.93 | 0/0 | 3.63 (90.7%) | 114.3 | 340 |
| Caddy 2 | 11,639 | 5.02 | 18.27 | 41.31 | 0/0 | 3.85 (96.4%) | 331.2 | 48 |
| Envoy 1.39 | 18,995 | 3.25 | 5.50 | 13.49 | 0/0 | 3.99 (99.9%) | 210.3 | 40 |
| HAProxy 3.4 | 35,051 | 1.79 | 3.00 | 11.28 | 0/0 | 3.99 (99.7%) | 113.8 | 306 |
| Kong Gateway 3.9 | 10,798 | 6.18 | 17.69 | 42.51 | 0/0 | 4.01 (100.3%) | 371.4 | 1040 |
| NGINX 1.29 | 68,018 | 0.62 | 9.41 | 20.62 | 0/0 | 4.00 (99.9%) | 58.7 | 444 |
| OpenResty 1.27 | 53,611 | 1.21 | 2.47 | 16.82 | 0/0 | 4.00 (100.0%) | 74.6 | 83 |
| Pingora (Rust, custom) | 24,902 | 2.54 | 4.23 | 10.72 | 0/0 | 3.94 (98.4%) | 158.1 | 30 |
| Traefik v3 | 12,662 | 4.65 | 15.14 | 34.67 | 0/0 | 3.88 (97.1%) | 306.9 | 56 |
| Varnish 8 + hitch | 10,524 | 5.45 | 20.15 | 41.65 | 0/0 | 3.94 (98.4%) | 374.1 | 380 |

### `tls_h1` — HTTPS HTTP/1.1 keep-alive, 64 connections

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 10,158 | 5.76 | 16.30 | 97.09 | 0/0 | 3.99 (99.7%) | 392.6 | 210 |
| Apache httpd 2.4 | 11,616 | 5.04 | 13.18 | 129 | 0/0 | 3.92 (98.0%) | 337.3 | 97 |
| Apache Traffic Server 9.2 | 21,403 | 2.79 | 5.85 | 117 | 0/0 | 3.80 (95.0%) | 177.6 | 429 |
| Caddy 2 | 11,036 | 4.73 | 19.37 | 97.30 | 0/0 | 3.82 (95.5%) | 346.0 | 51 |
| Envoy 1.39 | 17,336 | 3.50 | 6.10 | 80.34 | 0/0 | 3.98 (99.4%) | 229.3 | 39 |
| HAProxy 3.4 | 27,703 | 2.29 | 3.11 | 109 | 0/0 | 3.98 (99.6%) | 143.7 | 310 |
| Kong Gateway 3.9 | 8,770 | 6.99 | 18.48 | 168 | 0/0 | 3.96 (98.9%) | 451.3 | 1040 |
| NGINX 1.29 | 48,844 | 0.55 | 6.83 | 102 | 0/0 | 3.94 (98.6%) | 80.7 | 448 |
| OpenResty 1.27 | 34,143 | 1.25 | 5.35 | 113 | 0/0 | 3.61 (90.2%) | 105.6 | 83 |
| Pingora (Rust, custom) | 15,417 | 4.09 | 6.78 | 73.07 | 0/0 | 3.95 (98.8%) | 256.4 | 32 |
| Traefik v3 | 11,642 | 4.64 | 16.27 | 93.19 | 0/0 | 3.88 (97.1%) | 333.6 | 69 |
| Varnish 8 + hitch | 7,525 | 7.27 | 26.01 | 111 | 0/0 | 3.92 (97.9%) | 520.2 | 258 |

### `tls_h2` — HTTPS HTTP/2: 16 connections x 8 streams

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 10,878 | 10.65 | 28.21 | 49.60 | 1232/0 | 3.98 (99.6%) | 366.2 | 209 |
| Apache httpd 2.4 | 7,010 | 14.07 | 60.01 | 141 | 0/0 | 3.19 (79.8%) | 455.3 | 108 |
| Apache Traffic Server 9.2 | 24,182 | 5.04 | 14.63 | 33.67 | 0/0 | 3.87 (96.8%) | 160.0 | 536 |
| Caddy 2 | 9,113 | 12.79 | 36.11 | 67.95 | 0/0 | 3.87 (96.8%) | 425.0 | 56 |
| Envoy 1.39 | 21,090 | 5.88 | 9.71 | 21.06 | 0/0 | 3.94 (98.5%) | 186.7 | 40 |
| HAProxy 3.4 | 27,945 | 4.50 | 6.82 | 23.03 | 0/0 | 3.98 (99.6%) | 142.5 | 311 |
| Kong Gateway 3.9 | 9,212 | 13.77 | 44.13 | 81.97 | 48/0 | 3.80 (95.0%) | 412.7 | 1045 |
| NGINX 1.29 | 59,485 | 0.96 | 10.95 | 29.02 | 640/0 | 3.98 (99.4%) | 66.8 | 457 |
| OpenResty 1.27 | 44,219 | 2.66 | 6.33 | 21.53 | 472/0 | 3.99 (99.7%) | 90.2 | 83 |
| Pingora (Rust, custom) | 21,474 | 5.80 | 10.17 | 18.07 | 0/0 | 3.92 (97.9%) | 182.3 | 32 |
| Traefik v3 | 9,857 | 11.91 | 32.45 | 54.80 | 0/0 | 3.91 (97.8%) | 397.1 | 65 |
| Varnish 8 + hitch | 5,985 | 15.63 | 86.10 | 214 | 0/0 | 3.94 (98.4%) | 657.5 | 329 |

### `h3` — HTTP/3 (QUIC): 16 connections x 8 streams

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 9,083 | 12.88 | 28.04 | 56.28 | 810/0 | 3.96 (98.9%) | 435.4 | 228 |
| Apache httpd 2.4 | unsupported: no HTTP/3 in httpd (mod_http2 stops at HTTP/2) | | | | | | | |
| Apache Traffic Server 9.2 | unsupported: the Ubuntu build has no QUIC (experimental in 9.x, needs qui | | | | | | | |
| Caddy 2 | 9,456 | 12.33 | 33.86 | 67.22 | 0/0 | 3.90 (97.4%) | 411.9 | 51 |
| Envoy 1.39 | 10,252 | 13.20 | 22.14 | 42.40 | 0/0 | 3.98 (99.6%) | 388.5 | 44 |
| HAProxy 3.4 | 30,221 | 4.11 | 8.23 | 28.23 | 0/0 | 3.80 (95.1%) | 125.9 | 309 |
| Kong Gateway 3.9 | unsupported: no HTTP/3 in Kong Gateway 3.9 OSS | | | | | | | |
| NGINX 1.29 | 66,414 | 1.21 | 8.76 | 41.18 | 106/0 | 3.83 (95.7%) | 57.6 | 481 |
| OpenResty 1.27 | 57,012 | 2.08 | 6.52 | 43.83 | 124/0 | 3.81 (95.2%) | 66.8 | 104 |
| Pingora (Rust, custom) | unsupported: no HTTP/3 in Pingora | | | | | | | |
| Traefik v3 | 10,164 | 11.57 | 30.75 | 65.30 | 0/0 | 3.91 (97.9%) | 385.1 | 63 |
| Varnish 8 + hitch | unsupported: no HTTP/3 in Varnish Cache or hitch (Varnish Enterprise / a  | | | | | | | |

### `large_1mb` — 1 MiB responses, 32 connections (throughput MB/s)

| proxy | MB/s | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 1027.9 MB/s | 32.57 | 44.80 | 76.11 | 0/0 | 4.00 (99.9%) | 3,889.5 | 227 |
| Apache httpd 2.4 | 1631.3 MB/s | 13.69 | 69.73 | 137 | 0/0 | 3.98 (99.5%) | 2,438.7 | 113 |
| Apache Traffic Server 9.2 | 3703.0 MB/s | 8.55 | 11.87 | 39.43 | 0/0 | 4.00 (99.9%) | 1,079.5 | 554 |
| Caddy 2 | 2966.4 MB/s | 9.29 | 32.43 | 68.80 | 0/0 | 3.85 (96.3%) | 1,298.9 | 55 |
| Envoy 1.39 | 3642.2 MB/s | 8.52 | 13.73 | 27.38 | 0/0 | 4.00 (99.9%) | 1,097.6 | 76 |
| HAProxy 3.4 | 2257.2 MB/s | 13.93 | 21.86 | 54.43 | 0/0 | 3.98 (99.5%) | 1,763.2 | 309 |
| Kong Gateway 3.9 | 1377.3 MB/s | 21.17 | 43.58 | 90.95 | 0/0 | 4.00 (100.0%) | 2,903.1 | 1048 |
| NGINX 1.29 | 4388.8 MB/s | 6.76 | 17.47 | 63.99 | 0/0 | 3.98 (99.5%) | 906.6 | 483 |
| OpenResty 1.27 | 4225.8 MB/s | 7.88 | 14.39 | 44.30 | 0/0 | 3.96 (99.1%) | 937.9 | 106 |
| Pingora (Rust, custom) | 3438.3 MB/s | 9.18 | 15.78 | 33.83 | 0/0 | 3.98 (99.4%) | 1,156.5 | 62 |
| Traefik v3 | 2896.8 MB/s | 9.72 | 31.23 | 70.52 | 0/0 | 3.85 (96.3%) | 1,329.6 | 44 |
| Varnish 8 + hitch | 3603.0 MB/s | 8.48 | 19.52 | 41.33 | 0/0 | 3.97 (99.3%) | 1,102.0 | 411 |

### `gzip_64k` — 64 KiB text compressed by the proxy (gzip), 64 connections

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 4,788 | 13.76 | 29.70 | 74.45 | 0/0 | 3.83 (95.8%) | 800.6 | 212 |
| Apache httpd 2.4 | 5,519 | 9.88 | 37.92 | 112 | 0/0 | 3.93 (98.1%) | 711.3 | 122 |
| Apache Traffic Server 9.2 | 5,794 | 10.95 | 15.07 | 49.12 | 0/0 | 4.00 (99.9%) | 689.7 | 579 |
| Caddy 2 | 9,311 | 5.88 | 21.94 | 50.84 | 0/0 | 3.89 (97.3%) | 417.9 | 85 |
| Envoy 1.39 | 8,832 | 6.79 | 13.03 | 27.51 | 0/0 | 4.00 (100.0%) | 452.8 | 82 |
| HAProxy 3.4 | 12,847 | 4.91 | 6.69 | 22.75 | 0/0 | 4.00 (99.9%) | 311.2 | 308 |
| Kong Gateway 3.9 | 6,239 | 10.08 | 23.33 | 53.97 | 0/0 | 3.99 (99.7%) | 639.4 | 1052 |
| NGINX 1.29 | 9,310 | 5.80 | 20.99 | 47.89 | 0/0 | 4.00 (99.9%) | 429.2 | 487 |
| OpenResty 1.27 | 6,447 | 10.54 | 16.31 | 33.51 | 0/0 | 4.00 (99.9%) | 619.6 | 85 |
| Pingora (Rust, custom) | 13,458 | 4.68 | 7.92 | 20.39 | 0/0 | 3.98 (99.4%) | 295.3 | 62 |
| Traefik v3 | 9,375 | 5.93 | 20.48 | 47.42 | 0/0 | 3.89 (97.3%) | 415.3 | 78 |
| Varnish 8 + hitch | 2,591 | 18.09 | 101 | 211 | 0/0 | 3.93 (98.2%) | 1,515.5 | 389 |

### `cache_hit` — served from the proxy cache, 64 connections

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 11,591 | 5.52 | 16.71 | 89.59 | 0/0 | 3.87 (96.8%) | 334.2 | 214 |
| Apache httpd 2.4 | 19,537 | 0.75 | 17.29 | 52.29 | 0/0 | 3.63 (90.9%) | 186.1 | 122 |
| Apache Traffic Server 9.2 | 52,600 | 1.13 | 2.38 | 23.98 | 0/0 | 4.00 (100.0%) | 76.1 | 801 |
| Caddy 2 | 1,662 | 21.05 | 199 | 505 | 0/0 | 3.89 (97.2%) | 2,340.2 | 331 |
| Envoy 1.39 | unsupported: the HTTP cache filter is alpha; in 1.39 it makes its own int | | | | | | | |
| HAProxy 3.4 | 56,216 | 1.05 | 1.64 | 22.07 | 0/0 | 4.00 (100.0%) | 71.1 | 310 |
| Kong Gateway 3.9 | 11,389 | 5.64 | 15.26 | 40.95 | 0/0 | 3.99 (99.8%) | 350.7 | 1052 |
| NGINX 1.29 | 63,485 | 0.30 | 7.70 | 21.78 | 0/0 | 4.00 (100.0%) | 63.0 | 487 |
| OpenResty 1.27 | 53,032 | 1.52 | 2.63 | 22.45 | 0/0 | 3.98 (99.5%) | 75.1 | 85 |
| Pingora (Rust, custom) | 26,860 | 2.36 | 4.43 | 26.99 | 0/0 | 3.97 (99.3%) | 147.9 | 32 |
| Traefik v3 | unsupported: no HTTP cache in Traefik OSS (Traefik Enterprise / plugins) | | | | | | | |
| Varnish 8 + hitch | 34,387 | 1.90 | 5.32 | 28.87 | 0/0 | 3.99 (99.7%) | 116.0 | 397 |

### `ws_echo` — WebSocket echo: 64 VUs x 500 messages (k6)

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 104,346 | 1.00 | 3.00 | 23.00 | 0/0 | 3.24 (80.9%) | 31.0 | 215 |
| Apache httpd 2.4 | 65,424 | 1.00 | 3.00 | 18.00 | 0/0 | 3.93 (98.1%) | 60.0 | 124 |
| Apache Traffic Server 9.2 | 96,681 | 1.00 | 3.00 | 18.00 | 0/0 | 3.66 (91.5%) | 37.9 | 804 |
| Caddy 2 | 78,878 | 1.00 | 4.00 | 18.00 | 0/0 | 3.20 (79.9%) | 40.5 | 70 |
| Envoy 1.39 | 84,220 | 1.00 | 3.00 | 18.00 | 0/0 | 3.73 (93.3%) | 44.3 | 82 |
| HAProxy 3.4 | 102,366 | 1.00 | 3.00 | 21.00 | 0/0 | 3.67 (91.7%) | 35.8 | 310 |
| Kong Gateway 3.9 | 103,775 | 1.00 | 3.00 | 20.00 | 0/0 | 3.28 (81.9%) | 31.6 | 1054 |
| NGINX 1.29 | 102,502 | 1.00 | 3.00 | 26.00 | 0/0 | 3.58 (89.6%) | 35.0 | 486 |
| OpenResty 1.27 | 105,329 | 1.00 | 3.00 | 19.00 | 0/0 | 3.22 (80.5%) | 30.6 | 85 |
| Pingora (Rust, custom) | 81,950 | 1.00 | 3.00 | 14.00 | 0/0 | 3.80 (94.9%) | 46.3 | 46 |
| Traefik v3 | 76,534 | 1.00 | 4.00 | 18.00 | 0/0 | 3.19 (79.9%) | 41.8 | 61 |
| Varnish 8 + hitch | 79,715 | 1.00 | 3.00 | 16.00 | 0/0 | 3.82 (95.6%) | 48.0 | 398 |

### `grpc_health` — gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 9,213 | 12.91 | 33.56 | 70.61 | 0/0 | 3.99 (99.8%) | 433.5 | 219 |
| Apache httpd 2.4 | 6,928 | 15.77 | 59.95 | 122 | 0/0 | 3.28 (82.1%) | 474.0 | 127 |
| Apache Traffic Server 9.2 | unsupported: no HTTP/2 to origins, so no gRPC proxying | | | | | | | |
| Caddy 2 | 6,947 | 17.44 | 29.28 | 55.71 | 0/0 | 3.80 (94.9%) | 546.6 | 63 |
| Envoy 1.39 | 19,294 | 6.05 | 13.79 | 21.83 | 0/0 | 3.86 (96.6%) | 200.2 | 82 |
| HAProxy 3.4 | 20,341 | 6.29 | 8.87 | 26.58 | 0/0 | 3.99 (99.8%) | 196.3 | 310 |
| Kong Gateway 3.9 | 7,711 | 15.28 | 38.71 | 75.72 | 0/0 | 3.99 (99.8%) | 517.7 | 1065 |
| NGINX 1.29 | 9,720 | 13.08 | 17.99 | 24.43 | 0/0 | 1.03 (25.7%) | 105.9 | 498 |
| OpenResty 1.27 | 6,204 | 21.26 | 27.39 | 46.75 | 0/0 | 1.02 (25.6%) | 165.0 | 87 |
| Pingora (Rust, custom) | 9,203 | 13.65 | 24.62 | 35.85 | 0/0 | 3.00 (74.9%) | 325.5 | 46 |
| Traefik v3 | 7,026 | 17.77 | 28.69 | 40.62 | 0/0 | 3.79 (94.9%) | 540.1 | 49 |
| Varnish 8 + hitch | unsupported: no gRPC: Varnish cannot proxy HTTP/2 with trailers to backen | | | | | | | |

### `open_loop_5k` — open loop at exactly 5000 rps (64 conns): latency without coordinated omission

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 4,965 | 0.93 | 11.70 | 19.41 | 0/0 | 2.68 (66.9%) | 539.1 | 217 |
| Apache httpd 2.4 | 4,996 | 0.62 | 1.74 | 5.71 | 0/0 | 2.28 (57.0%) | 456.4 | 127 |
| Apache Traffic Server 9.2 | 4,992 | 1.41 | 3.94 | 12.48 | 0/0 | 1.93 (48.1%) | 385.6 | 826 |
| Caddy 2 | 4,992 | 0.70 | 5.20 | 23.60 | 0/0 | 2.26 (56.5%) | 452.4 | 50 |
| Envoy 1.39 | 4,995 | 1.37 | 3.69 | 8.58 | 0/0 | 2.61 (65.2%) | 522.3 | 82 |
| HAProxy 3.4 | 4,996 | 0.61 | 1.69 | 4.90 | 0/0 | 1.73 (43.2%) | 346.2 | 311 |
| Kong Gateway 3.9 | 4,959 | 0.84 | 9.44 | 41.45 | 0/0 | 2.76 (69.1%) | 557.0 | 1059 |
| NGINX 1.29 | 4,996 | 0.58 | 0.99 | 3.83 | 0/0 | 1.06 (26.5%) | 212.3 | 497 |
| OpenResty 1.27 | 4,996 | 0.58 | 0.99 | 6.17 | 0/0 | 1.26 (31.6%) | 252.7 | 85 |
| Pingora (Rust, custom) | 4,995 | 0.60 | 1.68 | 5.47 | 0/0 | 2.08 (51.9%) | 415.8 | 46 |
| Traefik v3 | 4,995 | 0.70 | 3.92 | 16.13 | 0/0 | 2.24 (56.0%) | 448.7 | 48 |
| Varnish 8 + hitch | 4,995 | 0.70 | 1.89 | 3.67 | 0/0 | 2.44 (61.0%) | 488.7 | 440 |

### `ratelimit_accuracy` — /limited (10 r/s) hammered at 200 rps for 10 s: how many get through

| proxy | status codes | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | ok | 0.74 | 2.87 | 6.12 | 0/1895 | 0.20 (5.1%) | 1,026.3 | 249 |
| Apache httpd 2.4 | unsupported: no request-rate limiting in the standard modules (mod_rateli | | | | | | | |
| Apache Traffic Server 9.2 | unsupported: rate_limit.so limits concurrency per remap, not requests per | | | | | | | |
| Caddy 2 | ok | 0.70 | 1.71 | 4.62 | 0/1901 | 0.23 (5.7%) | 1,138.9 | 48 |
| Envoy 1.39 | ok | 0.62 | 1.63 | 1.79 | 0/1887 | 0.12 (3.0%) | 596.3 | 83 |
| HAProxy 3.4 | ok | 0.36 | 0.52 | 1.97 | 0/1991 | 0.08 (2.1%) | 414.0 | 310 |
| Kong Gateway 3.9 | ok | 0.88 | 2.72 | 3.71 | 0/1891 | 0.26 (6.6%) | 1,310.0 | 1060 |
| NGINX 1.29 | ok | 0.32 | 1.09 | 1.44 | 0/1895 | 0.07 (1.7%) | 343.2 | 497 |
| OpenResty 1.27 | ok | 0.33 | 1.06 | 1.63 | 0/1896 | 0.07 (1.8%) | 364.5 | 85 |
| Pingora (Rust, custom) | ok | 0.33 | 1.12 | 1.33 | 0/1901 | 0.08 (2.0%) | 390.9 | 46 |
| Traefik v3 | ok | 0.65 | 48.59 | 53.23 | 0/1896 | 0.22 (5.5%) | 1,096.1 | 34 |
| Varnish 8 + hitch | ok | 0.49 | 0.59 | 2.18 | 0/1991 | 0.12 (3.0%) | 591.2 | 436 |

### `c10k` — 10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)

| proxy | rps | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Apache APISIX 3.15 | 5,296 | 1,687 | 2,345 | 22,017 | 0/0 | 3.82 (95.5%) | 721.4 | 1290 |
| Apache httpd 2.4 | 464 | 503 | 61,412 | 61,922 | 12843/0 | 0.26 (6.5%) | 561.8 | 85 |
| Apache Traffic Server 9.2 | 9,127 | 1,041 | 1,340 | 1,588 | 0/0 | 2.35 (58.8%) | 257.6 | 4442 |
| Caddy 2 | 3,761 | 1,842 | 6,257 | 8,142 | 0/5466 | 3.84 (96.0%) | 1,020.6 | 1998 |
| Envoy 1.39 | 8,576 | 1,145 | 1,856 | 2,043 | 0/0 | 2.82 (70.5%) | 328.9 | 1380 |
| HAProxy 3.4 | 18,936 | 502 | 997 | 1,096 | 0/0 | 3.10 (77.6%) | 163.9 | 746 |
| Kong Gateway 3.9 | 7,857 | 1,198 | 1,761 | 2,067 | 0/0 | 3.88 (97.1%) | 494.2 | 1338 |
| NGINX 1.29 | 19,008 | 501 | 861 | 1,231 | 0/0 | 2.50 (62.6%) | 131.7 | 563 |
| OpenResty 1.27 | 18,552 | 502 | 1,014 | 1,369 | 0/0 | 2.95 (73.8%) | 159.1 | 91 |
| Pingora (Rust, custom) | 13,670 | 710 | 1,070 | 1,515 | 0/0 | 3.89 (97.3%) | 284.8 | 619 |
| Traefik v3 | 4,073 | 1,483 | 7,195 | 10,398 | 0/0 | 3.90 (97.6%) | 958.6 | 2428 |
| Varnish 8 + hitch | 5,025 | 523 | 21,079 | 29,009 | 0/0 | 2.66 (66.5%) | 529.7 | 3423 |

## Chaos: backend failover and reload under load

| proxy | failover: load errors / requests | timeline failed (of ~480 @20 rps) | fail window s | app2 back after s | reload kind | reload: load errors / requests | reload timeline failed | reload s |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| Apache APISIX 3.15 | 0 / 23994 | 0 / 562 | 0.0 | 3.4 |  | 0 / 166414 | 0 / 330 | 0.04 |
| Apache httpd 2.4 | 0 / 19946 | 0 / 559 | 0.0 | 2.6 |  | 48 / 176743 | 1 / 325 | 0.34 |
| Apache Traffic Server 9.2 | 0 / 20848 | 0 / 560 | 0.0 | 0.4 |  | 0 / 422368 | 0 / 330 | 0.09 |
| Caddy 2 | 0 / 23921 | 0 / 574 | 0.0 | 0.9 |  | 0 / 176221 | 0 / 344 | 0.23 |
| Envoy 1.39 | 0 / 18225 | 0 / 559 | 0.0 | 4.1 |  | 0 / 267172 | 0 / 328 | 0.01 |
| HAProxy 3.4 | 0 / 15378 | 0 / 570 | 0.0 | 4.3 |  | 0 / 461888 | 0 / 337 | 0.23 |
| Kong Gateway 3.9 | 0 / 23974 | 0 / 562 | 0.0 | 3.6 |  | 0 / 155390 | 0 / 326 | 0.18 |
| NGINX 1.29 | 0 / 23441 | 0 / 564 | 0.0 | 6.1 |  | 52 / 954396 | 0 / 333 | 0.18 |
| OpenResty 1.27 | 0 / 23628 | 0 / 564 | 0.0 | 5.5 |  | 28 / 765919 | 0 / 357 | 0.22 |
| Pingora (Rust, custom) | 1 / 18389 | 0 / 574 | 0.0 | 3.1 |  | 37 / 256776 | 0 / 328 | 2.09 |
| Traefik v3 | 12 / 22798 | 0 / 560 | 0.0 | 0.7 |  | 0 / 175328 | 0 / 334 | 0.01 |
| Varnish 8 + hitch | 0 / 18288 | 0 / 563 | 0.0 | 1.7 |  | 0 / 157887 | 0 / 331 | 1.35 |

## Probe details per proxy

### Apache APISIX 3.15 (`apisix`)

Apache APISIX 3.15 in standalone mode (routes in apisix.yaml, hot-reloaded on change). Upstreams show roundrobin / weighted / least_conn / chash on a header, active + passive health checks and retries; traffic-split does the canary split and the cookie stickiness (rules matched on the cookie), proxy-mirror mirrors to shadow, forward-auth / jwt-auth / basic-auth / ip-restriction / limit-req / limit-conn / client-control / cors / fault-injection / redirect / proxy-cache (disk, PURGE) / gzip / brotli / request-id / prometheus / opentelemetry cover the rest; serverless functions set $limit_rate (bandwidth) and serve the static file. HTTP/3 on :8443, h2c on :8080, PROXY protocol on :8082, TCP/UDP stream routes, mTLS per SNI.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab:8443/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ✅ | slow share=0.08 {'app1': 137, 'slow': 25, 'app2': 138} |
| `lb_hash_header` | ✅ | u1 -> {'app1': 20}; 10 users -> {'app2': 15, 'app1': 6, 'app3': 9} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=app1; Path=/; HttpOnly' first=app1 then={'app1': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=5 |
| `lb_outlier_ejection` | ✅ | first20={200: 13, 500: 7} last20={200: 36, 500: 4} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 3.2s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.6s |
| `lb_canary_split` | ✅ | canary share=0.100 {'app3': 60, 'app1': 60, 'app2': 60, 'canary': 20} |
| `lb_mirror` | ✅ | shadow received 20/20 |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app2': 2, 'app3': 3, 'app1': 2} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
| `http3` | ✅ | proto=HTTP/3.0 status={'200': 641} errors=0 [] |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app2 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.21s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | -- | HTTP/2 to upstreams only for gRPC (scheme grpc/grpcs) |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': ''} |
| `proxy_protocol_upstream` | -- | APISIX cannot send PROXY protocol to HTTP upstreams (enable_tcp_pp_to_upstream is for stream routes) |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:32902 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:34770 headers=['Connection'] |
| `udp_l4` | ✅ | echo:app1:ping-a7012f |
| `tls_passthrough_sni` | -- | stream routes with `sni` terminate TLS; there is no SNI-based passthrough |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 80571E2694750000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client', 'X-Client-Cert-Verify': 'SUCCESS'} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | -- | no ACME client in APISIX (use cert-manager / acme.sh and push the certificate) |
| `cache_hit` | ✅ | origin app2#1 -> app2#1; Apisix-Cache-Status: MISS -> HIT age=None |
| `cache_purge` | ✅ | purge -> 200; origin app1#1 -> app3#1; NOTE: the keep-alive connection that sent PURGE kept getting the old entry, a fresh connection saw the purge |
| `cache_stale_on_error` | -- | proxy-cache has no stale-if-error mode |
| `compress_gzip` | ✅ | Content-Encoding=gzip 345 bytes (65536 uncompressed) |
| `compress_brotli` | ✅ | Content-Encoding=br 165 bytes (65536 uncompressed) |
| `compress_zstd` | -- | gzip and brotli plugins only |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
| `header_add_remove` | ✅ | X-Lab-Proxy=apisix X-Powered-By=removed Server=APISIX |
| `request_id` | ✅ | 'c62571c7-b404-4c7c-9c24-7b7c41b93196' / '22bf7084-6e75-48c4-afb4-4d8698e5ee40' |
| `rate_limit` | ✅ | codes={200: 6, 429: 34} |
| `connection_limit` | ✅ | codes={200: 3, 429: 9} |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="basic") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 200 ACAO=* methods=GET,POST,PUT,DELETE,OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.00s |
| `fault_injection` | ✅ | 503 share=0.17 codes={200: 83, 503: 17} |
| `bandwidth_limit` | ✅ | 200 1048576 bytes in 1.98s (528 KB/s) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes', 'cache', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'status', 'time', 'ua', 'upstream'] |
| `metrics_prometheus` | ✅ | 200 2803 samples e.g. apisix_bandwidth{type="egress",route="a",service="",consumer="",node="10.77.0.12 |
| `admin_api` | ✅ | GET /v1/routes -> 200 '[{"modifiedIndex":1789329706,"key":"/routes/a","value":{"priority":100,"hosts":[' |
| `tracing_otel` | ✅ | jaeger traces for service 'apisix': 5 |
| `docker_label_discovery` | -- | no Docker provider (APISIX Ingress Controller does this on Kubernetes) |

### Apache httpd 2.4 (`apache`)

Official httpd 2.4 image, event MPM sized for 4 cores. Demonstrates mod_proxy (http/h2c/ws/tls upstreams), mod_proxy_balancer (byrequests, bybusyness, loadfactor, stickysession, failonstatus), mod_proxy_hcheck active health checks, mod_cache_disk with CacheStaleOnError, mod_deflate + mod_brotli, mod_ratelimit bandwidth limiting, mod_remoteip PROXY protocol, mod_md ACME against Pebble (activated by a graceful reload from MDMessageCmd), mTLS with SSL_CLIENT_S_DN_CN, mod_unique_id request ids, JSON access log and a Prometheus exporter sidecar. No HTTP/3, no L4, no rate limiting, no JWT/forward auth without third-party modules.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=http://app.lab:18080/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab:18080/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ❌ | slow share=0.33 {'app1': 100, 'app2': 100, 'slow': 100} |
| `lb_hash_header` | -- | mod_proxy_balancer has byrequests / bytraffic / bybusyness / heartbeat only - no consistent hashing |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=.a1; path=/; HttpOnly' first=app1 then={'app1': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=4 |
| `lb_outlier_ejection` | ✅ | first20={200: 19, 500: 1} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 6.2s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 2.2s |
| `lb_canary_split` | ✅ | canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
| `lb_mirror` | -- | no request mirroring in mod_proxy |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app2': 2, 'app1': 3, 'app3': 1} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app2",\n "pool": "app",\n ' |
| `http3` | -- | no HTTP/3 in httpd (mod_http2 stops at HTTP/2) |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app1 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.21s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | ✅ | upstream proto=HTTP/2.0 |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
| `proxy_protocol_upstream` | -- | mod_proxy cannot send PROXY protocol to upstreams (mod_remoteip only accepts it) |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:60728 |
| `tcp_l4` | -- | httpd is HTTP-only (no generic TCP proxying) |
| `udp_l4` | -- | httpd is HTTP-only |
| `tls_passthrough_sni` | -- | no L4 passthrough (mod_proxy terminates or re-encrypts TLS) |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 80B70709F6790000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'lab-client', 'X-Client-Cert-Verify': 'SUCCESS'} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | ✅ | subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
| `cache_hit` | ✅ | origin app1#1 -> app1#1; X-Cache: MISS from app.lab -> HIT from app.lab age=0 |
| `cache_purge` | -- | mod_cache has no purge API (htcacheclean works offline on the disk cache) |
| `cache_stale_on_error` | ✅ | first 200 origin=app2#1; after expiry with origin 503: 200 origin=app2#1 X-Cache=HIT from app.lab |
| `compress_gzip` | ✅ | Content-Encoding=gzip 345 bytes (65536 uncompressed) |
| `compress_brotli` | ✅ | Content-Encoding=br 98 bytes (65536 uncompressed) |
| `compress_zstd` | -- | no zstd output filter (mod_deflate = gzip, mod_brotli = br) |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab:18080' |
| `header_add_remove` | ✅ | X-Lab-Proxy=apache X-Powered-By=removed Server=lab-backend/1.0 |
| `request_id` | ✅ | 'aqb7z3J1sg6HPRY-VQeDMgAAAes' / 'aqb7z3J1sg6HPRY-VQeDMwAAAds' |
| `rate_limit` | -- | no request-rate limiting in the standard modules (mod_ratelimit is bandwidth only; mod_qos / mod_evasive are third-party) |
| `connection_limit` | -- | no per-client concurrency limit in the standard modules (mod_qos is third-party) |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | -- | JWT validation needs a third-party module (mod_auth_openidc, mod_authnz_jwt) |
| `forward_auth` | -- | no auth_request-style subrequest to an external authorizer in httpd core |
| `cors` | ✅ | 204 ACAO=* methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 502 after 2.01s |
| `fault_injection` | ✅ | 503 share=0.18 codes={200: 82, 503: 18} |
| `bandwidth_limit` | ✅ | 200 1048576 bytes in 2.01s (522 KB/s) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes', 'cache', 'duration_us', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'status', 'time', 'ua', 'uri'] |
| `metrics_prometheus` | ✅ | 200 83 samples e.g. apache_accesses_total 1130 |
| `admin_api` | ✅ | GET /server-status?auto -> 200 '127.0.0.1\nServerVersion: Apache/2.4.68 (Unix) OpenSSL/3.5.6\nServerMPM: event\nSer' |
| `tracing_otel` | -- | the OpenTelemetry Apache module (otel-webserver-module) is a separate build |
| `docker_label_discovery` | -- | no Docker provider |

### Apache Traffic Server 9.2 (`ats`)

ATS 9.2.3 from Ubuntu packages. remap.config is generated from remap.spec because ATS compares the request URL's port with the from-URL; NextHop strategies.yaml provides round-robin, weights and passive failover; header_rewrite does routing by header/query, method 405, IP lists, basic auth, body limit, fault injection, CORS and security headers; conf_remap sets per-remap timeouts, fq_pacing paces bandwidth, rate_limit.so caps concurrency, multiplexer mirrors, statichit serves a file, sslheaders exposes the client certificate, compress.so does gzip/brotli, sni.yaml gives mTLS and SNI tunnels, and stats_over_http/traffic_ctl are the admin surface. JSON access log through logging.yaml to stdout.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=http://app.lab/landing |
| `route_header` | -- | remap has no header/query conditions and header_rewrite's set-destination is overridden by the NextHop strategy that picks the origin |
| `route_query` | -- | see route_header |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | -- | strategies apply weights only to consistent_hash (same URL -> same host); there is no weighted round-robin in 9.2 |
| `lb_least_conn` | -- | NextHop strategies offer rr_strict / rr_ip / first_live / latched / consistent_hash - no least-connections |
| `lb_hash_header` | -- | consistent_hash keys are url / path / cache_key / hostname - a request header cannot be the key |
| `lb_sticky_cookie` | -- | no cookie stickiness (cookie_remap can route on cookies but does not set them) |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=22 |
| `lb_outlier_ejection` | -- | strategies failover retries 5xx on the next host (errors hidden) but markdown_codes did not take the flaky host out of rotation in 9.2.3 |
| `lb_active_health` | -- | ATS 9 strategies only do passive health (active origin checks arrived with ATS 10) |
| `lb_canary_split` | -- | no weighted round-robin (see lb_weighted); a canary needs the consistent-hash weights on varying keys |
| `lb_mirror` | ✅ | shadow received 20/20 |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app2': 1, 'app1': 1, 'app3': 1} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | -- | cleartext HTTP/2 is not supported on plain ports (h2 via ALPN only) |
| `http3` | -- | the Ubuntu build has no QUIC (experimental in 9.x, needs quiche) |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app1 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.20s |
| `grpc` | -- | no HTTP/2 to origins, so no gRPC proxying |
| `h2_upstream` | -- | ATS 9 speaks HTTP/1.1 to origins |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
| `proxy_protocol_upstream` | -- | no PROXY protocol towards origins in 9.2 |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:58464 |
| `tcp_l4` | -- | ATS is an HTTP proxy (sni.yaml tunnel_route is the only L4 feature) |
| `udp_l4` | -- | HTTP only |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 80C741128C710000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'Client-Ip': '10.77.0.1', 'X-Client-Cert-Issuer': 'CN = pxlab CA, O = pxlab', 'X-Client-Cert-Sub |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | -- | acme.so only serves challenge files; there is no ACME client |
| `cache_hit` | ✅ | origin app1#1 -> app1#1; X-Cache: miss -> hit-fresh age=0 |
| `cache_purge` | ✅ | purge -> 200; origin app2#1 -> app3#1 |
| `cache_stale_on_error` | ✅ | first 200 origin=app1#1; after expiry with origin 503: 200 origin=app1#1 X-Cache=hit-fresh |
| `compress_gzip` | ✅ | Content-Encoding=gzip 380 bytes (65536 uncompressed) |
| `compress_brotli` | -- | the Ubuntu compress.so is built without brotli (gzip only) |
| `compress_zstd` | -- | compress.so does gzip and brotli |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab:18080' |
| `header_add_remove` | ✅ | X-Lab-Proxy=ats X-Powered-By=removed Server=ats |
| `request_id` | ✅ | 'f6f8202f-6652-49c4-8155-7153cd506fac-193' / 'f6f8202f-6652-49c4-8155-7153cd506fac-194' |
| `rate_limit` | -- | rate_limit.so limits concurrency per remap, not requests per second per client |
| `connection_limit` | ✅ | codes={200: 3, 429: 9} |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (None) creds=200 |
| `jwt_auth` | -- | no JWT validation plugin (uri_signing.so signs URLs; tslua could do it) |
| `forward_auth` | -- | authproxy.so forwards the ORIGINAL path to the authorizer, which does not fit the lab's /auth service |
| `cors` | ✅ | 204 ACAO=* methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.86s |
| `fault_injection` | ✅ | 503 share=0.14 codes={503: 14, 200: 86} |
| `bandwidth_limit` | -- | fq_pacing.so needs the kernel fq qdisc (SO_MAX_PACING_RATE) on the interface, which a container does not have |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | -- | origin error bodies pass through; body_factory only styles ATS-generated errors |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes', 'cache', 'duration_ms', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'status', 'time', 'ua', 'upstream'] |
| `metrics_prometheus` | -- | stats_over_http.so exposes JSON at /_stats; Prometheus needs an exporter |
| `admin_api` | ✅ | rc=0 'proxy.process.http.current_active_client_connections 0' |
| `tracing_otel` | -- | no OpenTelemetry |
| `docker_label_discovery` | -- | no Docker provider |

### Caddy 2 (`caddy`)

Caddy 2 built with xcaddy: caddy-ratelimit, caddy-l4 (TCP/UDP/SNI passthrough), caddy-jwt, caddy-brotli and the Souin cache-handler (Caddy has no built-in cache). Automatic HTTPS stays on for acme.lab only (Pebble issuer, HTTP-01 on :80); every other site carries explicit certificates because Caddy would otherwise try to get Let's Encrypt certs for *.lab. h1/h2/h2c/h3 are enabled on the plain and TLS listeners; PROXY protocol is accepted on :8082 through a listener wrapper.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ✅ | slow share=0.02 {'slow': 6, 'app1': 150, 'app2': 144} |
| `lb_hash_header` | ✅ | u1 -> {'app3': 20}; 10 users -> {'app2': 9, 'app1': 15, 'app3': 6} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=916340cf243f672cd49155ba442cfd74ef69cbc40906c1aa6' first=app1 then={'app1': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=57 |
| `lb_outlier_ejection` | ✅ | first20={200: 17, 500: 3} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 3.1s; while unhealthy: {'app2': 15, 'app1': 15} app3 hits=0; re-admitted after 3.7s |
| `lb_canary_split` | ✅ | canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
| `lb_mirror` | -- | no request mirroring / shadowing in reverse_proxy |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app3': 1, 'app2': 1, 'app1': 1} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app3",\n "pool": "app",\n ' |
| `http3` | ✅ | proto=HTTP/3.0 status={'200': 677} errors=0 [] |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app1 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.20s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | ✅ | upstream proto=HTTP/2.0 |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'h2'} |
| `proxy_protocol_upstream` | ✅ | listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 0, 'dst_ip': '0.0.0.0', 'dst_port': 0, 'protocol': '0x11'} |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:36410 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:48328 headers=['Connection'] |
| `udp_l4` | ✅ | echo:app1:ping-a6f7d1 |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_128_GCM_SHA256 |
| `tls_legacy_refused` | ✅ | 80175DFDBC7A0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'CN=lab-client,O=pxlab'} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | ✅ | subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
| `cache_hit` | ✅ | origin app2#1 -> app2#1; Cache-Status: Souin; fwd=uri-miss; stored; key=GET-http-app.lab:18080-/cacheable/a6f7d1 -> Souin; hit; ttl=59; key=GET-http-app.lab:18080-/cacheable/a6f7d1; detail=DEFAULT age=1 |
| `cache_purge` | ✅ | purge -> 200; origin app3#1 -> app2#1 |
| `cache_stale_on_error` | ✅ | first 200 origin=app2#1; after expiry with origin 503: 200 origin=app2#1 Cache-Status=Souin; hit; ttl=-2; key=GET-http-app.lab:18080-/cacheable-short/a6f7d1; detail=DEFAULT; fwd=stale; fwd-status=503 |
| `compress_gzip` | ✅ | Content-Encoding=gzip 352 bytes (65536 uncompressed) |
| `compress_brotli` | ✅ | Content-Encoding=br 417 bytes (65536 uncompressed) |
| `compress_zstd` | ✅ | Content-Encoding=zstd 102 bytes (65536 uncompressed) |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
| `header_add_remove` | ✅ | X-Lab-Proxy=caddy X-Powered-By=removed Server=None |
| `request_id` | ✅ | '10942b52-3cc8-4cb8-882b-6220fda9920c' / '3b1d235e-dc0a-4447-b9a3-660ecc33a91d' |
| `rate_limit` | ✅ | codes={200: 10, 429: 30} |
| `connection_limit` | -- | no per-client concurrency limit (caddy-ratelimit is a request-rate limiter only) |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="restricted") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.01s |
| `fault_injection` | -- | no fault-injection primitive (a CEL matcher cannot draw random numbers); needs a plugin |
| `bandwidth_limit` | -- | no bandwidth/throughput limiting |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 '{"level":"info","ts":1789327334.420578,"msg":"using config from file","file":"/etc/caddy/Caddyfile"}\n{"level":"info","ts'; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes_read', 'duration', 'level', 'logger', 'msg', 'request', 'resp_headers', 'size', 'spanID', 'status', 'traceID', 'ts'] |
| `metrics_prometheus` | ✅ | 200 1093 samples e.g. caddy_admin_http_requests_total{code="200",handler="admin",method="POST",path="/ |
| `admin_api` | ✅ | GET /config/ -> 200 '{"admin":{"listen":"0.0.0.0:2019"},"apps":{"cache":{"Storers":null,"SurrogateKey' |
| `tracing_otel` | ✅ | jaeger traces for service 'caddy': 3 |
| `docker_label_discovery` | -- | caddy-docker-proxy (lucaslorentz) is a separate distribution that generates the Caddyfile from labels |

### Envoy 1.39 (`envoy`)

Official Envoy image with a bootstrap + file-based xDS (LDS/CDS/RDS files in a watched directory: bumping a version is the reload). lds.yaml is generated from lds.src.yaml because Envoy's YAML parser has no merge keys. Demonstrates ExtensionWithMatcher (ext_authz / basic_auth only where wanted), per-route filter configs (fault, local rate limit, RBAC, buffer, bandwidth limit, Lua error page, JWT), ring-hash cookies, outlier detection, mirroring, weighted clusters, h2c/TLS/PROXY-protocol upstreams, QUIC/HTTP/3, UDP proxy, OTel tracing and JSON access logs.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app1 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=http://app.lab/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 308 Location=https://redirect.lab:8443/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app2': 25, 'app1': 75} |
| `lb_least_conn` | ✅ | slow share=0.05 {'slow': 16, 'app2': 145, 'app1': 139} |
| `lb_hash_header` | ✅ | u1 -> {'app2': 20}; 10 users -> {'app1': 12, 'app2': 9, 'app3': 9} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky="0604085547a40599"; Max-Age=3600; Path=/; HttpOnl' first=app1 then={'app1': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=29 |
| `lb_outlier_ejection` | ✅ | first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 1.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 2.2s |
| `lb_canary_split` | ✅ | canary share=0.085 {'app1': 92, 'app2': 91, 'canary': 17} |
| `lb_mirror` | ✅ | shadow received 20/20 |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app3': 2, 'app2': 2, 'app1': 1} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
| `http3` | ✅ | proto=HTTP/3.0 status={'200': 933} errors=0 [] |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app2 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.21s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | ✅ | upstream proto=HTTP/2.0 |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.2', 'sni': 'backend.lab', 'alpn': 'http/1.1'} |
| `proxy_protocol_upstream` | ✅ | listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 48844, 'dst_ip': '10.77.0.2', 'dst_port': 8080, 'protocol': '0x11'} |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:53348 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:33056 headers=['Connection'] |
| `udp_l4` | ✅ | echo:app1:ping-a705b8 |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 8097564FCB7F0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client', 'X-Forwarded-Client-Cert': 'Hash=b5b0abe3c4cbc70e95 |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | -- | no ACME client in Envoy (certificates come from SDS / a control plane such as cert-manager) |
| `cache_hit` | -- | the HTTP cache filter is alpha; in 1.39 it makes its own internal upstream request that bypasses route-level header mutations, redirects and direct responses for every route (breaks 20+ probes), so it is left out |
| `cache_purge` | -- | no cache filter in use (and the alpha cache filter has no invalidation API) |
| `cache_stale_on_error` | -- | no cache filter in use (and the alpha cache filter has no stale-if-error mode) |
| `compress_gzip` | ✅ | Content-Encoding=gzip 690 bytes (65536 uncompressed) |
| `compress_brotli` | ✅ | Content-Encoding=br 100 bytes (65536 uncompressed) |
| `compress_zstd` | ✅ | Content-Encoding=zstd 99 bytes (65536 uncompressed) |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
| `header_add_remove` | ✅ | X-Lab-Proxy=envoy X-Powered-By=removed Server=envoy |
| `request_id` | ✅ | 'a1f68bef-f89f-4ad4-8957-93a09c62606e' / '66703245-e9c1-4846-8bab-d6b3975c2dd9' |
| `rate_limit` | ✅ | codes={200: 15, 429: 25} |
| `connection_limit` | -- | the connection_limit network filter is per listener; per-client concurrency needs the global rate-limit service |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="http://app.lab/basic") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 200 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.00s |
| `fault_injection` | ✅ | 503 share=0.17 codes={200: 83, 503: 17} |
| `bandwidth_limit` | ❌ | 200 1048576 bytes in 1.13s (928 KB/s) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['authority', 'bytes_sent', 'client', 'duration_ms', 'flags', 'method', 'path', 'protocol', 'request_id', 'status', 'time', 'ua'] |
| `metrics_prometheus` | ✅ | 200 6286 samples e.g. envoy_bw_http_bandwidth_limit_request_allowed_total_size{} 0 |
| `admin_api` | ✅ | GET /server_info -> 200 '{\n "version": "b579d07d3ad7ee11d32b105e91a5a39ad24718d7/1.39.1/Clean/RELEASE/Bor' |
| `tracing_otel` | ✅ | jaeger traces for service 'envoy': 5 |
| `docker_label_discovery` | -- | no Docker provider; endpoints come from xDS (or STRICT_DNS as here) |

### HAProxy 3.4 (`haproxy`)

Official HAProxy LTS image (3.4.4): QUIC/HTTP/3 through OpenSSL 3.5's native QUIC API, ACME client (experimental, crt-store starts with a temporary key pair until Pebble issues the certificate), Lua forward-auth through the internal httpclient, jwt_verify for JWTs, stick-tables for rate/connection limits, bwlim filter, built-in cache and Prometheus exporter. Master-worker mode makes `kill -USR2 1` a seamless reload. No UDP, no mirroring, no purge, gzip only.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab:18080/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ✅ | slow share=0.03 {'slow': 8, 'app2': 147, 'app1': 145} |
| `lb_hash_header` | ✅ | u1 -> {'app3': 20}; 10 users -> {'app1': 15, 'app2': 9, 'app3': 6} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=a1; path=/; HttpOnly' first=app1 then={'app1': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=3 |
| `lb_outlier_ejection` | ✅ | first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 2.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.1s |
| `lb_canary_split` | ✅ | canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
| `lb_mirror` | -- | no native request mirroring; use tcp-level tee or SPOE + an external agent |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app2': 2, 'app1': 2, 'app3': 1} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
| `http3` | ✅ | proto=HTTP/3.0 status={'200': 1025} errors=0 [] |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app2 |
| `sse_streaming` | ✅ | events=5 first=0.21s total=1.20s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | ✅ | upstream proto=HTTP/2.0 |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'http/1.1'} |
| `proxy_protocol_upstream` | ✅ | listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 33228, 'dst_ip': '10.77.0.2', 'dst_port': 8080, 'protocol': '0x11'} |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:33726 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:49882 headers=['Connection'] |
| `udp_l4` | -- | HAProxy proxies TCP and QUIC only; there is no generic UDP proxying (only syslog/DNS forwarding) |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 80070F3C2A780000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'lab-client', 'X-Client-Cert-Verify': '0'} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | ✅ | subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
| `cache_hit` | ✅ | origin app1#1 -> app1#1; X-Cache: MISS -> HIT age=0 |
| `cache_purge` | -- | the built-in cache is a small-object accelerator without an invalidation API; entries expire by max-age (or reload) |
| `cache_stale_on_error` | -- | the cache has no stale-if-error / grace mode; an expired entry is refetched and the origin's 503 is returned |
| `compress_gzip` | ✅ | Content-Encoding=gzip 1544 bytes (65536 uncompressed) |
| `compress_brotli` | -- | compression uses libslz (gzip/deflate only); no brotli or zstd support |
| `compress_zstd` | -- | no zstd (slz only) |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='proto=http;host="app.lab:18080";for=10.77.0.1' |
| `header_add_remove` | ✅ | X-Lab-Proxy=haproxy X-Powered-By=removed Server=haproxy |
| `request_id` | ✅ | '0A4D0001:81AE_0A4D0002:1F90_6AA6F689_07EA:0008' / '0A4D0001:81AE_0A4D0002:1F90_6AA6F689_07EB:0008' |
| `rate_limit` | ✅ | codes={200: 10, 429: 30} |
| `connection_limit` | ✅ | codes={200: 3, 429: 9} |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.00s |
| `fault_injection` | ✅ | 503 share=0.24 codes={200: 76, 503: 24} |
| `bandwidth_limit` | ✅ | 200 1048576 bytes in 2.10s (499 KB/s) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['backend', 'bytes', 'client_ip', 'frontend', 'method', 'proto', 'request_id', 'server', 'ssl', 'status', 'time', 'time_ms'] |
| `metrics_prometheus` | ✅ | 200 4525 samples e.g. haproxy_process_nbthread 4 |
| `admin_api` | ✅ | GET /stats -> 200 '<!DOCTYPE html>\n<html lang="en"><head><title>Statistics Report for HAProxy</titl' |
| `tracing_otel` | -- | no OpenTelemetry exporter in the official build (the OpenTracing filter needs a separate addon build) |
| `docker_label_discovery` | -- | no Docker provider; the Data Plane API / Ingress Controller do this in other setups |

### Kong Gateway 3.9 (`kong`)

Kong Gateway OSS 3.9 in DB-less mode with the expressions router. Upstreams demonstrate round-robin / weighted / least-connections / consistent-hashing (header, cookie stickiness), active + passive health checks and retries; bundled plugins cover rate limiting, IP restriction, basic auth, JWT, CORS, request/response transformers, proxy-cache (+ admin purge), request size limiting, correlation-id, prometheus, opentelemetry and acme (Pebble); pre/post-function serverless plugins do redirects, 405, fault injection, static files and the custom error page. Stream routes give TCP, UDP and TLS passthrough.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app1 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app2': 10, 'app3': 10, 'app1': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ✅ | slow share=0.05 {'app1': 139, 'app2': 145, 'slow': 16} |
| `lb_hash_header` | ✅ | u1 -> {'app2': 20}; 10 users -> {'app1': 9, 'app3': 12, 'app2': 9} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=f1c67503-dc16-43e8-b915-9fab0d301660; Path=/; Sam' first=app2 then={'app2': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=5 |
| `lb_outlier_ejection` | ✅ | first20={200: 17, 500: 3} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 2.1s; while unhealthy: {'app2': 15, 'app1': 15} app3 hits=0; re-admitted after 1.6s |
| `lb_canary_split` | ✅ | canary share=0.100 {'app1': 60, 'app3': 60, 'app2': 60, 'canary': 20} |
| `lb_mirror` | -- | no traffic mirroring in Kong OSS |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app1': 2, 'app3': 2, 'app2': 1} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
| `http3` | -- | no HTTP/3 in Kong Gateway 3.9 OSS |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app2 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.21s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | -- | HTTP/2 to upstreams only for gRPC services (protocol grpc/grpcs) |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
| `proxy_protocol_upstream` | -- | Kong cannot send PROXY protocol to upstreams |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:56778 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:48750 headers=['Connection'] |
| `udp_l4` | ✅ | echo:app1:ping-a6fff2 |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 806756E04D7D0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | -- | mtls-auth is a Kong Enterprise plugin; nginx-level ssl_verify_client would apply to every TLS listener |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | ✅ | subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
| `cache_hit` | ✅ | origin app2#1 -> app2#1; X-Cache-Status: Miss -> Hit age=0 |
| `cache_purge` | ✅ | purge -> 204; origin app1#1 -> app3#1 |
| `cache_stale_on_error` | -- | proxy-cache has no stale-if-error mode |
| `compress_gzip` | ✅ | Content-Encoding=gzip 611 bytes (65536 uncompressed) |
| `compress_brotli` | -- | gzip only (nginx gzip injected through KONG_NGINX_PROXY_GZIP) |
| `compress_zstd` | -- | gzip only |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
| `header_add_remove` | ✅ | X-Lab-Proxy=kong X-Powered-By=removed Server=lab-backend/1.0 |
| `request_id` | ✅ | 'b349ff86-f185-4cd5-a062-5046e908601f' / '41ae2ab5-ab09-4063-9f0e-b22c4304bda3' |
| `rate_limit` | ✅ | codes={200: 10, 429: 30} |
| `connection_limit` | -- | no per-client concurrency limit in OSS (rate-limiting is per request) |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | -- | no forward-auth plugin in Kong OSS (openid-connect is Enterprise; write a pre-function with lua-resty-http) |
| `cors` | ✅ | 200 ACAO=* methods=GET,POST,PUT,DELETE,OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.01s |
| `fault_injection` | ✅ | 503 share=0.28 codes={200: 72, 503: 28} |
| `bandwidth_limit` | -- | no bandwidth limiting (response-ratelimiting counts requests) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'status', 'time', 'ua', 'upstream', 'upstream_time'] |
| `metrics_prometheus` | ✅ | 200 1972 samples e.g. kong_bandwidth_bytes{service="app",route="a",direction="egress",workspace="defau |
| `admin_api` | ✅ | GET /status -> 200 '{"server":{"connections_active":15,"total_requests":1154,"connections_reading":0' |
| `tracing_otel` | ✅ | jaeger traces for service 'kong': 5 |
| `docker_label_discovery` | -- | no Docker provider (Kong Ingress Controller does this on Kubernetes) |

### NGINX 1.29 (`nginx`)

Open-source nginx from the official `-otel` image, which also ships the njs, ACME (1.29 preview) and OpenTelemetry dynamic modules. Sticky sessions are done the OSS way (cookie = upstream address, map -> proxy_pass variable) because `sticky` is Plus-only; JWT is verified by an njs handler behind auth_request; PURGE is a refreshing subrequest (real purge is Plus / ngx_cache_purge); active health checks, brotli/zstd and HTTP/2 to non-gRPC upstreams are Plus / third-party features and are declared unsupported.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=http://app.lab:8080/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ✅ | slow share=0.03 {'app1': 145, 'app2': 145, 'slow': 10} |
| `lb_hash_header` | ✅ | u1 -> {'app3': 20}; 10 users -> {'app2': 12, 'app1': 9, 'app3': 9} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=10.77.0.13:8080; Path=/; HttpOnly' first=app3 then={'app3': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=3 |
| `lb_outlier_ejection` | ✅ | first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | -- | active health checks (health_check directive) are NGINX Plus only; open source is passive (max_fails / fail_timeout / proxy_next_upstream) - app3 keeps receiving traffic while its /healthz says 503 |
| `lb_canary_split` | ✅ | canary share=0.080 {'app1': 62, 'app2': 61, 'app3': 61, 'canary': 16} |
| `lb_mirror` | ✅ | shadow received 20/20 |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app1': 1, 'app2': 1, 'app3': 1} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app2",\n "pool": "app",\n ' |
| `http3` | ✅ | proto=HTTP/3.0 status={'200': 1170} errors=0 [] |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app3 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.21s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | -- | proxy_pass speaks HTTP/1.x to upstreams only; HTTP/2 towards upstreams exists solely for gRPC (grpc_pass) |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': ''} |
| `proxy_protocol_upstream` | -- | PROXY protocol towards upstreams is a stream (L4) feature (proxy_protocol on); for HTTP upstreams nginx sends X-Forwarded-For instead |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:46896 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:46592 headers=['Connection'] |
| `udp_l4` | ✅ | echo:app1:ping-a6f52b |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 8027B05DE8780000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: status 400; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client', 'X-Client-Cert-Verify': 'SUCCESS'} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | ✅ | subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
| `cache_hit` | ✅ | origin app2#1 -> app2#1; X-Cache: MISS -> HIT age=None |
| `cache_purge` | ✅ | purge -> 200; origin app3#1 -> app1#1 |
| `cache_stale_on_error` | ✅ | first 200 origin=app2#1; after expiry with origin 503: 200 origin=app2#1 X-Cache=STALE |
| `compress_gzip` | ✅ | Content-Encoding=gzip 345 bytes (65536 uncompressed) |
| `compress_brotli` | -- | ngx_brotli is a third-party module, not built into the official image (NGINX Plus ships it); build your own image to add it |
| `compress_zstd` | -- | zstd-nginx-module is third-party, not in the official image |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
| `header_add_remove` | ✅ | X-Lab-Proxy=nginx X-Powered-By=removed Server=nginx |
| `request_id` | ✅ | '84e511bc7542dc70105d0fdc7fab0c4c' / '1b17a8960320ea4d7220e053baf4bc08' |
| `rate_limit` | ✅ | codes={200: 6, 429: 34} |
| `connection_limit` | ✅ | codes={200: 3, 429: 9} |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.00s |
| `fault_injection` | ✅ | 503 share=0.12 codes={200: 88, 503: 12} |
| `bandwidth_limit` | ✅ | 200 1048576 bytes in 2.00s (523 KB/s) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 '2026/09/13 19:10:53 [notice] 275#275: js vm init njs: 00006483E75BF280\n2026/09/13 19:10:53 [notice] 275#275: signal proc'; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes', 'cache', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'ssl', 'status', 'time', 'ua'] |
| `metrics_prometheus` | ✅ | 200 57 samples e.g. go_gc_duration_seconds{quantile="0"} 0 |
| `admin_api` | ✅ | GET /nginx_status -> 200 'Active connections: 3 \nserver accepts handled requests\n 66 66 2256 \nReading: 0 W' |
| `tracing_otel` | ✅ | jaeger traces for service 'nginx': 3 |
| `docker_label_discovery` | -- | nginx has no Docker/label provider; nginx-proxy (docker-gen) or NGINX Plus' API are separate projects |

### OpenResty 1.27 (`openresty`)

OpenResty 1.27.1.2 (alpine-fat) with lua-resty-jwt, nginx-lua-prometheus, lua-resty-acme (+http/openssl) from opm. Same nginx core config as stacks/nginx, but JWT, rate/connection limits, forward auth, fault injection, a real cache purge (os.remove of the cache file), ACME (certificate requested from Pebble on the first TLS handshake for acme.lab) and Prometheus metrics are Lua. HTTP/3, stream L4 and sticky/hash balancing are nginx-native.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=http://app.lab:8080/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ✅ | slow share=0.04 {'app1': 146, 'app2': 143, 'slow': 11} |
| `lb_hash_header` | ✅ | u1 -> {'app3': 20}; 10 users -> {'app2': 12, 'app1': 9, 'app3': 9} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=10.77.0.13:8080; Path=/; HttpOnly' first=app3 then={'app3': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=3 |
| `lb_outlier_ejection` | ✅ | first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | -- | active health checks need lua-resty-upstream-healthcheck (opm) driving the balancer; the plain upstream is passive like nginx |
| `lb_canary_split` | ✅ | canary share=0.090 {'app1': 61, 'app2': 61, 'app3': 60, 'canary': 18} |
| `lb_mirror` | ✅ | shadow received 20/20 |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app1': 2, 'app2': 1, 'app3': 2} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app3",\n "pool": "app",\n ' |
| `http3` | ✅ | proto=HTTP/3.0 status={'200': 1097} errors=0 [] |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app1 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.20s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | -- | proxy_pass is HTTP/1.x only (h2c upstreams only for gRPC via grpc_pass), same as nginx |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': ''} |
| `proxy_protocol_upstream` | -- | PROXY protocol towards upstreams is a stream-module feature only, same as nginx |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:40162 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:58548 headers=['Connection'] |
| `udp_l4` | ✅ | echo:app1:ping-a6fe99 |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 80079F15AC7C0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: status 400; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client'} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | ✅ | subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
| `cache_hit` | ✅ | origin app3#1 -> app3#1; X-Cache: MISS -> HIT age=None |
| `cache_purge` | ✅ | purge -> 200; origin app1#1 -> app2#1 |
| `cache_stale_on_error` | ✅ | first 200 origin=app3#1; after expiry with origin 503: 200 origin=app3#1 X-Cache=HIT |
| `compress_gzip` | ✅ | Content-Encoding=gzip 345 bytes (65536 uncompressed) |
| `compress_brotli` | -- | no brotli module in the OpenResty image |
| `compress_zstd` | -- | no zstd module |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
| `header_add_remove` | ✅ | X-Lab-Proxy=openresty X-Powered-By=removed Server=openresty |
| `request_id` | ✅ | 'c357e9acbafaa6c23506984afd08c503' / '70e64010be7764a1b407afb5eb97947d' |
| `rate_limit` | ✅ | codes={200: 6, 429: 34} |
| `connection_limit` | ✅ | codes={200: 3, 429: 9} |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.00s |
| `fault_injection` | ✅ | 503 share=0.25 codes={200: 75, 503: 25} |
| `bandwidth_limit` | ✅ | 200 1048576 bytes in 2.00s (524 KB/s) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 '2026/09/13 19:51:07 [notice] 81#81: signal process started'; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes', 'cache', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'ssl', 'status', 'time', 'ua'] |
| `metrics_prometheus` | ✅ | 200 429 samples e.g. nginx_http_connections{state="active"} 2 |
| `admin_api` | ✅ | GET /nginx_status -> 200 'Active connections: 2 \nserver accepts handled requests\n 65 65 2183 \nReading: 0 W' |
| `tracing_otel` | -- | no OpenTelemetry module in the OpenResty image (opentelemetry-lua is a separate integration) |
| `docker_label_discovery` | -- | no Docker provider |

### Pingora (Rust, custom) (`pingora`)

A ~700-line Rust proxy on Pingora 0.9 (Cloudflare's framework): ProxyHttp hooks implement host/path routing, round-robin / weighted / ketama hashing / cookie stickiness, HTTP health checks, retries on connect failure, outlier ejection, h2c and verified-TLS upstreams, gRPC, rate and concurrency limits (pingora-limits), JWT (jsonwebtoken), basic auth, IP lists, fault injection, per-route timeouts, response cache (pingora-cache MemCache), compression, mTLS, SNI certificate callback, a static file, a custom error page, JSON access log, Prometheus metrics, a status API and a raw TCP proxy app. Zero-downtime upgrade via the framework's socket hand-off. What is missing is missing from the code, not from the framework's limits (mostly).

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | -- | pingora-load-balancing ships round-robin / random / consistent-hash selection; least-connections would be a custom BackendSelection |
| `lb_hash_header` | ✅ | u1 -> {'app1': 20}; 10 users -> {'app2': 15, 'app1': 6, 'app3': 9} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=app3; Path=/; HttpOnly' first=app3 then={'app3': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=3 |
| `lb_outlier_ejection` | ✅ | first20={200: 17, 500: 3} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 2.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 2.1s |
| `lb_canary_split` | ✅ | canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
| `lb_mirror` | -- | no mirroring in the framework (would be a second upstream request written by hand) |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app2': 1, 'app1': 1, 'app3': 2} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app2",\n "pool": "app",\n ' |
| `http3` | -- | no HTTP/3 in Pingora |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app2 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.20s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | ✅ | upstream proto=HTTP/2.0 |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'http/1.1'} |
| `proxy_protocol_upstream` | -- | no PROXY protocol towards upstreams |
| `proxy_protocol_accept` | -- | no PROXY protocol on listeners |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:53200 headers=['Connection'] |
| `udp_l4` | -- | Pingora is TCP/HTTP only |
| `tls_passthrough_sni` | -- | the L4 app in this proxy copies bytes; SNI parsing for passthrough is not implemented |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 800798FF1F7F0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Org': 'pxlab'} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | -- | no ACME client (certificates come from files / callbacks) |
| `cache_hit` | ✅ | origin app1#1 -> app1#1; X-Cache: MISS -> HIT age=0 |
| `cache_purge` | -- | pingora-cache serves PURGE only for storages implementing purge; MemCache does in principle but the lab keeps it out of scope |
| `cache_stale_on_error` | -- | stale-if-error is wired through should_serve_stale(); the in-memory cache expires objects before the lab's 2 s window |
| `compress_gzip` | ✅ | Content-Encoding=gzip 609 bytes (65536 uncompressed) |
| `compress_brotli` | -- | pingora's compression module in this build negotiates gzip/zstd (brotli support is feature-gated) |
| `compress_zstd` | ✅ | Content-Encoding=zstd 99 bytes (65536 uncompressed) |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
| `header_add_remove` | ✅ | X-Lab-Proxy=pingora X-Powered-By=removed Server=pingora |
| `request_id` | ✅ | 'cf72452e-6150-4d0d-9f3a-5a9dce0d2eb6' / '23924bf1-8cce-4be3-8d5c-239db894bda1' |
| `rate_limit` | ✅ | codes={200: 10, 429: 30} |
| `connection_limit` | ✅ | codes={200: 3, 429: 9} |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | -- | no built-in subrequest to an authorizer (would be a hand-written upstream call) |
| `cors` | ✅ | 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 502 after 2.00s |
| `fault_injection` | ✅ | 503 share=0.19 codes={200: 81, 503: 19} |
| `bandwidth_limit` | -- | no built-in bandwidth limiting (body filters are synchronous) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['cache', 'duration_ms', 'error', 'host', 'method', 'remote_addr', 'status', 'time', 'tries', 'upstream', 'uri'] |
| `metrics_prometheus` | ✅ | 200 261 samples e.g. pingora_http_request_duration_seconds_bucket{host="",le="0.005"} 3 |
| `admin_api` | ✅ | GET / -> 200 '{"outliers":[],"proxy":"pingora-lab","requests_seen":0,"uptime_s":2,"version":"0' |
| `tracing_otel` | -- | no OpenTelemetry integration in this binary |
| `docker_label_discovery` | -- | no Docker provider |

### Traefik v3 (`traefik`)

Official Traefik v3 image with the file provider (watched: edits are the reload) and the Docker provider (whoami.lab is discovered from labels). HTTP/3 on :8443, ACME against Pebble (LEGO_CA_CERTIFICATES), mirroring, weighted traffic split, p2c balancing, sticky cookies, forwardAuth, mTLS with passTLSClientCert, TCP/UDP/SNI-passthrough routers. No cache, no JWT, no request-id, no Forwarded header, no file serving in the open-source edition.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app3 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app2': 11, 'app1': 10, 'app3': 9} |
| `lb_weighted` | ✅ | app1 share=0.75 {'app1': 75, 'app2': 25} |
| `lb_least_conn` | ✅ | slow share=0.03 {'app1': 161, 'slow': 8, 'app2': 131} |
| `lb_hash_header` | -- | no hash-based balancing (wrr / p2c / sticky cookies only) |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=682614ad3435cf07; Path=/; HttpOnly' first=app1 then={'app1': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=77 |
| `lb_outlier_ejection` | -- | no passive per-server ejection: the circuitBreaker middleware opens for the whole service, health checks probe /healthz only |
| `lb_active_health` | ✅ | ejected after 1.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.1s |
| `lb_canary_split` | ✅ | canary share=0.100 {'app2': 88, 'app1': 87, 'canary': 20, 'app3': 5} |
| `lb_mirror` | ✅ | shadow received 20/20 |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app1': 2, 'app2': 2, 'app3': 2} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
| `http3` | ✅ | proto=HTTP/3.0 status={'200': 655} errors=0 [] |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app1 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.21s |
| `grpc` | ✅ | tls:8443: SERVING |
| `h2_upstream` | ✅ | upstream proto=HTTP/2.0 |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'h2'} |
| `proxy_protocol_upstream` | -- | PROXY protocol towards upstreams exists only for TCP services (tcp.serversTransports.proxyProtocol), not HTTP |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:47854 |
| `tcp_l4` | ✅ | instance=app1 remote_addr=10.77.0.2:47866 headers=['Connection'] |
| `udp_l4` | ✅ | echo:app1:ping-a6f92e |
| `tls_passthrough_sni` | ✅ | subject=CN = backend.lab, O = pxlab TLSv1.3 |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_128_GCM_SHA256 |
| `tls_legacy_refused` | ✅ | 8077E52C0B7B0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70
Protocol: TLSv1.1
    Protocol  : TLSv1.1 |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Forwarded-Tls-Client-Cert-Info': 'Subject%3D%22O%3Dpxlab%2CCN%3Dlab-client%22%2CSubject%3D%22 |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | ✅ | subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
| `cache_hit` | -- | no HTTP cache in Traefik OSS (Traefik Enterprise / plugins) |
| `cache_purge` | -- | no cache |
| `cache_stale_on_error` | -- | no cache |
| `compress_gzip` | ✅ | Content-Encoding=gzip 352 bytes (65536 uncompressed) |
| `compress_brotli` | ✅ | Content-Encoding=br 94 bytes (65536 uncompressed) |
| `compress_zstd` | ✅ | Content-Encoding=zstd 102 bytes (65536 uncompressed) |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | -- | Traefik sets X-Forwarded-* only; no RFC 7239 Forwarded generation |
| `header_add_remove` | ✅ | X-Lab-Proxy=traefik X-Powered-By=removed Server=lab-backend/1.0 |
| `request_id` | -- | no request-id generation (a plugin or the upstream has to do it) |
| `rate_limit` | ✅ | codes={200: 6, 429: 34} |
| `connection_limit` | ✅ | codes={200: 3, 429: 9} |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | -- | no JWT validation in OSS (ForwardAuth, a plugin such as traefik-jwt-plugin, or Traefik Enterprise) |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 200 ACAO=* methods=GET,POST,PUT,DELETE,OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 504 after 2.00s |
| `fault_injection` | -- | no fault-injection middleware |
| `bandwidth_limit` | -- | no bandwidth limiting (rateLimit is per request) |
| `static_files` | -- | Traefik has no file server; static content must come from an upstream |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 ''; then 200 |
| `access_log_json` | ✅ | json keys: ['ClientAddr', 'ClientHost', 'ClientPort', 'ClientUsername', 'DownstreamContentSize', 'DownstreamStatus', 'Duration', 'OriginContentSize', 'OriginDuration', 'OriginStatus', 'Overhead', 'RequestAddr'] |
| `metrics_prometheus` | ✅ | 200 418 samples e.g. go_gc_duration_seconds{quantile="0"} 1.9343e-05 |
| `admin_api` | ✅ | GET /api/rawdata -> 200 '{"routers":{"a-tls@file":{"entryPoints":["websecure"],"middlewares":["common@fil' |
| `tracing_otel` | ✅ | jaeger traces for service 'traefik': 1 |
| `docker_label_discovery` | ✅ | 200 'Hostname: 000d81002bc0\nIP: 127.0.0.1\nIP: ::1\nIP: 10.77.0.32\n' |

### Varnish 8 + hitch (`varnish`)

Official varnish:8.0 image (ships vmod_vsthrottle, digest, reqwest, saintmode, fileserver, uuid, cookie ...) behind hitch for TLS (PROXY v2 between them, h2 via ALPN, mTLS on :8444). VCL implements routing, shard hashing, cookie stickiness, saintmode outlier ejection, retries, grace (stale-on-error), PURGE, vsthrottle rate limiting, JWT verification with vmod_digest, forward auth and a TLS/h2 backend with vmod_reqwest, static files with vmod_fileserver and custom error pages. varnishncsa and a Prometheus exporter run as sidecars on the shared VSM directory; varnishreload swaps VCL without dropping connections. No HTTP/3, gRPC, L4, ACME or brotli.

| capability | result | detail |
|---|:---:|---|
| `route_host` | ✅ | a.lab -> app2 (X-Route=a), b.lab -> b1 |
| `route_path_prefix` | ✅ | upstream path=/hello query=x=1 X-Route=api |
| `route_path_regex` | ✅ | path=/v2/things X-Route=versioned |
| `route_rewrite` | ✅ | upstream path=/new/thing X-Route=rewritten |
| `route_redirect` | ✅ | 301 Location=/landing |
| `route_header` | ✅ | instance=canary |
| `route_query` | ✅ | instance=canary |
| `route_method` | ✅ | DELETE -> 405 (x-instance=None) |
| `redirect_https` | ✅ | 301 Location=https://redirect.lab/x?q=1 |
| `lb_round_robin` | ✅ | {'app3': 10, 'app1': 10, 'app2': 10} |
| `lb_weighted` | ✅ | app1 share=0.73 {'app1': 73, 'app2': 27} |
| `lb_least_conn` | -- | vmod_directors has round_robin / random / fallback / hash / shard - no least-connections director |
| `lb_hash_header` | ✅ | u1 -> {'app2': 20}; 10 users -> {'app1': 18, 'app3': 3, 'app2': 9} |
| `lb_sticky_cookie` | ✅ | cookie='lab_sticky=app3; Path=/; HttpOnly' first=app3 then={'app3': 12} |
| `lb_retry_dead_member` | ✅ | codes={200: 30} max_ms=4 |
| `lb_outlier_ejection` | ✅ | first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
| `lb_active_health` | ✅ | ejected after 2.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.7s |
| `lb_canary_split` | ✅ | canary share=0.090 {'app1': 68, 'app2': 52, 'canary': 18, 'app3': 62} |
| `lb_mirror` | -- | no request mirroring |
| `lb_upstream_keepalive` | ✅ | new upstream connections for 60 requests: {'app1': 2, 'app3': 2, 'app2': 2} |
| `http2_tls` | ✅ | HTTP/2 200 upstream proto=HTTP/1.1 |
| `h2c_frontend` | ✅ | status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
| `http3` | -- | no HTTP/3 in Varnish Cache or hitch (Varnish Enterprise / a QUIC terminator in front) |
| `websocket` | ✅ | text echo='hello' binary 4096=4096 instance=app1 |
| `sse_streaming` | ✅ | events=5 first=0.0s total=1.21s |
| `grpc` | -- | no gRPC: Varnish cannot proxy HTTP/2 with trailers to backends |
| `h2_upstream` | -- | Varnish speaks HTTP/1.1 to backends; h2 is only available via vmod_reqwest over TLS (used for tls.lab) |
| `tls_upstream` | ✅ | listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
| `proxy_protocol_upstream` | ✅ | listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 42730, 'dst_ip': '10.77.0.2', 'dst_port': 8080, 'protocol': '0x11'} |
| `proxy_protocol_accept` | ✅ | X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:36512 |
| `tcp_l4` | -- | Varnish is HTTP-only |
| `udp_l4` | -- | Varnish is HTTP-only |
| `tls_passthrough_sni` | -- | no L4 passthrough (hitch terminates TLS) |
| `tls_termination` | ✅ | 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
| `tls13` | ✅ | TLSv1.3 TLS_AES_256_GCM_SHA384 |
| `tls_legacy_refused` | ✅ | 8047BA5AB87A0000:error:8000006F:system library:BIO_connect:Connection refused:../crypto/bio/bio_sock2.c:183:calling connect()
8047BA5AB87A0000:error:10000067:BIO routines:BIO_connect:connect error:../ |
| `mtls_client_cert` | ✅ | without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {} |
| `sni_multi_cert` | ✅ | app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
| `acme_auto_cert` | -- | hitch has no ACME client (use certbot/lego and reload hitch) |
| `cache_hit` | ✅ | origin app3#1 -> app3#1; X-Cache: MISS -> HIT age=0 |
| `cache_purge` | ✅ | purge -> 200; origin app1#1 -> app2#1 |
| `cache_stale_on_error` | ✅ | first 200 origin=app3#1; after expiry with origin 503: 200 origin=app3#1 X-Cache=HIT |
| `compress_gzip` | ✅ | Content-Encoding=gzip 345 bytes (65536 uncompressed) |
| `compress_brotli` | -- | Varnish compresses with gzip only |
| `compress_zstd` | -- | gzip only |
| `xff_headers` | ✅ | XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
| `forwarded_rfc7239` | ✅ | Forwarded='for=10.77.0.1;proto=http;host=app.lab:18080' |
| `header_add_remove` | ✅ | X-Lab-Proxy=varnish X-Powered-By=removed Server=varnish |
| `request_id` | ✅ | 'cea3123b-6e1d-4856-bdab-f318f8bd7400' / '5d5eb2de-1df5-4e00-88a3-2df22975112e' |
| `rate_limit` | ✅ | codes={200: 10, 429: 30} |
| `connection_limit` | -- | no per-client concurrency limit (vsthrottle is a request-rate limiter) |
| `ip_allow_deny` | ✅ | /allowed=200 /denied=403 |
| `basic_auth` | ✅ | no creds=401 (Basic realm="pxlab") creds=200 |
| `jwt_auth` | ✅ | none=401 valid=200 bad-sig=401 |
| `forward_auth` | ✅ | none=401 token=200 X-Auth-User=alice |
| `cors` | ✅ | 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
| `security_headers` | ✅ | {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
| `body_size_limit` | ✅ | 2MiB=413 100KiB=200 |
| `upstream_timeout` | ✅ | 503 after 2.00s |
| `fault_injection` | ✅ | 503 share=0.25 codes={200: 75, 503: 25} |
| `bandwidth_limit` | -- | no bandwidth limiting in Varnish Cache (Enterprise has vmod_tcp/..) |
| `static_files` | ✅ | 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
| `custom_error_page` | ✅ | 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
| `hot_reload` | ✅ | reload rc=0 "VCL 'reload_20260913_194547_507' compiled\nVCL 'reload_20260913_194547_507' now active"; then 200 |
| `access_log_json` | ✅ | json keys: ['bytes', 'duration_s', 'handling', 'host', 'method', 'remote_addr', 'request_id', 'status', 'time', 'ua', 'uri'] |
| `metrics_prometheus` | ✅ | 200 552 samples e.g. varnish_backend_bereq_bodybytes{backend="app1",server="unknown"} 0 |
| `admin_api` | ✅ | rc=0 'Child in state running' |
| `tracing_otel` | -- | no OpenTelemetry in Varnish Cache |
| `docker_label_discovery` | -- | no Docker provider |
