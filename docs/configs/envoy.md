# Envoy 1.39 - config walkthrough

Stack: `stacks/envoy/` - image `envoyproxy/envoy:v1.39-latest`. Envoy is configured through **xDS**; here the xDS
resources are files in a watched directory, which is the closest thing to "edit a config file" Envoy offers:

| file | resource | how it is applied |
|---|---|---|
| `envoy.yaml` | bootstrap: node, admin (:9101), `dynamic_resources` (LDS/CDS via `path_config_source` + `watched_directory`), overload manager | restart |
| `lds.src.yaml` -> `gen.py` -> `lds.yaml` | listeners (LDS); the HCM/filter chain is written once and reused through YAML anchors and merge keys, which Envoy's own yaml-cpp parser does not support - `gen.py` expands them (`pre_up` in lab.yaml) | file watch (write + rename) |
| `cds.yaml` | clusters (CDS) | file watch |
| `rds.yaml` | routes (RDS), referenced by every HCM | file watch - bumping `version_info` is the lab's reload |

Read this next to those files.

## Listeners (`lds.src.yaml`)

Every HTTP listener uses the same `x-hcm-common` anchor:

```yaml
codec_type: AUTO                 # h1, h2 by ALPN, and h2c prior knowledge on plain ports
use_remote_address: true         # XFF = the real peer (xff_num_trusted_hops: 0)
generate_request_id: true
preserve_external_request_id: true
strip_any_host_port: true
upgrade_configs:                 # WebSocket upgrades get a router-only filter chain
  - upgrade_type: websocket
    filters: [router]
tracing: *tracing                # OpenTelemetry -> cluster jaeger (client_sampling 100, random 0.1 %)
access_log: *access_log          # JSON to stdout
rds: *rds
http_filters: *http_filters
```

| listener | port | specifics |
|---|---|---|
| `http` | 8080 (+80 via `additional_addresses`) | plain |
| `https` | 8443 | `tls_inspector`; filter chain `server_names: [b.lab]` with b.lab's cert, default chain with app.lab's (`x-tls-app`), ALPN h2/http1.1 |
| `http3` | 8443/udp | `udp_listener_config.quic_options`, `QuicDownstreamTransport`, `codec_type: HTTP3` |
| `mtls` | 8444 | `require_client_certificate: true`, `validation_context.trusted_ca`, HCM `forward_client_cert_details: SANITIZE_SET` + `set_current_client_cert_details.subject` -> `x-forwarded-client-cert`; the route adds `X-Client-Cert-CN: %DOWNSTREAM_PEER_SUBJECT%` |
| `pp` | 8082 | `envoy.filters.listener.proxy_protocol` listener filter |
| `passthrough` | 8445 | `tls_inspector` + `tcp_proxy` per `server_names` (no TLS termination) |
| `tcp` | 9000 | `tcp_proxy` -> cluster `app1_tcp` |
| `udp` | 9001/udp | `udp_proxy` listener filter, `on_no_match` route -> `app1_udp` |
| `metrics` | 9100 | tiny HCM that rewrites `/metrics` to the admin's `/stats/prometheus` (cluster `admin` = 127.0.0.1:9101) |

### The HTTP filter chain (`x-http-filters`)

Order matters; each filter is configured once at the listener and enabled/tuned per route with
`typed_per_filter_config`:

1. `fault` - per-route abort (`/fault`: 20 % 503).
2. `local_ratelimit` - per-route token bucket (`/limited`: `max_tokens 15, tokens_per_fill 10, fill_interval 1s`, status 429).
3. `ext_authz` wrapped in **`ExtensionWithMatcher`**: an `xds_matcher` with a `not_matcher` on `:authority` prefix
   `auth.lab` -> `SkipFilter`, so forward auth runs only for that host. `http_service` -> cluster `auth`
   (`app1:8080`, `path_prefix: /auth`), `allowed_headers` (x-auth-token, authorization) forwarded to the auth service,
   `allowed_upstream_headers` (x-auth-user, x-auth-groups) copied to the upstream request.
4. `jwt_authn` - provider `pxlab` with `local_jwks: /auth/jwt.jwks.json` (HS256 `oct` key), `claim_to_headers`
   `sub -> X-JWT-Sub`, `requirement_map: { pxlab }`; the `jwt.lab` vhost selects it with a `PerRouteConfig`.
5. `basic_auth` wrapped in `ExtensionWithMatcher` on `:path == /basic` (`users: /auth/htpasswd.sha1`).
6. `rbac` - per-route `RBACPerRoute` (`/allowed`: ALLOW only `direct_remote_ip 10.77.0.1/32`; `/denied`: DENY `10.77.0.0/24`).
7. `cors` - per-route `CorsPolicy`.
8. `buffer` - 64 MiB default, `BufferPerRoute` 1 MiB on `/upload` (413).
9. `bandwidth_limit` - `enable_mode: DISABLED` globally, `RESPONSE` with `limit_kbps: 488` on `/bw`.
10. `lua` - empty default, per-route `LuaPerRoute` on `/error-page` rewrites a 5xx body into the custom page.
11. `compressor.brotli`, `compressor.zstd`, `compressor.gzip` - `min_content_length 256`, content types.
12. `router`.

The alpha `envoy.filters.http.cache` is deliberately **absent**: in 1.39 it issues its own internal upstream request
that bypasses route-level header mutations, redirects and direct responses for every route (20+ probes broke). Caching
is declared unsupported.

## Routes (`rds.yaml`)

`request_headers_to_add` at the RouteConfiguration level adds `X-Lab-Proxy`, `X-Real-IP`
(`%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%`), `X-Forwarded-Host`, RFC 7239 `Forwarded`; `response_headers_to_remove:
[x-powered-by]`; `alt-svc` for h3. Envoy sets `x-forwarded-for`, `x-forwarded-proto`, `x-request-id` itself.

Virtual hosts:

| vhost | route |
|---|---|
| `a.lab`, `b.lab` | `route.cluster` + `request_headers_to_add X-Route` |
| `redirect.lab` | `redirect: { https_redirect: true, port_redirect: 8443, response_code: PERMANENT_REDIRECT }` |
| `weighted/leastconn/health.lab` | cluster does the work (weights, `LEAST_REQUEST`, health checks) |
| `hash.lab` | `hash_policy: [{ header: X-User }, { connection_properties: { source_ip } }]` on the `RING_HASH` cluster |
| `sticky.lab` | `hash_policy: [{ cookie: { name: lab_sticky, ttl: 3600s } }]` - Envoy generates the cookie |
| `retry.lab` | `retry_policy: { retry_on: connect-failure,refused-stream,reset, num_retries: 3 }` |
| `cb.lab` | cluster `cb` with `outlier_detection: { consecutive_5xx: 3, base_ejection_time: 10s }` + retries on 5xx |
| `canary.lab` | `weighted_clusters: [{app, 90}, {canary, 10}]` |
| `mirror.lab` | `request_mirror_policies: [{ cluster: shadow, runtime_fraction 100 }]` |
| `pp/h2/tls.lab` | clusters `app_pp` (`ProxyProtocolUpstreamTransport` V2), `app_h2` (`http2_protocol_options`), `app_tls` (`UpstreamTlsContext`, `sni: backend.lab`, `trusted_ca`, SAN matcher) |
| `auth.lab`, `jwt.lab`, `mtls.lab` | see filters above |
| `*` (default) | vhost-level `retry_policy: { retry_on: connect-failure,refused-stream,reset, num_retries: 2, retry_host_predicate: previous_hosts, host_selection_retry_max_attempts: 3 }` (a stopped backend costs a retry, not a 503: the first chaos run without it returned 208 x 503, with plain retries still 7-9 x 503 because a retry may pick the same host; the `previous_hosts` predicate brought it to 0), then the path routes below |

Default vhost routes, in order (first match wins): `DELETE /api/` -> `direct_response 405`; `X-Canary: 1` /
`?beta=1` -> `canary`; `/api/` `prefix_rewrite: /`; `safe_regex ^/v[0-9]+/`; `/old/` `regex_rewrite`; `/redirect-me`
`redirect.path_redirect`; gRPC prefix -> cluster `grpc` (h2c); `/ws` with `upgrade_configs` and `timeout: 0s`; `/sse`
`timeout: 0s`; `/limited`, `/allowed`, `/denied`, `/basic`, `/upload`, `/timeout` (`timeout: 2s`), `/fault`, `/bw`,
`/static/index.html` (`direct_response` from a file), `/error-page`, `/cors`, `/secure` (`response_headers_to_add`),
`/compressible`, then `prefix: /` -> `app`.

## Clusters (`cds.yaml`)

All `STRICT_DNS` + `dns_lookup_family: V4_ONLY` (Docker DNS), `connect_timeout: 3s`. `app` has generous
`circuit_breakers` (50k), active `health_checks` (`/healthz` every 2 s) and `idle_timeout: 90s` upstream keep-alive.
`weighted` uses `load_balancing_weight`; `leastconn` `LEAST_REQUEST`; `hash` `RING_HASH`; `retry` includes
`app3:8099`; `cb` outlier detection; `health` checks every 1 s; `grpc`/`app_h2` `http2_protocol_options`; `app_tls`
TLS transport socket; `app_pp` proxy-protocol transport socket; `app1_tcp`, `app1_tls_raw`, `app1_udp` for L4;
`jaeger` (h2) and `admin` (STATIC 127.0.0.1:9101).

## Operations

* Admin :9101 - `/server_info`, `/ready`, `/stats`, `/config_dump`, `/clusters`. The compose healthcheck speaks HTTP/1.1
  to `/ready` with bash (`/dev/tcp`), because the image has no curl and the admin server rejects HTTP/1.0.
* Reload = `sed -i 's/^version_info: .*/version_info: "<epoch>"/' rds.yaml`; the watched directory picks it up.
  `gen.py` writes `lds.yaml` via tmp + rename because inotify `MOVED_TO` is what Envoy watches.

## Unsupported here (and why)

`connection_limit` (the network filter is per listener; per-client needs the global rate-limit service),
`acme_auto_cert` (no ACME - SDS/cert-manager), `cache_hit/purge/stale_on_error` (alpha cache filter left out),
`docker_label_discovery`. `bandwidth_limit` runs but is marked ❌: the filter's ~1 s burst before throttling makes the
1 MiB transfer finish too fast for the probe's threshold.

## Gotchas we hit

1. Durations need units (`fill_interval: 0.05s`, not `0.05`).
2. `ext_authz.http_service.authorization_request.allowed_headers` is deprecated -> top-level `allowed_headers`.
3. Runtime-key overrides for max connections moved to the `overload_manager` downstream-connections monitor.
4. yaml-cpp: no merge keys, no unknown top-level keys -> generator with `ignore_aliases`.
5. WebSocket hung with buffer/bandwidth/compressor in the chain -> `upgrade_configs` with a router-only chain.
6. The alpha cache filter's internal request (XFF shows `10.77.0.1,10.77.0.2`, upstream null) skips route behaviour.
7. Health checks slow down to `no_traffic_interval` (**60 s** by default) on a cluster that has seen no traffic - the
   active-health probe failed once because app3 was only re-checked a minute later. Set `no_traffic_interval` (1-2 s
   here) when a pool is idle between bursts.
