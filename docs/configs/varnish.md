# Varnish Cache 8 + hitch - config walkthrough

Stack: `stacks/varnish/` - four containers: `varnishd` (image `varnish:8.0`), `hitch` (TLS terminator, `hitch:latest`),
`varnishncsa` (JSON access log, same image on the shared VSM dir) and `prometheus_varnish_exporter`
(`exporter/Dockerfile`). Files: `default.vcl`, `hitch.conf`. Read this next to `stacks/varnish/default.vcl`.

## Process / listeners (compose `command`)

```
varnishd -F -n /var/lib/varnish/pxlab -f /etc/varnish/default.vcl
  -a http=:8080,HTTP  -a http80=:80,HTTP          # plain HTTP (h2c via feature=+http2)
  -a proxy=:6086,PROXY                             # from hitch: PROXY v2 carries client IP + TLS facts
  -a pp=:8082,PROXY                                # accepts PROXY protocol from clients
  -p feature=+http2 -p http_gzip_support=on
  -p thread_pools=2 -p thread_pool_min=200 -p thread_pool_max=4000
  -p workspace_client=128k -p http_req_size=64k -s malloc,512m -t 120
```

Varnish Cache has **no TLS**: hitch listens on :8443 (app.lab + b.lab certs, SNI) and :8444 (mTLS,
`client-verify = required`, `client-verify-ca = /certs/ca.crt`), negotiates h2 by ALPN (`alpn-protos = "h2,
http/1.1"`) and forwards to `[varnish]:6086` with `write-proxy-v2 = on`. In VCL, `proxy.is_ssl()` (vmod_proxy) reads the
PROXY TLVs to set `X-Forwarded-Proto`.

## VCL: imports, backends, probes

```vcl
import directors; import std; import proxy; import vsthrottle; import digest; import reqwest;
import saintmode; import fileserver; import uuid; import cookie;
probe hc { .url = "/healthz"; .interval = 1s; .window = 3; .threshold = 2; }
backend app1 { .host = "app1"; .port = "8080"; .probe = hc; .max_connections = 4000; ... }
backend dead    { .host = "app3"; .port = "8099"; }             # retry demo
backend app1_pp { .host = "app1"; .port = "8081"; .proxy_header = 2; }   # PROXY v2 to the upstream
backend app1_t2 { .host = "app1"; .port = "8080"; .first_byte_timeout = 2s; }   # /timeout
acl lab_net { "10.77.0.0"/24; }  acl host_only { "10.77.0.1"; }
```

Every backend declared must be used somewhere or `varnishd` refuses the VCL.

`vcl_init` builds the directors: `rr` (round_robin), `weighted` (random with weights 3/1), `hash` (`directors.shard`,
consistent hashing; key = `hash.key(req.http.X-User)`), `retry` (rr incl. `dead`), `cb` (rr of `saintmode` wrappers:
per-object denylist after 5xx = outlier ejection), `canary_split` (random 30/30/30/10), `fs = fileserver.root("/static")`,
`authsvc = reqwest.client(...)` (forward auth) and `tlsbe = reqwest.client(base_url = "https://app1:8443", ...)` - the
HTTPS/h2 backend (Varnish itself only speaks HTTP/1.1 to backends).

## `vcl_recv`

1. Headers for the upstream: `X-Lab-Proxy`, `X-Request-ID = uuid.uuid_v4()` when absent, `X-Forwarded-Proto` from
   `proxy.is_ssl()`, `X-Forwarded-Host`, `X-Real-IP`, RFC 7239 `Forwarded`; `X-Host` = host without port.
2. `PURGE` on `/cacheable*` -> `return (purge)`; WebSocket upgrade -> `return (pipe)` (`vcl_pipe` copies the Upgrade
   headers).
3. Host switch on `X-Host`: `redirect.lab` -> `synth(750)` (301 to https in `vcl_synth`), `a.lab`/`b.lab` set `X-Route`
   and the backend, each balancing host picks its director (`hash.backend(by = KEY, key = ...)`, cookie stickiness with
   `cookie.get("lab_sticky")` -> exact backend and `X-Sticky-New` for the first visit), `pp.lab` -> `app1_pp`,
   `tls.lab`/`h2.lab` -> `tlsbe.backend()`, `auth.lab` -> `authsvc.init/set_header/send` then `synth(401)` unless 200
   (`X-Auth-User` copied), `jwt.lab` -> HS256 check in pure VCL:
   `digest.base64url_nopad_hex(digest.hmac_sha256(secret, header.payload)) != sig` -> 401, `exp` extracted with a regex
   and compared through `std.real(...)`, `X-JWT-Sub` extracted the same way.
4. Path rules: DELETE `/api/` -> `synth(405)`; `X-Canary`/`beta=1` -> `canary`; `/api/` strip via `regsub`;
   `^/v[0-9]+/`; `/old/` -> `/new/`; `/redirect-me` -> `synth(751)`; `/limited` ->
   `vsthrottle.is_denied("" + client.ip, 10, 1s, 10s)` -> 429; `/conn-limited` (no per-client concurrency limit ->
   unsupported); `/allowed`, `/denied` via ACLs; `/basic` compares the header with `"Basic " + digest.base64("lab:lab-pass")`;
   `/upload` -> `std.integer(req.http.Content-Length, 0) > 1048576` -> 413; `/timeout` -> `app1_t2`; `/fault` ->
   `std.random(0, 100) < 20` -> 503; `/bw` (no bandwidth limiting -> unsupported); `/static/` -> `fs.backend()` + `pass`;
   `/error-page` sets `X-Custom-Error`; `/cors` OPTIONS -> `synth(752)`; `/compressible` -> `/size/65536`.
5. Non-GET/HEAD -> `pass`, else `hash` (the origin's `Cache-Control` decides what is cached; the built-in vcl handles
   `Set-Cookie`, `no-store`, etc.).

## Backend side

`vcl_backend_response`: `beresp.grace = 300s` (stale while revalidate / stale on error); a background fetch returning 5xx
is `abandon`ed so the stale object survives (`cache_stale_on_error`); `do_stream = true`; `do_gzip` for text and JSON
but **not** `event-stream` (gzip would buffer SSE); `cb.lab` + 5xx -> `saintmode.denylist(10s)` + `return (retry)`;
`/error-page` 5xx -> `return (error(status))` so `vcl_backend_error` builds the custom page
(`synthetic(std.fileread("/static/error.html"))`, `X-Error-Page: custom`). `vcl_backend_error` also implements the
retry-on-connect-failure for `retry.lab` (`bereq.retries < 3 -> retry`) and, for every route, one retry of idempotent
requests except the deliberate timeout route (without it the first chaos run answered 156 x 503 while app2 was stopped).

## Delivery

`vcl_deliver`: `X-Cache HIT/MISS` from `obj.hits`, strips `X-Powered-By`/`Via`, sets the sticky cookie on first visit
(`Set-Cookie lab_sticky=<X-Instance>`), CORS and security headers. `vcl_synth`: 750/751/752 become the https redirect,
`/landing` redirect and CORS preflight; 401 gets the right `WWW-Authenticate`; everything else is a short text body.

## Operations

* Reload: `varnishreload -n /var/lib/varnish/pxlab` (`vcl.load` + `vcl.use` over the management socket) - no
  connection drop.
* Admin probe: `varnishadm status`; metrics from the exporter on :9100; access log = `docker logs pxlab-varnish-log`
  (varnishncsa `-F` JSON format with `%{Varnish:handling}x` = hit/miss/pass/pipe).

## Unsupported here (and why)

`lb_least_conn` (no such director), `lb_mirror`, `h2_upstream` (only through vmod_reqwest over TLS), `tcp_l4`,
`udp_l4`, `tls_passthrough_sni`, `http3`, `grpc` (no h2 trailers to backends), `acme_auto_cert` (hitch has no ACME
client), `connection_limit`, `bandwidth_limit`, `compress_brotli`, `compress_zstd`, `tracing_otel`,
`docker_label_discovery`.

## Gotchas we hit

1. Strings with quotes need the long-string form `{"..."}`.
2. `std.time2integer` does not exist in 8.0 - `std.real(now, 0.0)` does.
3. An unused `backend` is a compile error - delete it or reference it.
4. hitch: a frontend-level `client-verify` only applies to `pem-file`s declared **inside that frontend**.
5. SSE was buffered by gzip -> exclude `event-stream` from `do_gzip` and keep `do_stream`.
6. Chunked responses from Varnish broke the raw-socket probes until the harness learned to decode chunked bodies.
