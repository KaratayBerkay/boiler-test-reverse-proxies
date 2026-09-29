# Traefik v3 - config walkthrough

Stack: `stacks/traefik/` - image `traefik:v3` (3.7). Two layers of configuration:

* `traefik.yml` - **static**: entrypoints, providers, observability, ACME resolvers. Changing it needs a restart.
* `dynamic/dynamic.yml` - **dynamic**: routers, middlewares, services, TLS. The file provider watches the directory, so
  editing it *is* the reload (`reload_cmd` just bumps the `# reload-stamp:` comment).
* Docker labels on `whoami` in `shared/compose.yaml` - the Docker provider turns them into a router for `whoami.lab`.

## Static: entrypoints

| entrypoint | address | notes |
|---|---|---|
| `web80` | `:80` | ACME HTTP-01 + redirect demo |
| `web` | `:8080` | h1 + h2c (cleartext HTTP/2 is always on); `forwardedHeaders.trustedIPs` |
| `websecure` | `:8443` | `http3: { advertisedPort: 8443 }` -> h1/h2/h3 |
| `mtls` | `:8444` | routers on it use `tls: { options: mtls }` |
| `passthrough` | `:8445` | TCP routers with `tls.passthrough` |
| `pp` | `:8082` | `proxyProtocol: { trustedIPs: [0.0.0.0/0] }` - accepts PROXY protocol |
| `tcp` / `udp` | `:9000` / `:9001/udp` | L4 routers |
| `metrics` / `traefik` | `:9100` / `:9101` | Prometheus; API + dashboard (`api.insecure: true`), `/ping` |

Providers: `file: { directory: /etc/traefik/dynamic, watch: true }` and `docker: { endpoint: unix:///var/run/docker.sock,
exposedByDefault: false, network: pxlab, defaultRule: "Host(`{{ .Name }}.lab`)" }`. Observability: JSON `log` and
`accessLog` (keeping `X-Request-ID`), `metrics.prometheus` with entrypoint + service labels, `tracing.otlp.http` to Jaeger
with `sampleRate: 0.001` (parent-based, so the tracing probe's sampled parent is always traced). ACME:
`certificatesResolvers.pebble.acme` with `caServer: https://pebble:14000/dir`, `httpChallenge.entryPoint: web80`,
`storage: /data/acme.json`; the environment variable `LEGO_CA_CERTIFICATES=/certs/pebble-ca.pem` makes lego trust Pebble.
`serversTransport` defaults: `maxIdleConnsPerHost: 200`, `dialTimeout: 3s`, `responseHeaderTimeout: 30s`.

## Dynamic: routers

Routers combine a rule, a priority, the entrypoints they listen on, a middleware chain and a service. Two things shape
the file:

1. **A router with `tls:` only matches TLS connections**, so every host route exists twice: `a` (entrypoints web80/web)
   and `a-tls` (websecure, `tls: { options: default }`). Path routers list `[web, websecure]` without `tls:` and rely on
   the entrypoint-level TLS store (`tls.stores.default.defaultCertificate`).
2. Priority decides between overlapping rules: `catch-all` (`PathPrefix(/)`, priority 1), path routes 50, `api-delete`
   60 (`Method(DELETE) && PathPrefix(/api/)`), header/query canary 55, host routes 100.

| contract | router rule -> middlewares -> service |
|---|---|
| `/api/*` | `PathPrefix(/api/)` -> `strip-api` (`stripPrefix`), `route-api` -> `app`; DELETE -> `to-405` (`replacePath /405`) -> `static` origin returns 405 |
| `^/v[0-9]+/` | `PathRegexp` -> `route-versioned` |
| `/old/` | `rewrite-old` (`replacePathRegex ^/old/(.*) -> /new/$1`) |
| `/redirect-me` | `redirect-landing` (`redirectRegex`, `permanent: true`) |
| `X-Canary: 1`, `?beta=1` | `Header(...)`, `Query(...)` -> `canary` service |
| gRPC | `PathPrefix(/grpc.health.v1.Health/)` -> service `grpc` (`url: h2c://app1:9090`) |
| `/limited` | `rateLimit { average: 10, period: 1s, burst: 5 }` |
| `/conn-limited` | `inFlightReq { amount: 3 }` + `replacePath /delay/1000` |
| `/allowed`, `/denied` | `ipAllowList` (`10.77.0.1/32`; the deny list is an allow-list of an unused range) |
| `/basic` | `basicAuth { users: [lab:$apr1$...] }` |
| `/upload` | `buffering { maxRequestBodyBytes: 1048576 }` -> 413 |
| `/timeout` | service `app-slow-timeout` with `serversTransport: timeout-2s` (`responseHeaderTimeout: 2s`) |
| `/error-page` | `errors { status: [500-599], service: static, query: /error.html }` |
| `/cors` | `headers { accessControlAllowOriginList, accessControlAllowMethods, ... }` |
| `/secure` | `headers { stsSeconds, forceSTSHeader: true, contentTypeNosniff, frameDeny, referrerPolicy }` |
| `/compressible` | `compress { encodings: [zstd, br, gzip], minResponseBodyBytes: 256 }` |
| `/ws`, `/sse`, rest | `catch-all` with the `retry` middleware (WebSocket and streaming need nothing special; without `retry` the first chaos run returned 451 x 502 while app2 was down) |

`common` is a `chain` middleware wrapping `proxy-headers` (`customRequestHeaders X-Lab-Proxy`, `customResponseHeaders
X-Powered-By: ""` - an empty value deletes the header - and `Alt-Svc`). Traefik adds `X-Forwarded-*` and `X-Real-Ip`
itself; it does **not** generate RFC 7239 `Forwarded` or a request id (both declared unsupported).

Host routers: `a`/`b` (+`-tls`), `redirect-https` (`redirectScheme https permanent`), one router per load-balancing
host, `auth` (`forwardAuth { address: http://app1:8080/auth, authResponseHeaders: [X-Auth-User, X-Auth-Groups] }`),
`mtls` (entrypoint mtls, `tls.options: mtls`, `passTLSClientCert { info.subject.commonName }` -> the CN arrives in
`X-Forwarded-Tls-Client-Cert-Info`), `acme` (`tls: { certResolver: pebble }`).

## Dynamic: services

```yaml
app:            loadBalancer.servers app1..3 + healthCheck { path: /healthz, interval: 2s }   # active checks
weighted:       servers with `weight: 3` / `weight: 1`
leastconn:      strategy: p2c            # power-of-two-choices approximates least connections (3.x)
sticky:         sticky.cookie { name: lab_sticky, httpOnly: true }
retry:          servers incl. app3:8099 + `retry` middleware (attempts 3)
cb:             app1, app2, flaky + retry middleware (no per-server ejection -> lb_outlier_ejection unsupported)
health:         healthCheck interval 1s
canary-split:   weighted.services [{app, 90}, {canary, 10}]      # traffic split between services
mirror:         mirroring { service: app, mirrorBody: true, mirrors: [{shadow, 100}] }
h2:             url: h2c://app1:8080
tls-upstream:   serversTransport: backend-tls { serverName: backend.lab, rootCAs: [/certs/ca.crt] }
```

L4: `tcp.routers.tcp9000` (`HostSNI(*)`), `passthrough` (`HostSNI(passthrough.lab)`, `tls.passthrough: true`),
`udp.routers.udp9001`. TLS: two certificates (SNI picks b.lab's), `stores.default.defaultCertificate`, options
`default` (TLS 1.2+, ALPN h2/http1.1) and `mtls` (`clientAuth.clientAuthType: RequireAndVerifyClientCert`).

## Operations

* Reload = file watch; the chaos run shows 0 failed requests while routers are swapped.
* Metrics on :9100; `/api/rawdata` and the dashboard on :9101; healthcheck `traefik healthcheck` uses `ping`.

## Unsupported here (and why)

`lb_hash_header` (wrr/p2c/sticky only), `lb_outlier_ejection` (circuitBreaker is per service), `proxy_protocol_upstream`
(TCP services only), `cache_*` (no cache in OSS), `forwarded_rfc7239`, `request_id`, `jwt_auth` (plugin or Enterprise),
`fault_injection`, `bandwidth_limit`, `static_files` (no file server).

## Gotchas we hit

1. Routers with `tls:` never see plain HTTP -> duplicate routers per scheme.
2. `chain` takes `middlewares:`, not `steps:`.
3. HSTS is only added to TLS responses unless `forceSTSHeader: true`.
4. The container healthcheck (`traefik healthcheck`) needs `ping:` enabled.
5. `lab.yaml` reload command with `$(date)` inside YAML needs careful quoting - the harness runs `["shell", "..."]`
   commands in the stack directory.
