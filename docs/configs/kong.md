# Kong Gateway 3.9 (OSS, DB-less) - config walkthrough

Stack: `stacks/kong/` - image `kong:3.9`. Kong is OpenResty plus an entity model (services, routes, upstreams,
consumers, plugins). In **DB-less** mode the whole model is one declarative file: `kong.src.yml` -> `gen.py` ->
`kong.yml` (the generator inlines PEM files for `${file:certs/...}` placeholders, because certificates must be inline
in declarative config). Everything nginx-level comes from `KONG_*` environment variables in `compose.yaml`.

Read this next to `stacks/kong/kong.src.yml` and `stacks/kong/compose.yaml`.

## nginx-level settings (environment)

| variable | meaning |
|---|---|
| `KONG_DATABASE=off`, `KONG_DECLARATIVE_CONFIG=/kong/kong.yml` | DB-less |
| `KONG_ROUTER_FLAVOR=expressions` | the expressions router (`http.host == "a.lab" && http.path ^= "/api/"`) |
| `KONG_PROXY_LISTEN="0.0.0.0:8080 http2 reuseport, 0.0.0.0:80 reuseport, 0.0.0.0:8443 http2 ssl reuseport, 0.0.0.0:8082 proxy_protocol reuseport"` | h2c on 8080, TLS + h2 on 8443, PROXY protocol on 8082 |
| `KONG_STREAM_LISTEN="0.0.0.0:9000 reuseport, 0.0.0.0:9001 udp reuseport, 0.0.0.0:8445 ssl reuseport"` | stream listeners; `ssl` on 8445 is what makes `tls_passthrough` routes preread SNI |
| `KONG_ADMIN_LISTEN=0.0.0.0:8001` (-> host 19101), `KONG_STATUS_LISTEN=0.0.0.0:9100` | admin API; status API with `/metrics` (prometheus plugin) |
| `KONG_ADMIN_GUI_LISTEN=off` | Kong Manager would otherwise grab 8445 |
| `KONG_SSL_CERT/KEY` | default certificate; per-SNI certs come from the declarative `certificates` + `snis` |
| `KONG_TRUSTED_IPS=0.0.0.0/0`, `KONG_REAL_IP_HEADER=proxy_protocol`, `KONG_REAL_IP_RECURSIVE=on` | client IP from PROXY protocol / XFF |
| `KONG_LUA_SSL_TRUSTED_CERTIFICATE=/certs/pebble-ca.pem,/certs/ca.crt` | cosocket trust (ACME client, TLS upstream verification) |
| `KONG_NGINX_HTTP_LOG_FORMAT` + `KONG_PROXY_ACCESS_LOG=/dev/stdout json_lab` | JSON access log (`$$` escapes compose interpolation) |
| `KONG_NGINX_PROXY_GZIP*` | gzip injected into the proxy server block (no compression plugin in OSS) |
| `KONG_TRACING_INSTRUMENTATIONS=all`, `KONG_TRACING_SAMPLING_RATE=0.001` | tracing instrumentation (exporter = opentelemetry plugin) |
| `KONG_UNTRUSTED_LUA=on` | pre/post-function code may use `io` (static file, error page) |

## Declarative model (`kong.src.yml`)

* `certificates` (app.lab, b.lab) + `snis` (`app.lab, a.lab, proxy, localhost` -> cert 1, `b.lab` -> cert 2) +
  `ca_certificates` (lab CA, referenced by the TLS upstream service).
* `upstreams` = load-balancing pools:

| upstream | algorithm / options | contract |
|---|---|---|
| `app` | `round-robin`, active health (`/healthz`, interval 2, 2 successes/failures) + passive | default pool |
| `weighted` | targets `weight: 300` / `100` | weighted RR |
| `leastconn` | `least-connections` | |
| `hash` | `consistent-hashing`, `hash_on: header`, `hash_on_header: x_user` (nginx-variable spelling!), `hash_fallback: ip` | header hash |
| `sticky` | `hash_on: cookie`, `hash_on_cookie: lab_sticky` - Kong sets the cookie itself | cookie stickiness |
| `retry` | RR incl. `app3:8099`; the service has `retries: 3` | retry |
| `cb` | passive `http_statuses: [500,502,503,504], http_failures: 3` + active checks every 5 s to re-admit | outlier ejection |
| `health` | active checks every 1 s | active health |
| `canary_split` | weights 30/30/30/10 | traffic split |

* `services` own their `routes` (nested; a nested route's `service:` must be absent). The main service `app` (host =
  upstream `app`, `retries: 3`, timeouts) carries the host routes (`priority: 100`) and the path routes
  (`priority: 50`, `strip_path: false` - the default `true` would strip an exact path to `/`):

| route | expression | plugins |
|---|---|---|
| `a` | `http.host == "a.lab"` | `request-transformer add X-Route:a` |
| `redirect` | `http.host == "redirect.lab"` | `pre-function` -> `kong.response.exit(301, "", { Location = "https://..." })` |
| `jwt` | `http.host == "jwt.lab"` | `jwt { key_claim_name: iss, claims_to_verify: [exp] }` (credential on consumer `lab`, key `pxlab`) |
| `api-delete` (60) | `http.method == "DELETE" && http.path ^= "/api/"` | `pre-function` 405 |
| `api` | `http.path ^= "/api/"`, `strip_path: true`, `path_handling: v1` | `X-Route:api` |
| `versioned` | `http.path ~ r#"^/v[0-9]+/"#` | |
| `old` | `http.path ~ r#"^/old/(?<rest>.*)$"#` | `request-transformer replace uri /new/$(uri_captures.rest)` |
| `redirect-me` | `http.path == "/redirect-me"` | `pre-function` 301 |
| `limited` | | `rate-limiting { second: 10, policy: local, limit_by: ip, error_code: 429 }` |
| `conn-limited` | | rewrite only (no concurrency limit in OSS) |
| `allowed` / `denied` | | `ip-restriction { allow: [10.77.0.1] }` / `{ deny: [10.77.0.0/24] }` |
| `basic` | | `basic-auth` (consumer `lab` / `lab-pass`) |
| `upload` | | `request-size-limiting { allowed_payload_size: 1, size_unit: megabytes }` |
| `fault` | | `pre-function` with `math.random() < 0.2 -> 503` |
| `static` | | `pre-function` reads `/static/index.html` (`io`) |
| `error-page` | | `request-transformer` -> `/status/503`; `post-function` with `enable_buffering()`, `header_filter` (sets `X-Error-Page`, clears `Content-Length`) and `body_filter` (`set_raw_body` from `/static/error.html`) |
| `cors` | | `cors { origins: ["*"], methods, headers, max_age }` |
| `secure` | | `response-transformer add` the four headers |
| `cacheable` | `http.path ^= "/cacheable"` | `proxy-cache { strategy: memory, cache_control: true, cache_ttl: 60 }`; purge = `DELETE /proxy-cache` on the admin API |
| `compressible` | | rewrite to `/size/65536` (gzip from nginx) |
| `catch-all` (1) | `http.path ^= "/"` | |

Other services: `canary` (routes `http.headers.x_canary == "1"`, `http.queries.beta == "1"`, priority 56), `b`
(`b1:8080`), one service per upstream (`weighted`, `leastconn`, `hash`, `sticky`, `retry`, `cb`, `health`,
`canary_split`), `app_tls` (`protocol: https`, `tls_verify: true`, `ca_certificates`), `app_t2` (`read_timeout: 2000`,
`retries: 0`, route `/timeout`), `grpc` (`protocol: grpc`, route `protocols: [grpc, grpcs]`), and the stream services
`tcp_app1` (`protocol: tcp`, route `destinations: [{ port: 9000 }]`), `udp_app1` (`udp`, port 9001),
`passthrough_app1` (`tls_passthrough`, `snis: [passthrough.lab]`, port 8445).

* `consumers`: `lab` with `basicauth_credentials` and `jwt_secrets` (HS256, `key: pxlab` = the `iss` claim).
* Global `plugins`: `pre-function` (adds `X-Lab-Proxy` and RFC 7239 `Forwarded`; Kong sets `X-Forwarded-*`,
  `X-Real-IP` itself), `response-transformer` (remove `X-Powered-By`, add `Alt-Svc`), `correlation-id`
  (`X-Request-ID`, uuid, `echo_downstream`), `prometheus` (status codes, latency, bandwidth, upstream health),
  `opentelemetry` (`traces_endpoint: http://jaeger:4318/v1/traces`, `sampling_rate: 0.001`, w3c headers), `acme`
  (`api_uri: https://static:14001/directory` - Kong appends `/directory`, Pebble serves `/dir`, so
  `shared/staticsrv` provides a TLS shim; `storage: shm`, HTTP-01 on :80).

## Operations

* Reload: `python3 gen.py && curl -X POST http://127.0.0.1:19101/config -F config=@kong.yml` - the admin API
  re-applies the declarative file atomically. `kong reload` only HUPs nginx and does **not** re-read it.
* Admin `/status` on 19101; metrics `/metrics` on 9100; `kong health` as the container healthcheck.

## Unsupported here (and why)

`lb_mirror`, `h2_upstream` (gRPC only), `proxy_protocol_upstream`, `mtls_client_cert` (mtls-auth is Enterprise),
`http3`, `cache_stale_on_error`, `compress_brotli`/`zstd`, `connection_limit`, `forward_auth` (openid-connect is
Enterprise; a pre-function with lua-resty-http would do), `bandwidth_limit`, `docker_label_discovery`.

## Gotchas we hit

1. `${file:...}` placeholders are replaced even inside comments - keep them out of comments.
2. A block sequence inside a flow mapping is invalid YAML; nested routes must not carry `service:`; `snis` need
   `certificate: { id }`.
3. Kong Manager listens on 8445 by default -> `KONG_ADMIN_GUI_LISTEN=off`.
4. `strip_path` defaults to `true` and strips exact-path routes to `/`.
5. `hash_on_header` must be spelled as the nginx variable (`x_user`); `X-User` silently hashes nothing.
6. `kong reload` does not re-read DB-less config -> `POST /config`.
7. The ACME plugin appends `/directory` to `api_uri` -> the static shim in `shared/compose.yaml`.
8. `tls_passthrough` needs the stream listener flagged `ssl`.
9. Sandboxed Lua blocks `io` -> `KONG_UNTRUSTED_LUA=on` for the file-serving functions.
