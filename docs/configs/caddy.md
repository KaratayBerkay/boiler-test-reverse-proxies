# Caddy 2 - config walkthrough

Stack: `stacks/caddy/` - custom image `pxlab-caddy:latest` built with **xcaddy** (`Dockerfile`):
`caddy-ratelimit`, `caddy-l4` (TCP/UDP/SNI passthrough), `caddy-jwt`, `caddy-brotli`, `cache-handler` (Souin).
Plain Caddy has none of those. Config: `Caddyfile` (`caddy run --config /etc/caddy/Caddyfile --adapter caddyfile`).

Read this next to `stacks/caddy/Caddyfile`.

## Global options

```caddyfile
{
	admin 0.0.0.0:2019             # config API -> :9101 on the host (GET /config/, POST /load)
	auto_https disable_redirects   # ACME management stays on (acme.lab), no automatic :80 -> https redirects
	http_port 80                   # HTTP-01 challenges are solved here
	https_port 443
	default_sni app.lab            # clients without SNI get app.lab's certificate
	metrics                        # Prometheus on the admin endpoint (and :9100 below)
	log { output stdout  format json }
	servers { protocols h1 h2 h2c h3  trusted_proxies static 10.77.0.0/24  client_ip_headers X-Forwarded-For }
	servers :8082 { listener_wrappers { proxy_protocol { timeout 5s  allow 0.0.0.0/0 } }  protocols h1 h2c }
	order rate_limit before basic_auth
	order jwtauth before basic_auth
	order cache before rewrite
	cache { ttl 60s  stale 300s  default_cache_control public  api { souin } }
	layer4 { :9000 { route { proxy app1:8080 } }  udp/:9001 { route { proxy udp/app1:9002 } }
	         :8445 { @pass tls sni passthrough.lab  route @pass { proxy app1:8443 } ... } }
}
```

* Plugin directives have no place in Caddy's built-in directive order, so `order ... before ...` is mandatory for
  `rate_limit`, `jwtauth` and `cache`.
* `servers :8082 { listener_wrappers { proxy_protocol } }` is how a listener **accepts** PROXY protocol
  (`proxy_protocol_accept`).
* `layer4` is caddy-l4's global app: TCP (`tcp_l4`), UDP (`udp_l4`) and TLS passthrough by SNI (`tls_passthrough`).
* Tracing is configured through the environment (`OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318`,
  `OTEL_TRACES_SAMPLER=parentbased_traceidratio`, `OTEL_TRACES_SAMPLER_ARG=0.001`) plus `tracing { span pxlab }` in the site.

## Snippets

* `(proxy_headers)` - `header_up X-Lab-Proxy / X-Real-IP / Forwarded / X-Request-ID {http.request.uuid}`,
  `header_down -X-Powered-By -Server`. Caddy adds `X-Forwarded-For/Proto/Host` by itself.
* `(pool_app)` - `lb_policy round_robin`, `lb_retries 3`, `lb_try_duration 2s`, active health (`health_uri /healthz`,
  `health_interval 2s`), passive (`fail_duration 5s`, `max_fails 5`), `transport http { keepalive 90s
  keepalive_idle_conns 64 max_conns_per_host 20000 }`.
* `(tls_lab)` - `tls /certs/app.lab.fullchain.crt /certs/app.lab.key { protocols tls1.2 tls1.3 }`.
* `(default_site)` - the whole default vhost, imported by both `:80, :8080, :8082` and
  `https://app.lab:8443, https://proxy:8443, https://localhost:8443`. Caddy refuses a `tls` directive on a site that also
  has an HTTP port, so the body is a snippet and the plain/TLS sites import it.

## Default vhost (`default_site`)

Caddy evaluates directives in a fixed order, not in file order. Anything that must win over the catch-all lives in its
own `handle` block (a bare `respond 405` would run **after** every `handle`):

| contract | Caddyfile |
|---|---|
| `DELETE /api/*` -> 405 | `@del { method DELETE  path /api/* }  handle @del { respond 405 }` |
| `/allowed`, `/denied` | `@allowed_no { path /allowed  not client_ip 10.77.0.1/32 } handle @allowed_no { respond 403 }`, same for `/denied` with `client_ip 10.77.0.0/24` |
| `/api/*` strip | `handle_path /api/* { reverse_proxy ... header_up X-Route api }` (`handle_path` strips the prefix) |
| `^/v[0-9]+/` | `@versioned path_regexp ^/v[0-9]+/` |
| `/old/*` | `uri replace /old/ /new/` |
| `/redirect-me` | `redir /redirect-me /landing 301` |
| header / query routing | `@canary { header X-Canary 1 }`, `@beta query beta=1` -> `reverse_proxy canary:8080` |
| gRPC | `reverse_proxy h2c://app1:9090` |
| `/sse` | `flush_interval -1` |
| `/limited` | `rate_limit { zone limited { key {client_ip}  events 10  window 1s } }` |
| `/basic` | `basic_auth { lab <bcrypt> }` |
| `/upload` | `request_body { max_size 1MB }` |
| `/timeout` | `rewrite * /delay/5000` + `transport http { response_header_timeout 2s }` |
| `/bw` | plain proxy (no bandwidth limiting -> unsupported) |
| `/static/*` | `handle_path /static/* { root * /static  file_server }` |
| `/error-page` | `@err status 5xx  handle_response @err { root * /static  rewrite * /error.html  header X-Error-Page custom  file_server { status 503 } }` |
| `/cors` | `@cors_preflight { path /cors  method OPTIONS }` -> headers + `respond 204` |
| `/secure` | four `header` lines |
| `/cacheable*` | `cache` (Souin) before `reverse_proxy`; `Cache-Status` header; `PURGE` on the URL invalidates |
| `/compressible` | `encode zstd br gzip` at site level (br from caddy-brotli) |
| everything else (incl. `/ws`) | `handle { reverse_proxy app1:8080 app2:8080 app3:8080 { import pool_app ... } }` - WebSockets need no special config |

## Host sites

Sites are declared per scheme/port: `http://a.lab:8080, http://a.lab:80 { import site_a }` and `https://a.lab:8443 {
import tls_lab  import site_a }`. `b.lab` on 8443 uses `tls /certs/b.lab.fullchain.crt /certs/b.lab.key` - a different
certificate chosen by SNI. `redirect.lab` -> `redir https://{host}{uri} 301`.

Load balancing sites (one `reverse_proxy` each):

| host | policy |
|---|---|
| `weighted.lab` | `lb_policy weighted_round_robin 3 1` |
| `leastconn.lab` | `lb_policy least_conn` |
| `hash.lab` | `lb_policy header X-User` |
| `sticky.lab` | `lb_policy cookie lab_sticky` |
| `retry.lab` | `lb_retries 3  lb_try_duration 3s  lb_try_interval 50ms` (dead `app3:8099`) |
| `cb.lab` | `fail_duration 10s  max_fails 3  unhealthy_status 5xx` (passive) + `lb_retries 3` |
| `health.lab` | `health_uri /healthz  health_interval 1s  health_passes 2  health_fails 2` (active) |
| `canary.lab` | `lb_policy weighted_round_robin 30 30 30 10` |
| `mirror.lab` | plain pool - no mirroring in Caddy (unsupported) |

Upstream protocols: `pp.lab` -> `transport http { proxy_protocol v2 }`; `h2.lab` -> `reverse_proxy h2c://app1:8080`;
`tls.lab` -> `reverse_proxy https://app1:8443 { transport http { tls_server_name backend.lab  tls_trust_pool file
/certs/ca.crt } }`.

Auth: `auth.lab` -> `forward_auth app1:8080 { uri /auth  copy_headers X-Auth-User X-Auth-Groups }`; `jwt.lab` ->
`jwtauth { sign_key <base64 secret>  sign_alg HS256  from_header Authorization  user_claims sub }` and
`header_up X-JWT-Sub {http.auth.user.id}`.

TLS variants: `https://mtls.lab:8444 { tls ... { client_auth { mode require_and_verify  trust_pool file /certs/ca.crt } }
... header_up X-Client-Cert-CN {http.request.tls.client.subject} }`; `https://acme.lab:8443 { tls { issuer acme { dir
https://pebble:14000/dir  trusted_roots /certs/pebble-ca.pem  disable_tlsalpn_challenge } } }` - automatic HTTPS does
the rest (HTTP-01 on `http_port 80`).

Operations: `:9100 { metrics /metrics  respond /healthz "ok" 200 }`; reload = `caddy reload --config ... --adapter
caddyfile` (pushes through the admin API, listeners kept, zero failed requests in the chaos run).

## Unsupported here (and why)

`lb_mirror`, `connection_limit` (caddy-ratelimit is request-rate only), `fault_injection` (no random matcher),
`bandwidth_limit`, `docker_label_discovery` (caddy-docker-proxy is a separate distribution).

## Gotchas we hit

1. **`tls` + HTTP port on the same site** is rejected -> plain and TLS site blocks that import one snippet.
2. **Host-less `:8443 { tls ... }` pins its certificate on every SNI**, including `acme.lab` whose certificate is
   managed automatically -> always name the hosts on TLS sites; `default_sni` covers SNI-less clients.
3. **Directive order beats file order**: a bare `respond` after `handle` blocks runs last -> wrap it in `handle`.
4. `handle /static/*` keeps the prefix, `handle_path` strips it; `file_server` with `root * /static` needs the stripped path.
5. Automatic HTTPS would try Let's Encrypt for every `*.lab` host - either give explicit certificates or disable it;
   `auto_https disable_redirects` keeps ACME for acme.lab only.
6. Plugin directives need `order` statements or Caddy refuses to adapt the Caddyfile.
