# Proxy matrix - what each proxy is, how it is configured, where it is strong

The probe-level capability matrix (69 rows x 12 proxies, generated from results) lives in
[`../results/SUMMARY.md`](../results/SUMMARY.md); the numbers in [`findings.md`](findings.md). This page is the
higher-level view for **choosing** a proxy and knowing what you sign up for. Every claim below was exercised in this lab
(`stacks/<key>/`, `docs/configs/<key>.md`).

## The twelve stacks

| key | proxy | language / model | configured through | reload model | best at | pain points seen in the lab |
|---|---|---|---|---|---|---|
| `nginx` | NGINX 1.29 OSS (`nginx:1.29-otel`) | C, event loop, N workers | `nginx.conf` (declarative, `map`/`split_clients` instead of `if`) | SIGHUP: new workers, old drain (idle keep-alive connections closed) | raw throughput per core, static+proxy+cache in one process, HTTP/3, stream L4, huge ecosystem | active health checks / sticky / purge / JWT are NGINX Plus; `proxy_set_header` inheritance; brotli needs a rebuild |
| `haproxy` | HAProxy 3.4 LTS | C, event loop, threads | `haproxy.cfg` (frontend rules + backends, ACLs, stick tables) | SIGUSR2 master-worker with fd hand-over (seamless) | L4/L7 load balancing depth (health checks, stick tables, `observe layer7`), runtime API, QUIC, ACME, Lua | no UDP, no mirroring, no purge/stale cache, gzip only, no OTel |
| `caddy` | Caddy 2 (xcaddy build) | Go | `Caddyfile` (site blocks + directives, fixed directive order) | admin API (`caddy reload`), zero-downtime | automatic HTTPS, simplest config, h1/h2/h2c/h3 by default, JSON config API; plugins via xcaddy | no built-in cache/rate-limit/L4/JWT (plugins), no mirroring, no bandwidth/conn limits; the Souin cache plugin collapsed to 1.7k rps on a hot key; passive health marked all upstreams down in the c10k storm |
| `traefik` | Traefik v3.7 | Go | static `traefik.yml` + dynamic providers (file, Docker labels, k8s) | file watch / provider events | dynamic environments (containers come and go), Docker label discovery, mirroring, weighted services, dashboard | no cache, no JWT, no `Forwarded`/request-id, no file serving, routers with `tls:` only match TLS |
| `envoy` | Envoy 1.39 | C++ | xDS (here: watched LDS/CDS/RDS YAML files) - verbose typed config | xDS updates, hot restart | filter chain depth (ext_authz, jwt_authn, rbac, local_ratelimit, fault, bandwidth, compressors, Lua), outlier detection, weighted clusters, mirroring, h2/h3/gRPC first-class, UDP | YAML volume (1700 generated lines), alpha cache filter unusable, no ACME, per-listener connection limits |
| `apache` | Apache httpd 2.4 | C, event MPM (threads) | `httpd.conf` (modules + vhosts + `<Location>` + macros) | graceful (SIGUSR1) | mod_proxy_balancer + hcheck, mod_cache_disk, mod_md (ACME), mod_ratelimit, mTLS, when httpd is already there | HTTP-only (no L4/h3), no rate/conn limiting or JWT/forward-auth in core, bybusyness ~ RR, mod_md needs graceful restart |
| `varnish` | Varnish 8 + hitch | C, VCL compiled to C | `default.vcl` (procedural) + `hitch.conf` | `varnishreload` (vcl.load/use) | caching semantics (grace/stale, purge, streaming), programmable request flow, vmods (directors, saintmode, vsthrottle, digest, reqwest) | no TLS (hitch), no HTTP/2 to backends, no L4/h3/gRPC/ACME, gzip only |
| `openresty` | OpenResty 1.27 | C + LuaJIT | `nginx.conf` + Lua blocks | SIGHUP | everything nginx does plus Lua: JWT, limits, forward auth, real purge, ACME client, Prometheus without exporters | Lua code is your code (tests!), same upstream limits as nginx |
| `kong` | Kong Gateway 3.9 OSS | OpenResty + Lua plugins | DB-less declarative `kong.yml` (services/routes/upstreams/consumers/plugins) | `POST /config` on the admin API | API-gateway model: consumers + credentials, plugin ecosystem (rate limit, JWT, ACME, proxy-cache, OTel, prometheus), expressions router, stream routes | Enterprise-only mTLS/forward-auth/OIDC, no h3, no mirroring, gzip only, `kong reload` != config reload |
| `apisix` | Apache APISIX 3.15 | OpenResty + Lua plugins | `apisix.yaml` standalone (or etcd + admin API) | file mtime watch | widest OSS plugin coverage in the lab (forward-auth, jwt, limit-req/conn, proxy-cache disk with PURGE, traffic-split, mirror, brotli, OTel, h3), stream routes, mTLS per SNI | schema errors silently drop routes, no ACME client, no SNI passthrough |
| `pingora` | Pingora 0.9 (custom Rust) | Rust, async | code (`ProxyHttp` trait) | socket hand-off upgrade | you control every byte and policy; excellent per-core throughput; cache/lb/limits as libraries | you write and maintain a proxy; no h3/UDP/ACME/OTel/brotli in this build |
| `ats` | Apache Traffic Server 9.2 | C++ | `records.config` + `remap.config` + `strategies.yaml` + plugins | `traffic_ctl config reload` | CDN-style caching (RAM/disk), remap rules at scale, header_rewrite, SNI tunnels; fast once tuned (28k rps h1, 52k cache hits) | weakest reverse-proxy feature set here (27 unsupported): no active health, no h2 to origins, no h2c/h3, no ACME/JWT, first-match remap order; default cache-lock timers serialize hot URLs |

## Capability families - who does what natively

Legend: **●** native · **○** via an official/first-party module or plugin (built into the image or added with the
project's own build tool) · **✗** not available in the open-source edition (see the stack's `lab.yaml` for the reason).

| family | nginx | haproxy | caddy | traefik | envoy | apache | varnish | openresty | kong | apisix | pingora | ats |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| host/path/regex/header/query/method routing | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | header/query ✗ |
| round-robin / weighted / least-conn | ● | ● | ● | p2c | ● | busyness≈RR | no least-conn | ● | ● | ● | no least-conn | RR only |
| consistent hash / sticky cookie | ● OSS trick | ● | ● | sticky only | ● | sticky only | ● | ● OSS trick | ● | ● | ● | ✗ |
| active health checks | ✗ Plus | ● | ● | ● | ● | ● hcheck | ● probes | ✗ | ● | ● | ● | ✗ (ATS 10) |
| passive ejection / retries | ● | ● | ● | retry only | ● | ● failonstatus | ● saintmode | ● | ● | ● | ● | retries only |
| canary split / mirroring | ● / ● | weights / ✗ | weights / ✗ | ● / ● | ● / ● | weights / ✗ | ● / ✗ | ● / ● | weights / ✗ | ● / ● | weights / ✗ | ✗ / ● multiplexer |
| HTTP/2, h2c, HTTP/3 | ● ● ● | ● ● ● | ● ● ● | ● ● ● | ● ● ● | ● ● ✗ | ● ● ✗ | ● ● ● | ● ● ✗ | ● ● ● | ● ● ✗ | ● ✗ ✗ |
| WebSocket / SSE / gRPC | ● | ● | ● | ● | ● | ● | ● / ● / ✗ | ● | ● | ● | ● | ● / ● / ✗ |
| h2c, TLS, PROXY protocol to upstream | gRPC only / ● / ✗ | ● ● ● | ● ● ● | ● ● tcp-only | ● ● ● | ● ● ✗ | reqwest / ● / ● | gRPC only / ● / ✗ | gRPC only / ● / ✗ | gRPC only / ● / ✗ | ● ● ✗ | ✗ ● ✗ |
| accept PROXY protocol | ● | ● | ● | ● | ● | ● remoteip | ● | ● | ● | ● | ✗ | ● |
| TCP / UDP / SNI passthrough | ● ● ● | ● ✗ ● | ● ● ● (l4) | ● ● ● | ● ● ● | ✗ | ✗ | ● ● ● | ● ● ● | ● ● ✗ | ● ✗ ✗ | ✗ ✗ tunnel |
| TLS 1.3, SNI certs, mTLS | ● | ● | ● | ● | ● | ● | hitch | ● | ● (mTLS ✗) | ● | ● | ● |
| ACME built in | ● (1.29) | ● (3.2+) | ● | ● | ✗ | ● mod_md | ✗ | ○ lua-resty-acme | ● plugin | ✗ | ✗ | ✗ |
| cache hit / purge / stale-on-error | ● / refresh / ● | ● / ✗ / ✗ | ○ Souin ● ● | ✗ | ✗ (alpha) | ● / ✗ / ● | ● ● ● | ● ● ● | ● ● ✗ | ● ● ✗ | ● / ✗ / ✗ | ● ● ● |
| gzip / brotli / zstd | ● ✗ ✗ | ● ✗ ✗ | ● ○ ● | ● ● ● | ● ● ● | ● ● ✗ | ● ✗ ✗ | ● ✗ ✗ | ● ✗ ✗ | ● ● ✗ | ● ✗ ● | ● ✗ ✗ |
| X-Forwarded-*, Forwarded, request id | ● | ● | ● | XF only | ● | ● | ● | ● | ● | ● | ● | ● |
| rate limit / connection limit | ● ● | ● ● | ○ / ✗ | ● ● | ● / ✗ | ✗ ✗ | ● / ✗ | ● ● | ● / ✗ | ● ● | ● ● | concurrency only |
| IP allow/deny, basic auth | ● | ● | ● | ● | ● rbac | ● | ● | ● | ● | ● | ● | ● |
| JWT / forward auth | njs / ● | ● / Lua | ○ / ● | ✗ / ● | ● / ● | ✗ / ✗ | VCL / reqwest | ● / ● | ● / ✗ | ● / ● | ● / ✗ | ✗ / ✗ |
| body limit / timeout / fault / bandwidth | ● ● ● ● | ● ● ● ● | ● ● ✗ ✗ | ● ● ✗ ✗ | ● ● ● ●* | ● ● ● ● | ● ● ● ✗ | ● ● ● ● | ● ● ● ✗ | ● ● ● ● | ● ● ● ✗ | ● ● ● ✗ |
| static files / custom error page / CORS / security headers | ● | ● | ● | ✗ / ● / ● / ● | ● | ● | ● | ● | ● | ● | ● | ● / ✗ / ● / ● |
| JSON access log / Prometheus / OpenTelemetry | ● / exporter / ● | ● / ● / ✗ | ● / ● / ● | ● / ● / ● | ● / ● / ● | ● / exporter / ✗ | ● / exporter / ✗ | ● / ● / ✗ | ● / ● / ● | ● / ● / ● | ● / ● / ✗ | ● / ✗ / ✗ |
| admin/status API, hot reload | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Docker label discovery | ✗ | ✗ | ✗ | ● | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

\* Envoy's bandwidth limiter passes bytes but its ~1 s burst made the lab's threshold fail (❌ in the matrix).

## Choosing

* **"I need a fast, boring edge for a web app"** - nginx (or OpenResty when you will need scripting later). Highest
  requests-per-core in the lab, one process for static files + proxy + cache + TLS + h3.
* **"I need a load balancer first, HTTP features second"** - HAProxy: the richest health-check / stick-table /
  connection-management model, seamless reloads, runtime API, QUIC. Accept the lack of UDP, cache and OTel.
* **"Certificates and config should manage themselves"** - Caddy for small fleets (automatic HTTPS, tiny config);
  Traefik when routes come from container/Kubernetes metadata.
* **"I need a programmable data plane with policy filters"** - Envoy (ext_authz, jwt_authn, rbac, outlier detection,
  xDS control planes, gRPC/h3 first-class). Budget time for the YAML.
* **"It is an API gateway: consumers, credentials, plugins, per-route policies"** - APISIX (widest OSS plugin coverage
  here) or Kong (DB-less declarative model, expressions router). Both are OpenResty underneath.
* **"Caching is the product"** - Varnish (grace, purge, VCL) for HTTP/1 origins with hitch in front; ATS when you want a
  CDN-style cache with remap rules and can live with its 9.x load-balancing limits.
* **"httpd is already there"** - Apache mod_proxy does more than people expect (balancer, hcheck, cache, md/ACME, brotli),
  but has no L4, no h3 and no rate limiting in core.
* **"We want to own the proxy"** - Pingora: a few hundred lines of Rust gave 54 verified capabilities at nginx-class
  throughput; everything missing is missing from the code, not the framework.

## Deployment shape (from the compose files)

| | nginx | haproxy | caddy | traefik | envoy | apache | varnish | openresty | kong | apisix | pingora | ats |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| image | official `nginx:1.29-otel` | official `haproxy:lts` | custom (xcaddy) | official `traefik:v3` | official `envoyproxy/envoy` | official `httpd:2.4` | official `varnish:8.0` + `hitch` | custom (opm) | official `kong:3.9` | official `apache/apisix` | custom (cargo) | custom (Ubuntu pkgs) |
| containers | 2 (exporter) | 1 | 1 | 1 | 1 | 2 (exporter) | 4 (hitch, log, exporter) | 1 | 1 | 1 | 1 | 1 |
| unprivileged :80 | root workers | `ip_unprivileged_port_start=0` | caddy binds | root | root | root parent | root | root | `ip_unprivileged_port_start=0` | root | root | trafficserver user (8080 only + :80) |
| writable state | cache volume | none | `/data` (certs) | `/data/acme.json` | none | tmpfs `/md`, cache | VSM dir (shared) | cache volume | shm | cache dir | none | cache file |
| config mount | directory | directory | directory | file + dir | directory (watched) | directory | file | directory | generated file | generated file | directory | files |
