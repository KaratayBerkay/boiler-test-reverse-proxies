# OpenResty 1.27 - config walkthrough

Stack: `stacks/openresty/` - custom image `pxlab-openresty:latest` = `openresty/openresty:1.27.1.2-alpine-fat` + opm
packages (`SkyLothar/lua-resty-jwt`, `knyar/nginx-lua-prometheus`, `fffonion/lua-resty-acme`, `ledgetech/lua-resty-http`;
`lua-resty-limit-traffic` is bundled). Config: `nginx.conf` + `snippets/` (mounted as `/etc/openresty`).

The nginx core is the same as `stacks/nginx` (read `docs/configs/nginx.md` first). This page covers **what is done in
Lua instead** - the point of OpenResty is that everything nginx open source lacks can be scripted in `*_by_lua_block`
phases without extra C modules.

## Shared dicts and init phases

```nginx
lua_shared_dict limit_req 10m;    lua_shared_dict limit_conn 10m;    # lua-resty-limit-traffic state
lua_shared_dict prometheus 16m;                                       # nginx-lua-prometheus
lua_shared_dict acme 16m;                                             # lua-resty-acme storage (shm adapter)
lua_ssl_trusted_certificate /certs/pebble-ca.pem;                     # cosocket TLS trust (ACME client)
```

* `init_by_lua_block` - `require("resty.acme.autossl").init({ tos_accepted, domain_whitelist = {"acme.lab"},
  storage_adapter = "shm", domain_key_types = {"ecc"}, blocking = false }, { api_uri = "https://pebble:14000/dir" })`.
  The ACME client options (directory URL) are the **second** argument - putting `api_uri` in the first silently
  targets Let's Encrypt.
* `init_worker_by_lua_block` - `autossl.init_worker()`, an eager issuance timer on worker 0 (`update_cert{domain =
  "acme.lab"}` two seconds after start, controlled by `ACME_EAGER`; without it the first handshake gets the fallback
  certificate and issuance happens lazily), and the Prometheus registry + metrics (`prometheus.init` must run per
  worker).
* `log_by_lua_block` - `metric_requests:inc`, `metric_latency:observe` for every request.

## Lua per location

| contract | Lua |
|---|---|
| `/limited` | `access_by_lua_block`: `resty.limit.req.new("limit_req", 10, 5)`; `lim:incoming(binary_remote_addr, true)` -> `rejected` => `ngx.exit(429)`; the returned `delay` is ignored deliberately = nginx `nodelay` semantics (sleeping on it would smooth the burst instead) |
| `/conn-limited` | `resty.limit.conn.new("limit_conn", 3, 0, 0.5)` in access, `lim:leaving(...)` in `log_by_lua_block` (stored in `ngx.ctx`) |
| `/fault` | `access_by_lua_block { if math.random() < 0.2 then return ngx.exit(503) end }` |
| `PURGE /cacheable/x` | `@purge` `content_by_lua_block`: rebuild nginx's cache path from the key (`md5`, `levels=1:2` -> `<last>/<2 before>/<md5>`) and `os.remove` it - a **real** purge, unlike the refresh trick in the nginx stack; answers `X-Cache: PURGED` / `NOT-FOUND` |
| `auth.lab` | `ngx.location.capture("/_auth")` (internal location proxying to `app1:8080/auth`); non-200 -> 401/403 with `WWW-Authenticate`; `ngx.req.set_header("X-Auth-User", ...)` |
| `jwt.lab` | `resty.jwt:verify(secret, token, { exp = validators.is_not_expired() })`; `X-JWT-Sub` from `obj.payload.sub` |
| `acme.lab` | `ssl_certificate_by_lua_block { autossl.ssl_certificate() }` (placeholder `ssl_certificate` directives are required by nginx but replaced per handshake); `/.well-known/acme-challenge` -> `autossl.serve_http_challenge()` on the default vhost's port 80 |
| `:9100/metrics` | `content_by_lua_block { metric_connections:set(...) prometheus:collect() }` - native Prometheus without an exporter sidecar |
| `:9101/_pebble-check` | debug aid: `resty.http` request to Pebble with `ssl_verify = true` proves the cosocket trust store |

Everything else (routing maps, upstreams, stream block, cache, gzip, `limit_rate`, mTLS, sticky cookie, mirror, tls
upstream) is identical to the nginx stack; `X-Lab-Proxy` is `openresty`.

## Operations

Reload `openresty -c /etc/openresty/nginx.conf -s reload` (SIGHUP; Lua code in `*_by_lua_block` is reloaded with the
config, `init_by_lua` state is rebuilt, shared dicts survive).

## Unsupported here (and why)

`lb_active_health` (needs lua-resty-upstream-healthcheck driving the balancer), `h2_upstream`,
`proxy_protocol_upstream` (nginx limits), `compress_brotli`, `compress_zstd`, `tracing_otel` (opentelemetry-lua is a
separate integration), `docker_label_discovery`.

## Gotchas we hit

1. opm has no `openresty/lua-resty-balancer` package in this image's index; the bundled `resty.limit.*` and
   `ngx.balancer` cover the lab.
2. `prometheus.init()` in `init_by_lua` is not enough - counters live per worker and need `init_worker`.
3. `autossl.init(autossl_config, acme_config)`: `api_uri` belongs to the second table.
4. `blocking = false` matters: with `blocking = true` issuance happens inside `ssl_certificate_by_lua`, where cosocket
   TLS ignores `lua_ssl_trusted_certificate`.
