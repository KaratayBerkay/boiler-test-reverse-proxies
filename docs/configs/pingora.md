# Pingora (Rust, custom proxy) - code walkthrough

Stack: `stacks/pingora/` - a ~780-line proxy written on Cloudflare's **Pingora 0.9** framework (`src/main.rs`,
`Cargo.toml`, `config.yaml`, `Dockerfile` -> image `pxlab-pingora:latest`). There is no config language: routing and
policies are Rust code implementing the `ProxyHttp` trait. This is the lab's "build your own proxy" option, so this page
walks through the code rather than a config file.

## Build and runtime

* `Cargo.toml`: `pingora` with features `lb, proxy, openssl, cache`, `pingora-limits` (rate / inflight counters),
  `jsonwebtoken`, `prometheus`, `parking_lot`, `serde_json`, `rand`, `uuid`; release profile `opt-level 3`, `lto =
  "thin"`, `codegen-units = 1`.
* `Dockerfile`: `rust:1-slim` build stage (`cargo build --release`), `debian:trixie-slim` runtime with `libssl3t64`,
  `curl` (healthcheck) and `procps` (`pgrep` for the upgrade). PID 1 is `sh -c "pingora-lab -c ...; while true; do sleep
  3600; done"` so that a zero-downtime upgrade (new process, old one exits) does not stop the container.
* `config.yaml` = Pingora `ServerConf`: `threads: 4`, `pid_file`, `upgrade_sock: /tmp/pingora_upgrade.sock`,
  `grace_period_seconds: 10`, `graceful_shutdown_timeout_seconds: 5`.

## `main()` - services

```rust
let app    = background_service("app health",  lb_rr(&[("app1:8080",1),("app2:8080",1),("app3:8080",1)], Some(2)));
let health = background_service("health.lab checks", lb_rr(..., Some(1)));
let cb     = background_service("cb.lab checks", lb_rr(&[app1, app2, flaky], Some(5)));
let weighted = background_service("weighted", lb_rr(&[("app1:8080",3),("app2:8080",1)], None));
let hash   = background_service("hash", LoadBalancer::<KetamaHashing>::from_backends(...));
let retry  = background_service("retry", lb_rr(&[app1, app2, ("app3:8099",1)], None));
let canary = background_service("canary", lb_rr(&[app1 30, app2 30, app3 30, canary 10], None));
```

Every `LoadBalancer` runs as a background service - including the ones without health checks, because `Static`
discovery only populates the backend set on the first update. `lb_rr` sets `HttpHealthCheck` (`GET /healthz`,
`consecutive_success/failure = 2`, 1 s timeouts) and `health_check_frequency`. `Backend::new` needs `IP:port`, so
`resolve()` turns docker names into addresses once at start.

Listeners: `http_proxy_service` on `0.0.0.0:8080` + `:80` with `HttpServerOptions { h2c: true }`; `:8443` with
`TlsSettings::with_callbacks(SniCerts { default: app.lab, b_lab })` + `enable_h2()` (the `TlsAccept` callback swaps in
b.lab's certificate when the SNI says so); `:8444` with `TlsSettings::intermediate(app.lab)`, `set_ca_file(ca.crt)`,
`set_verify(PEER | FAIL_IF_NO_PEER_CERT)` (mTLS). Plus three `listening::Service`s: `MetricsApp` on :9100
(`prometheus::TextEncoder`), `StatusApp` on :9101 (JSON: name, uptime, connections), `TcpProxyApp` on :9000 (raw
byte copy to `10.77.0.11:8080` with `tokio::io::copy_bidirectional`).

## `ProxyHttp` hooks

| hook | what it does |
|---|---|
| `init_downstream_modules` | adds `ResponseCompressionBuilder::enable(0)`; `early_request_filter` arms it (level 5, 0 for `/sse`) so the module parses `Accept-Encoding`; `response_filter` lowers it back to 0 unless the upstream `Content-Type` is text-like - the module itself compresses any `application/*`, and a 1 MiB random `/bin/` body gzipped at level 5 ran at 140 rps on 4 busy cores (3 400 rps once gated) |
| `request_filter` | **routing + everything answered locally**. Copies the header values it needs first (host, path, query, method, cookie, `X-User`, `Authorization`, `Content-Length`, `Origin`) to end the borrow, then: host `match` (`redirect.lab` -> 301 https; `b.lab` -> `Pool::Single("b1:8080")`; `weighted/hash/retry/cb/health/canary.lab` -> pools; `sticky.lab` parses `lab_sticky` -> `Pool::Single(appN)` or marks `sticky_new`; `h2.lab` -> `Pool::H2c`; `tls.lab` -> `Pool::Tls`; `jwt.lab` -> `verify_jwt` (HS256 with `jsonwebtoken`, `exp` validated) -> `X-JWT-Sub` or 401), then path features: DELETE `/api/` 405, `X-Canary`/`beta=1` -> canary, gRPC prefix -> `Pool::Grpc`, `/limited` -> `RATE.observe(&ip, 1) > 10` -> 429, `/conn-limited` -> `INFLIGHT.incr(ip, 1)` guard kept in ctx, `/allowed`, `/denied`, `/basic` (base64 compare), `/upload` (Content-Length), `/fault` (`rand::random::<f64>() < 0.2`), `/static/index.html` (file read once into a `LazyLock`), `/cors` OPTIONS -> 204; finally rewrites (`/api/` strip, `^/v<digits>/`, `/old/` -> `/new/`, `/conn-limited`, `/timeout` (sets `ctx.read_timeout = 2s`), `/bw`, `/error-page`, `/compressible`) via `set_uri` and `X-Route` headers |
| `request_cache_filter` | enables `session.cache` (MemCache + LRU eviction 64 MiB + `CacheLock`) for `/cacheable*` |
| `cache_key_callback` | `CacheKey::new(host + path, "lab")` |
| `response_cache_filter` | `CacheControl::from_resp_headers` -> `resp_cacheable(...)` with `CacheMetaDefaults` (60 s fresh, 30 s swr, 300 s sie); `no-store` -> uncacheable |
| `should_serve_stale` | `error.is_some()` (stale-if-error) |
| `upstream_peer` | `select()` picks the address: `lb.select(b"", 256)` for RR pools, `select_with(..., healthy && !outlier_marked)` for `cb`, `hash.select(hash_key)` for Ketama; builds the `HttpPeer`: TLS peers get `verify_cert`, `verify_hostname`, `ca`, SNI `backend.lab`; `H2c`/`Grpc` peers set `ALPN::H2` (prior knowledge); connection timeout 3 s, read timeout from ctx (30 s default), idle 90 s |
| `fail_to_connect` | `e.set_retry(true)` while `tries < 3` for the pools that may contain dead members - `upstream_peer` runs again and round-robin moves on |
| `upstream_request_filter` | `X-Lab-Proxy`, `X-Real-IP`, `X-Forwarded-Proto` (from `ssl_digest`), `X-Forwarded-Host`, RFC 7239 `Forwarded`, `X-Forwarded-For` append, `X-Request-ID` (uuid when absent) |
| `upstream_response_filter` | `outlier_observe(addr, 5xx)` for `cb.lab`: 3 failures -> ejected for 10 s (a `Mutex<HashMap>` of counters) |
| `response_filter` | removes `X-Powered-By`, `Server: pingora`, `X-Cache` from `session.cache.phase()` (HIT / STALE / MISS / BYPASS), sticky `Set-Cookie` from the upstream's `X-Instance`, CORS and security headers, and for `/error-page` + 5xx strips `Content-Length`/`Content-Encoding` and flags the body for replacement |
| `response_body_filter` | replaces the first chunk with the custom error page, empties the rest |
| `logging` | JSON line to stdout (time, client, method, uri, host, status, duration, upstream, tries, cache phase, error) + Prometheus counters/histograms |

## Operations

Zero-downtime upgrade (`reload_cmd`): start a new `pingora-lab -u -c config.yaml` (it requests the listening sockets
over the upgrade socket), then `kill -QUIT <old pid>`; the old process hands the sockets over and drains within
`grace_period_seconds`. There is no pid-file check for the old process - `pgrep -o -x pingora-lab` finds it.

## Unsupported here (and why)

`lb_least_conn` (would be a custom `BackendSelection`), `lb_mirror`, `proxy_protocol_upstream`, `proxy_protocol_accept`,
`udp_l4`, `tls_passthrough_sni` (the L4 app copies bytes without SNI parsing), `http3`, `acme_auto_cert`, `cache_purge`
(MemCache purge left out of scope), `cache_stale_on_error` (objects expire before the lab's 2 s window),
`compress_brotli` (feature-gated), `forward_auth`, `bandwidth_limit`, `tracing_otel`, `docker_label_discovery`. Most of
these are missing from *this code*, not from the framework.

## Gotchas we hit

1. `Static::new` returns a `Box`, `CacheKey::new(primary, user_tag)`, `HttpServerOptions` is `#[non_exhaustive]`
   (use `Default` + field assignment).
2. Borrow conflicts: read every header value you need before mutating the session.
3. `Backend::new` wants `IP:port` -> `resolve()`; `HttpHealthCheck::new("app.lab", false)` then `set_uri` on the
   existing request keeps the Host header (replacing the request lost it).
4. Pools without health checks stayed empty until they ran as background services (one discovery update).
5. SSE was buffered by the compression module -> level 0 for `/sse`; the module also compresses `application/octet-stream`,
   so gate by content type in `response_filter` (the level must be > 0 at request time or Accept-Encoding is never parsed).
7. Metrics registered lazily (`LazyLock` on first request) were empty on a freshly upgraded process -> `LazyLock::force`
   at start-up + the process collector.
6. `-u -d` (daemonize) waited for the socket transfer; start the new process in the background, then SIGQUIT the old.
