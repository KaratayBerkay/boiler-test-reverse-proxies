# Apache httpd 2.4 - config walkthrough

Stack: `stacks/apache/` - image `httpd:2.4` (2.4.68, event MPM) + `lusotycoon/apache-exporter` sidecar. Files:
`httpd.conf` (started with `httpd-foreground -f /usr/local/apache2/lab/httpd.conf`), `lottery.txt` (rnd RewriteMap for
fault injection), `md-message.sh` (mod_md hook). Read this next to `stacks/apache/httpd.conf`.

## Modules and process model

Only the modules the lab needs are loaded: mpm_event, auth*, socache_shmcb, watchdog (hcheck), reqtimeout, filter,
deflate, **brotli**, **ratelimit**, mime, log_config + **logio** (`%O`), env, headers, unique_id, setenvif,
**remoteip** (PROXY protocol), proxy + proxy_http + **proxy_http2** + proxy_wstunnel + proxy_balancer +
**proxy_hcheck** + lbmethod_byrequests/bybusyness + slotmem_shm, ssl, http2, **md** (ACME), cache + cache_disk, unixd,
status, dir, alias, rewrite, **macro**.

Event MPM sized for the 4-core cpuset: `ServerLimit 4`, `ThreadsPerChild 256`, `MaxRequestWorkers 1024`,
`AsyncRequestWorkerFactor 8` (keep-alive connections are cheap in event), `MaxKeepAliveRequests 10000`. `Protocols h2
h2c http/1.1` enables HTTP/2 on TLS and h2c (Upgrade / prior knowledge) on plain ports.

JSON access log: `LogFormat "{\"time\":...\"bytes\":%O,\"duration_us\":%D,...\"request_id\":\"%{UNIQUE_ID}e\",\"cache\":\"%{cache-status}e\"...}" json`
to `/proc/self/fd/1`.

## Proxy defaults

```apache
ProxyRequests Off              # reverse proxy only
ProxyPreserveHost On           # upstream sees the client's Host
ProxyAddHeaders On             # X-Forwarded-For / -Host / -Server
ProxyTimeout 30
SSLProxyEngine On
ProxyHCExpr ok {%{REQUEST_STATUS} =~ /^[234]/}
```

Headers added everywhere: `RequestHeader set X-Lab-Proxy apache`, `X-Real-IP "%{REMOTE_ADDR}s"`, `X-Forwarded-Proto
"%{REQUEST_SCHEME}s"`, RFC 7239 `Forwarded`, `RequestHeader setifempty X-Request-ID "%{UNIQUE_ID}e"` (mod_unique_id);
`Header always unset X-Powered-By` + `Header unset X-Powered-By` (both tables).

## Balancers (`<Proxy "balancer://...">`)

| balancer | members / ProxySet | contract |
|---|---|---|
| `app` | app1..3 `hcmethod=GET hcuri=/healthz hcinterval=2 hcfails=2 hcpasses=2 hcexpr=ok retry=5 keepalive=On max=2000`, `lbmethod=byrequests` | default pool with active checks |
| `weighted` | `loadfactor=3` / `loadfactor=1` | weighted RR |
| `leastconn` | `lbmethod=bybusyness` | least-busy (marked ❌: with fast backends bybusyness behaves like round-robin) |
| `sticky` | `route=a1..a3`, `stickysession=lab_sticky`; the vhost adds `Header add Set-Cookie "lab_sticky=.%{BALANCER_WORKER_ROUTE}e" env=BALANCER_ROUTE_CHANGED` | cookie stickiness |
| `retry` | includes `app3:8099`, `retry=30` - a member that fails to connect goes into error state for 30 s | retry |
| `cb` | `failonstatus=500,502,503`, `retry=10` | passive ejection on 5xx |
| `health` | `hcinterval=1` | active checks |
| `canary` | `loadfactor=30/30/30/10` | 90/10 split |

`balancer://` params like `timeout=` are **balancer** params, not worker params - that is why `/timeout` uses a
direct IP-form worker (`http://10.77.0.11:8080/delay/5000 timeout=2 retry=0`): mod_proxy shares one worker per backend
URL, so a per-route timeout needs a URL nobody else uses.

## Cache, compression, limits

* `CacheEnable disk "/cacheable/"` + `/cacheable-short/`, `CacheRoot /var/cache/apache` (tmpfs, mode 1777),
  `CacheHeader On` (`X-Cache: HIT/MISS`), `CacheDetailHeader On`, `CacheStaleOnError On`, `CacheLock On`,
  `CacheQuickHandler Off` (so mod_headers runs on hits). No purge API (`cache_purge` unsupported; htcacheclean is offline).
* `AddOutputFilterByType DEFLATE ...` and `AddOutputFilterByType BROTLI_COMPRESS ...` - gzip + br, no zstd.
* `/bw`: `SetOutputFilter RATE_LIMIT` + `SetEnv rate-limit 500` (mod_ratelimit, KB/s).
* No request-rate or per-client connection limiting in the standard modules (mod_qos/mod_evasive are third-party).

## ACME (mod_md)

```apache
MDCertificateAuthority https://pebble:14000/dir
MDCAChallenges http-01
MDPortMap http:80 https:8443       # the vhost listens on 8443, ACME expects 443
MDStoreDir /md                     # tmpfs, writable by the daemon user
MDMessageCmd /usr/local/apache2/lab/md-message.sh
MDomain acme.lab
```

A new certificate only becomes active after a **graceful reload**. `MDMessageCmd` runs as the unprivileged child, so
`md-message.sh` drops `/md/reload.flag` and a root shell loop in the compose `command` turns it into `httpd -k
graceful`. Pebble's CA is mounted over `/etc/ssl/certs/ca-certificates.crt` because mod_md has no per-CA trust option.

## The default vhost: `<Macro AppRoutes>`

The same route set serves `*:80 *:8080`, `*:8443` (TLS) and `*:8082` (`RemoteIPProxyProtocol On`), so it is a
mod_macro macro used three times. Inside:

| contract | httpd |
|---|---|
| `DELETE /api/` | `RewriteCond %{REQUEST_METHOD} =DELETE` + `RewriteRule ^/api/ - [R=405,L]` |
| header / query routing | `RewriteCond %{HTTP:X-Canary} =1` / `RewriteCond %{QUERY_STRING} (^|&)beta=1(&|$)` + `RewriteRule ^/(.*)$ http://canary:8080/$1 [P,L]` |
| `/old/` | `RewriteRule ^/old/(.*)$ /new/$1 [PT,E=ROUTE:rewritten]` + `RequestHeader set X-Route "%{ROUTE}e" env=ROUTE` |
| `/redirect-me` | `Redirect permanent /redirect-me /landing` + `ProxyPass /redirect-me !` (ProxyPass would otherwise shadow it) |
| `/fault` | `RewriteMap lottery "rnd:.../lottery.txt"` (`x 0|0|0|0|1`) + `RewriteCond ${lottery:x} =1` -> 503. RewriteMaps are per vhost, hence inside the macro |
| `/cors` preflight | `RewriteCond %{REQUEST_METHOD} =OPTIONS` -> `[R=204,L]`; `<Location /cors>` adds the headers |
| `/api/` strip | `<Location /api/> RequestHeader set X-Route api` + `ProxyPass /api/ balancer://app/` (trailing slash strips) |
| `^/v[0-9]+/` | `<LocationMatch>` + `RequestHeader set X-Route versioned` |
| gRPC | `ProxyPass /grpc.health.v1.Health/ h2c://app1:9090/...` (mod_proxy_http2) |
| `/ws` | `ProxyPass /ws ws://app1:8080/ws` (mod_proxy_wstunnel) |
| `/sse` | `<Location /sse> ProxyPass balancer://app/sse` (event MPM streams) |
| `/allowed`, `/denied` | `Require ip 10.77.0.1` / `<RequireAll> Require all granted; Require not ip 10.77.0.0/24` |
| `/basic` | `AuthType Basic ... AuthUserFile /auth/htpasswd; Require valid-user` |
| `/upload` | `LimitRequestBody 1048576` **plus** `RewriteCond %{HTTP:Content-Length} >1048576 -> [R=413]` (LimitRequestBody is not enforced for streamed proxy bodies) |
| `/timeout` | direct worker with `timeout=2 retry=0` |
| `/conn-limited` | plain (unsupported) |
| `/error-page` | `<Location /error-page> ProxyErrorOverride On; ErrorDocument 503 /error.html` + `Alias /error.html /static/error.html` + `Header always set X-Error-Page custom` |
| `/secure` | four `Header always set` |
| `/static/` | `ProxyPass /static/ !` + `Alias /static/ /static/` |
| everything else | `ProxyPass / balancer://app/` + `ProxyPassReverse` |

## Other vhosts

* `a.lab` (`*:80 *:8080 *:8443`, app.lab cert) and `b.lab` (own cert, `ProxyPass / http://b1:8080/`).
* `redirect.lab` - `RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]`.
* one `*:8080` vhost per balancing host (`ProxyPass / balancer://weighted/` ...); `hash.lab`, `mirror.lab`, `pp.lab`,
  `auth.lab`, `jwt.lab` fall back to the plain pool (unsupported).
* `h2.lab` - `ProxyPass / h2c://app1:8080/`.
* `tls.lab` - `ProxyPreserveHost Off` (otherwise the client's Host becomes the SNI), `SSLProxyVerify require`,
  `SSLProxyCACertificateFile /certs/ca.crt`, `SSLProxyCheckPeerName on`, `ProxyPass / https://app1:8443/`.
* `mtls.lab` on `*:8444` - `SSLCACertificateFile`, `SSLVerifyClient require`, `SSLOptions +StdEnvVars`,
  `RequestHeader set X-Client-Cert-CN "%{SSL_CLIENT_S_DN_CN}s"`.
* `acme.lab` on `*:8443` - `SSLEngine on` with no certificate directives: mod_md supplies it.
* `*:9101` - `server-status`, `balancer-manager`, `md-status` (the exporter scrapes `/server-status?auto`).

## Operations

Reload = `httpd -k graceful` (SIGUSR1). Failover under load is handled by `retry=5` + hcheck.

## Unsupported here (and why)

`lb_hash_header`, `lb_mirror`, `proxy_protocol_upstream`, `tcp_l4`, `udp_l4`, `tls_passthrough_sni` (HTTP only),
`http3`, `cache_purge`, `compress_zstd`, `rate_limit`, `connection_limit`, `jwt_auth`, `forward_auth` (third-party
modules), `tracing_otel` (otel-webserver-module is a separate build), `docker_label_discovery`.

## Gotchas we hit

1. `%O` in LogFormat needs mod_logio; inline `#` comments on directive lines are parsed as arguments.
2. `ping=0` is not a valid worker parameter; params after a `balancer://` URL are balancer params.
3. The image has no curl: healthcheck via bash `/dev/tcp`.
4. `Redirect` was shadowed by `ProxyPass /` -> `ProxyPass /redirect-me !`.
5. `ProxyPreserveHost On` sends the client's Host as SNI to TLS upstreams -> off in the tls.lab vhost.
6. mod_md store and the disk cache must be writable by `daemon` -> tmpfs with mode 1777.
7. mod_md's MDMessageCmd cannot signal the parent -> flag file + root loop.
8. `LimitRequestBody` is not enforced for proxied bodies -> RewriteCond on Content-Length.
9. `RewriteMap` is not inherited into vhosts -> declared inside the macro.
