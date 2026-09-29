---
name: reverse-proxy-capability-mapping
description: Map any reverse-proxy requirement (routing, load balancing, health checks, retries, canary/mirroring, HTTP/2/3, WebSocket, gRPC, TLS/mTLS/SNI/ACME, caching, compression, forwarded headers, rate/connection/body limits, auth, CORS, static files, error pages, logging, metrics, tracing, reload) to the exact native construct in NGINX, HAProxy, Caddy, Traefik, Envoy, Apache httpd, Varnish, OpenResty, Kong, APISIX, Pingora or Apache Traffic Server - or to an honest "not in the open-source edition, do X instead". Use this whenever someone asks how to do something in a specific proxy, wants to port a config between proxies, compares proxies, or asks "can nginx/haproxy/caddy/traefik/envoy/... do X?", even when they don't say "reverse proxy". Every mapping was verified by a probe in the reverse-proxies lab.
---

# Reverse-proxy capability mapping

Twelve proxies were configured to one identical contract and probed 69 ways (`reverse-proxies/docs/contract.md`,
`results/SUMMARY.md`). This skill is the lookup table that came out of it: **capability -> construct per proxy**, with
the traps that cost hours. Use it to answer "how do I do X in Y", to port configs, and to say *no* accurately.

## How to use it

1. Identify the capability group and read only that reference file:
   - `references/routing.md` - host/path/regex/rewrite/redirect/header/query/method routing
   - `references/load-balancing.md` - algorithms, hashing, stickiness, retries, outlier ejection, active health, canary, mirroring, keep-alive
   - `references/protocols.md` - HTTP/2, h2c, HTTP/3, WebSocket, SSE, gRPC, h2/TLS/PROXY-protocol upstreams, TCP/UDP/SNI passthrough
   - `references/tls.md` - termination, TLS 1.3, SNI certs, mTLS, ACME
   - `references/caching-compression.md` - cache hit/purge/stale, gzip/brotli/zstd
   - `references/headers-security.md` - forwarded headers, request id, rate/conn/body limits, timeouts, fault, bandwidth, IP lists, basic/JWT/forward auth, CORS, security headers, static files, error pages
   - `references/operations.md` - JSON logs, Prometheus, OpenTelemetry, admin API, reload, Docker discovery
2. Take the construct for the target proxy **and the caveat next to it** - the caveats are where configs break.
3. If the cell says *unsupported*, tell the user plainly and offer the listed alternative (plugin, Plus/Enterprise
   edition, a sidecar, or a different proxy). Do not invent a directive: every "not available" below was confirmed
   against the current docs and the lab run.

## Which proxy for which job (verified, not marketing)

| need | reach for | because |
|---|---|---|
| highest requests per core, static + proxy + cache + TLS/h3 in one binary | nginx / OpenResty | measured top of the throughput table; OpenResty adds Lua for what OSS nginx lacks (JWT, limits, purge, ACME) |
| load balancer first (health checks, stick tables, connection control), seamless reloads | HAProxy | richest LB model, master-worker reload with fd hand-over, runtime API; no UDP/cache purge/OTel |
| automatic HTTPS with the smallest config | Caddy | ACME by default, h1/h2/h2c/h3 on; plugins via xcaddy for rate limit / L4 / JWT / cache |
| routes derived from container or cluster metadata | Traefik | the only one with a Docker-label provider here; mirroring + weighted services built in; no cache/JWT/file serving |
| policy filters and a control plane (xDS), gRPC/h3 native | Envoy | ext_authz/jwt_authn/rbac/local_ratelimit/fault/lua per route, outlier detection; verbose YAML |
| API gateway: consumers, credentials, per-route plugins | APISIX (widest OSS plugin set) or Kong (DB-less declarative model) | both OpenResty-based; Kong keeps mTLS/OIDC/forward-auth for Enterprise |
| caching as the product | Varnish (VCL, grace, purge) or ATS (CDN-style, remap) | Varnish needs hitch for TLS; ATS 9 has weak LB (no active checks, no weighted RR) |
| httpd already deployed | Apache mod_proxy | balancer + hcheck + cache_disk + mod_md; no L4/h3/rate limiting in core |
| own the data plane | Pingora (Rust) | ~780 lines gave 54 verified capabilities at nginx-class throughput |

## The ten traps that are not in the docs

1. **nginx `proxy_set_header` does not inherit** once a location sets any header - keep the common set in an included
   snippet. Same for OpenResty.
2. **Traefik routers with `tls:` only match TLS**; plain HTTP needs a second router. HSTS is TLS-only unless
   `forceSTSHeader: true`.
3. **Caddy evaluates directives in a fixed order**, not file order: a bare `respond` runs after every `handle` block;
   plugin directives need `order ... before ...`; a host-less `:8443 { tls }` pins its cert on every SNI.
4. **HAProxy** ACLs on variables need `-m int/str`; `set-timeout` is backend-only; declaring one `filter` means
   declaring all of them.
5. **Envoy** yaml-cpp has no merge keys; the alpha cache filter breaks route-level behaviour; durations need units.
6. **Kong**: `kong reload` does not re-read DB-less config (`POST /config` does); `strip_path` defaults to true;
   `hash_on_header` uses nginx-variable spelling (`x_user`); the ACME plugin appends `/directory`.
7. **APISIX**: a schema violation silently drops that route; `enable_http2` is at the `apisix:` level; OTel collector
   settings live in `plugin_metadata`.
8. **Apache**: params after a `balancer://` URL are balancer params (a per-route `timeout=` needs its own worker
   URL); `LimitRequestBody` is not enforced for streamed proxy bodies; mod_md needs a graceful restart to activate.
9. **ATS**: remap = first match in file order and the request port is part of the match; strategies override
   `set-destination`; `@strategy='x'` keeps the quotes.
10. **Everything nginx-based** (nginx, OpenResty, Kong, APISIX): one retried slow request with `max_fails=1` can mark
    the whole pool down - disable next-upstream on slow routes.

## Files
- `references/*.md` - the mapping tables (one per capability group), each row = one probe id from the lab.
- Full configs that implement every row: `reverse-proxies/stacks/<proxy>/` with walkthroughs in `docs/configs/`.
