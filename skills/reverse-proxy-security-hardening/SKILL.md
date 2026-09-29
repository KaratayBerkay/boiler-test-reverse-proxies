---
name: reverse-proxy-security-hardening
description: Harden a reverse proxy or API gateway at the edge - trusted proxy / PROXY-protocol boundaries for the real client IP, X-Forwarded-* and RFC 7239 Forwarded, request ids, rate limiting and per-client concurrency limits, body size limits, timeouts, IP allow/deny lists, basic auth, JWT validation, forward auth (auth_request / ext_authz / forwardAuth), CORS, HSTS and security headers, hiding server/X-Powered-By, custom error pages, WebSocket/SSE and gRPC exposure - for NGINX, HAProxy, Caddy, Traefik, Envoy, Apache, Varnish, OpenResty, Kong, APISIX, Pingora and ATS. Use whenever a task mentions securing an ingress, auth at the proxy, rate limits, WAF-lite controls, header trust, DoS protection, or "clients see the wrong IP", even without the word proxy.
---

# Security hardening at the proxy

Verified by the reverse-proxies lab's headers/security probes on 12 proxies (`xff_headers`, `forwarded_rfc7239`,
`request_id`, `hide_server_headers`, `rate_limit`, `connection_limit`, `ip_allow/deny`, `basic_auth`, `jwt_auth`,
`forward_auth`, `body_limit`, `timeout_upstream`, `cors`, `security_headers`, `custom_error_page`). Per-proxy
constructs: `reverse-proxy-capability-mapping/references/headers-security.md`. This page is the checklist and the
reasoning.

## 1. Establish who the client is before anything else
- Decide the **trust boundary**: which peers may set `X-Forwarded-For` / send PROXY protocol. Configure it explicitly
  (`set_real_ip_from`, `trusted_proxies`, `forwardedHeaders.trustedIPs`, `xff_num_trusted_hops`, `KONG_TRUSTED_IPS`,
  `real-ip trusted_addresses`, `proxy_protocol_allowlist`). With no boundary, anyone can spoof their IP and defeat
  every IP-based rule below.
- PROXY protocol listeners must be **separate ports** that only the L4 balancer reaches; a public listener that
  "accepts PROXY protocol" lets any client claim any source address (Caddy `allow 0.0.0.0/0` in the lab is a lab
  setting).
- Behind Docker's userland proxy every client looks like the bridge gateway - test IP rules from inside the network or
  with PROXY protocol.
- Emit *both* `X-Forwarded-*` and RFC 7239 `Forwarded` only if upstreams read them; strip incoming copies of headers
  you set yourself (`X-Client-Cert-CN`, `X-Auth-User`, `X-JWT-Sub`) on listeners where they are not produced.

## 2. Limits: three kinds, all needed
| limit | protects against | proxy-side knob | lab observation |
|---|---|---|---|
| request rate per client | brute force, scraping, runaway clients | token bucket (nginx `limit_req burst nodelay`, Traefik `rateLimit`, Envoy `local_ratelimit`, APISIX `limit-req`, Kong `rate-limiting`, HAProxy stick table `http_req_rate`) | at 200 rps against a "10 r/s" limit for 10 s, bucket limiters (nginx, OpenResty, Traefik, Caddy, Envoy, Kong, APISIX, Pingora) passed 100-114 requests (10/s + burst) while HAProxy's and Varnish's sliding-window counters, which also count rejected requests, passed **10 in total** - the client is locked out until it slows down; Envoy's local limit is per route unless descriptors are used |
| concurrency per client | slowloris-style, hung backends | nginx `limit_conn`, HAProxy `conn_cur`, Traefik `inFlightReq`, APISIX `limit-conn`, Pingora `Inflight` | not available in Caddy, Envoy (per listener only), Apache core, Varnish, Kong OSS |
| body size | memory/disk exhaustion, upload abuse | `client_max_body_size`, `req.hdr_val(content-length)`, `request_body max_size`, `buffering.maxRequestBodyBytes`, `BufferPerRoute`, `request-size-limiting`, `client-control` | Apache's `LimitRequestBody` is not enforced on streamed proxy bodies - add a Content-Length rewrite rule; chunked uploads bypass Content-Length checks everywhere - buffer or enforce at the app |
Add **timeouts** per route (read/response-header 2-30 s, connect 1-3 s) and header-read timeouts (`client_header_timeout`,
`timeout http-request`, `RequestReadTimeout`) - the c10k scenario holds 10 000 idle connections; without timeouts they
are free for the attacker.

## 3. Authentication at the edge
- **Basic auth** is fine for admin paths over TLS; store bcrypt/apr1 hashes (Envoy's filter only reads `{SHA}` htpasswd).
- **JWT**: validate signature *and* `exp` (and `nbf`, `iss`, `aud`); HS256 shared secrets belong in files/secrets, not
  in the config text (the lab inlines them for reproducibility - do not copy that). Forward the subject as a header
  (`X-JWT-Sub`) and strip the same header from inbound requests. Where the proxy has no JWT (Traefik OSS, Apache,
  ATS) use forward auth or an OIDC plugin rather than home-made checks.
- **Forward auth** (`auth_request`, Lua httpclient, `forward_auth`, `forwardAuth`, `ext_authz`, `forward-auth`):
  send only what the authorizer needs (`allowed_headers`), copy back only allowlisted headers
  (`authResponseHeaders`, `allowed_upstream_headers`), set a short timeout and **fail closed**
  (`failure_mode_allow: false`, `status_on_error`). Cache decisions at the authorizer, not the proxy, unless the proxy
  supports keyed caching of auth responses.
- Scope auth filters to the routes that need them: Envoy `ExtensionWithMatcher`/per-route configs, Kong/APISIX
  route-level plugins, Caddy `handle` blocks, HAProxy ACL conditions - a global auth filter that "usually" skips is a
  bug waiting to happen.

## 4. Headers and responses
- Remove `Server`/`X-Powered-By` where possible (`server_tokens off`, `header_down -Server`, `ServerTokens Prod`,
  `response_server_str`) - full removal needs headers-more (nginx) or is impossible (some keep the product name).
- Security headers on TLS responses: HSTS (`max-age=31536000; includeSubDomains` once you are sure), `X-Content-Type-Options
  nosniff`, `X-Frame-Options DENY` (or CSP `frame-ancestors`), `Referrer-Policy`. nginx: `add_header ... always` or 4xx/5xx
  responses lose them; Traefik adds HSTS only on TLS unless `forceSTSHeader`.
- CORS: answer preflights at the proxy with an explicit origin list; `Access-Control-Allow-Origin: *` with credentials is
  invalid and browsers reject it. Do not reflect `Origin` blindly on authenticated routes.
- Custom error pages hide stack traces from upstreams (`proxy_intercept_errors`, `errors` middleware, `ProxyErrorOverride`,
  Lua/post-function body replacement); ATS cannot replace origin bodies.

## 5. Protocol exposure
- Enable h2c only on internal listeners; on public ports offer h2 via ALPN over TLS only.
- WebSocket routes need their own idle timeouts (`proxy_read_timeout 300s`, `timeout tunnel`) and should not inherit body
  buffering/compression filters (Envoy hung until the upgrade chain was router-only).
- gRPC through the proxy: limit `max_concurrent_streams`, and remember nginx opens ~one upstream connection per stream.
- Admin/metrics/status endpoints (`stub_status`, HAProxy stats, Caddy admin API, Envoy admin, `server-status`, Kong admin,
  APISIX control API, `traffic_ctl`) on **separate ports** that are not published beyond the management network; the
  lab publishes them for probing only.

## 6. Verify with probes, not by reading
```bash
curl -s -H 'X-Forwarded-For: 1.2.3.4' http://proxy/ | jq .headers            # must NOT show 1.2.3.4 as the client
for i in $(seq 30); do curl -s -o /dev/null -w '%{http_code} ' http://proxy/limited; done; echo   # 429s appear
curl -s -o /dev/null -w '%{http_code}\n' -H 'Content-Length: 2000000' -X POST http://proxy/upload   # 413
curl -s -X DELETE http://proxy/api/x -o /dev/null -w '%{http_code}\n'       # 405 from the proxy, not the app
curl -sI https://proxy/secure | grep -iE 'strict-transport|x-frame|nosniff|referrer'
curl -s -H 'Authorization: Bearer expired.token.here' http://jwt.lab/ -o /dev/null -w '%{http_code}\n'   # 401
```
