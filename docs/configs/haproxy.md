# HAProxy 3.4 LTS - config walkthrough

Stack: `stacks/haproxy/` - image `haproxy:lts` (3.4.4, master-worker mode, OpenSSL 3.5 with native QUIC). Files:
`haproxy.cfg`, `lab.lua` (forward auth), `errors/503.http` (custom error page). The directory is mounted at
`/usr/local/etc/haproxy`.

HAProxy has no vhost concept: **one frontend** handles every hostname and path with `http-request` rules and
`use_backend` selection. Read this next to `stacks/haproxy/haproxy.cfg`.

## `global`

```haproxy
expose-experimental-directives            # the `acme` section is experimental in 3.2-3.4
stats socket ipv4@0.0.0.0:9999 level admin expose-fd listeners   # runtime API; expose-fd = seamless reload
maxconn 60000
ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets
httpclient.resolvers.id docker            # the internal HTTP client (ACME + Lua) resolves via Docker DNS
httpclient.ssl.ca-file /certs/pebble-ca.pem
lua-load /usr/local/etc/haproxy/lab.lua
```

Threads follow the cpuset (4). The compose healthcheck talks to the :9999 runtime API with bash's `/dev/tcp` because the
image has no curl.

## `defaults`

* `log-format '%{+json}o %(time)t %(client_ip)ci ...'` - the 3.0+ JSON encoder with named fields (`access_log_json`).
* `option forwardfor` (XFF) and `option forwarded proto host for` (RFC 7239, 2.8+).
* `http-reuse always` - upstream connection pool shared across clients.
* `timeout tunnel 1h` - WebSocket lifetime; `timeout connect 3s`, `timeout server 30s`.
* `retries 3`, `option redispatch`, `retry-on conn-failure empty-response` - connection-level retries (`lb_retry`).
* `default-server inter 2s fall 2 rise 2 resolvers docker ... init-addr last,libc,none` - every server resolves through
  Docker DNS and keeps working if a name is temporarily unresolvable.
* `compression algo-res gzip` (libslz; no brotli/zstd), `errorfiles lab` -> `http-errors lab` with `errorfile 503`.

Global objects: `userlist lab` (basic auth), `cache lab` (256 MB, `max-age 60`, `process-vary on`), two stick tables
`st_req_rate` (`http_req_rate(1s)`) and `st_conn` (`conn_cur`).

## ACME

```haproxy
acme pebble
    directory https://pebble:14000/dir
    challenge http-01
    keytype ECDSA
    map virt@acme
crt-store
    load crt "/tmp/acme.lab.pem" alias "acme" acme pebble domains "acme.lab"
```

The crt-store starts with a temporary self-signed key pair, the ACME task fills the `virt@acme` map with the challenge
tokens, and the frontend answers `/.well-known/acme-challenge/` from that map:

```haproxy
http-request return status 200 content-type text/plain lf-string "%[path,field(-1,/)].%[path,field(-1,/),map(virt@acme)]\n" if { path_beg /.well-known/acme-challenge/ }
```

The binds reference the store as `crt "@/acme"`. Renewal: `acme renew acme` on the runtime API.

## The frontend `fe_http`

```haproxy
bind :80
bind :8080                                             # h1 + h2c (prior knowledge auto-detected)
bind :8443 ssl crt /certs/app.lab.pem crt /certs/b.lab.pem crt "@/acme" alpn h2,http/1.1   # SNI -> cert
bind quic4@:8443 ssl crt ... alpn h3                   # HTTP/3
bind :8444 ssl crt /certs/app.lab.pem ca-file /certs/ca.crt verify required                # mTLS
bind :8082 accept-proxy                                # PROXY protocol from clients
filter cache lab
filter compression
filter bwlim-out lab_bw default-limit 500000 default-period 1s
```

When more than one filter is used they must all be declared explicitly, in processing order.

### Header rules (every request)

`X-Forwarded-Proto` from `ssl_fc`, `X-Forwarded-Host`, `X-Real-IP`, `X-Lab-Proxy`, `X-Request-ID` from `unique-id`
(`unless { req.hdr(X-Request-ID) -m found }`), `X-Client-Cert-CN %[ssl_c_s_dn(CN)] if { ssl_c_used }`,
`http-response del-header X-Powered-By`, `alt-svc h3`.

The host is captured once: `http-request set-var(txn.h) req.hdr(host),field(1,:),lower` and every host rule tests
`{ var(txn.h) -m str x.lab }`. The path is copied to `txn.path` because `http-response` rules run after the request
buffer may be gone.

### Host rules

| host | rule |
|---|---|
| `redirect.lab` | `http-request redirect scheme https code 301 if ... !{ ssl_fc }` |
| `a.lab`, `b.lab` | `set-header X-Route a/b`; `use_backend be_b` for b.lab |
| `auth.lab` | `http-request lua.forward_auth` (Lua httpclient GET `app1:8080/auth`, sets `txn.auth_ok`/`txn.auth_user`), then `deny deny_status 401 ... !{ var(txn.auth_ok) -m int 1 }` and `set-header X-Auth-User` |
| `jwt.lab` | `jwt_verify("HS256","<secret>")` on the bearer token; `jwt_payload_query('$.exp','int'),sub(txn.now) -m int lt 1` rejects expired tokens; `X-JWT-Sub` from `jwt_payload_query('$.sub')` |
| `weighted/leastconn/hash/sticky/retry/cb/health/canary/pp/h2/tls.lab` | `use_backend be_*` |

### Path rules (default vhost)

| path | rule |
|---|---|
| `/api/` | `deny deny_status 405 ... METH_DELETE`; `set-header X-Route api`; `set-path %[path,regsub(^/api/,/)]` |
| `^/v[0-9]+/` | `path_reg` -> `X-Route versioned` |
| `/old/` | `set-path %[path,regsub(^/old/,/new/)]` |
| `/redirect-me` | `redirect location /landing code 301` |
| `/limited` | `track-sc0 src table st_req_rate` + `deny deny_status 429 if { sc_http_req_rate(0) gt 10 }` |
| `/conn-limited` | `track-sc1 src table st_conn` + `deny 429 if { sc_conn_cur(1) gt 3 }` |
| `/denied`, `/allowed` | `deny if { src 10.77.0.0/24 }` / `deny if !{ src 10.77.0.1 }` |
| `/basic` | `http-request auth realm pxlab if !{ http_auth(lab) }` |
| `/upload` | `deny deny_status 413 if { req.hdr_val(content-length) gt 1048576 }` |
| `/timeout` | `set-path /delay/5000`; the 2 s timeout is `http-request set-timeout server 2s` **in `be_app`** (`set-timeout` is backend-only) |
| `/fault` | `deny deny_status 503 if { rand(100) lt 20 }` |
| `/bw` | `set-path /bin/1048576` + `http-response set-bandwidth-limit lab_bw` |
| `/static/index.html` | `http-request return status 200 content-type text/html file /static/index.html` |
| `/error-page` | `set-path /status/503` + `http-response return status 503 ... file /static/error.html hdr X-Error-Page custom if { status 503 }` |
| `/cors` | `http-request return status 204 hdr Access-Control-Allow-Origin ... METH_OPTIONS`; response header on GET |
| `/secure` | four `http-response set-header` |
| `/cacheable*` | `http-request cache-use lab` / `http-response cache-store lab`; `X-Cache HIT/MISS` from `res.cache_hit` |
| `/compressible` | `set-path /size/65536` (compression filter) |
| `/grpc.health.v1.Health/` | `use_backend be_grpc` |
| `X-Canary: 1` / `?beta=1` | `use_backend be_canary if { req.hdr(X-Canary) -m str 1 } || { urlp(beta) -m str 1 }` |

## Backends

```haproxy
backend be_app         balance roundrobin; server appN appN:8080 check maxconn 20000
backend be_weighted    weight 3 / weight 1
backend be_leastconn   balance leastconn
backend be_hash        balance hdr(X-User); hash-type consistent
backend be_sticky      cookie lab_sticky insert indirect nocache httponly; server ... cookie a1
backend be_retry       no checks; server dead app3:8099 (found only by connect failures + redispatch)
backend be_cb          retry-on all-retryable-errors; server ... observe layer7 error-limit 3 on-error mark-down
backend be_health      check inter 1s fall 2 rise 2
backend be_canary_split weights 30/30/30/10
backend be_pp          server app1 app1:8081 send-proxy-v2 check check-send-proxy
backend be_h2          server app1 app1:8080 proto h2
backend be_tls         ssl verify required ca-file /certs/ca.crt sni str(backend.lab) check check-sni backend.lab
backend be_grpc        option tcp-check; server app1 app1:9090 proto h2
```

`be_grpc` needs `option tcp-check`: the inherited `option httpchk GET /healthz` would mark the gRPC port down.

## L4

`fe_tcp :9000 -> be_tcp app1:8080` (mode tcp) and `fe_passthrough :8445` with `tcp-request inspect-delay 5s`,
`tcp-request content accept if { req.ssl_hello_type 1 }` and `use_backend ... if { req.ssl_sni -i passthrough.lab }`.
No UDP (HAProxy only proxies TCP/QUIC) -> `udp_l4` unsupported.

## Operations

* `frontend metrics :9100` - `http-request use-service prometheus-exporter if { path /metrics }` (built in).
* `frontend stats :9101` - `stats enable; stats uri /stats; stats admin if TRUE`.
* Reload: `haproxy -c -f ... -q && kill -USR2 1` - the master starts a new worker, listeners are handed over through
  `expose-fd listeners`, the old worker drains.

## Unsupported here (and why)

`udp_l4`, `lb_mirror` (no request mirroring; SPOE or tee at L4), `cache_purge` and `cache_stale_on_error` (the cache is a
small-object accelerator without invalidation or grace), `compress_brotli`/`compress_zstd` (slz gzip only),
`tracing_otel` (no OpenTelemetry exporter in the official build), `docker_label_discovery`.

## Gotchas we hit

1. `{ var(txn.x) -m int 1 }` - variable ACLs need an explicit match type; without `-m int` the comparison silently
   never matches.
2. `set-timeout server` is only valid in a backend section.
3. Filters: as soon as you declare one `filter`, declare **all** of them (cache, compression, bwlim) - implicit ones stop
   being added.
4. `jwt_payload_query('$.exp','int'),sub(txn.now)` is the expiry check; `date` must be stored in a variable first.
5. The Lua httpclient needs `httpclient.resolvers.id` (Docker DNS) and, for HTTPS, `httpclient.ssl.ca-file`.
6. The gRPC backend inherits `option httpchk` from `defaults`; override it with `option tcp-check`.
7. The image runs as `haproxy`, so binding :80 for HTTP-01 needs `net.ipv4.ip_unprivileged_port_start=0` in compose.
