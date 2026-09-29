# Research sources

What the lab was built from, and what was surveyed for the `skills/` folder. Versions are the ones pulled on
2026-09-13 (`scripts/pull-images.sh`, `uv run pxlab info <stack>`).

## Proxies (official documentation used for each stack)

| stack | image | primary references |
|---|---|---|
| nginx 1.29.8 | `nginx:1.29-otel` (Docker Hub official) | [proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html), [upstream module](https://nginx.org/en/docs/http/ngx_http_upstream_module.html), [ACME module (1.29)](https://nginx.org/en/docs/http/ngx_http_acme_module.html), [ngx_otel_module](https://nginx.org/en/docs/ngx_otel_module.html), [njs](https://nginx.org/en/docs/njs/), [stream ssl_preread](https://nginx.org/en/docs/stream/ngx_stream_ssl_preread_module.html) |
| HAProxy 3.4.4 | `haproxy:lts` | [3.4 configuration manual](https://docs.haproxy.org/3.4/configuration.html), [native ACME wiki](https://github.com/haproxy/wiki/wiki/ACME:--native-haproxy), [configuration tutorials](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/), [Lua API (core.httpclient)](https://www.arpalert.org/src/haproxy-lua-api/3.0/index.html) |
| Caddy 2 | `caddy:2` + `caddy:2-builder` | [reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [global options](https://caddyserver.com/docs/caddyfile/options), [caddy-ratelimit](https://github.com/mholt/caddy-ratelimit), [caddy-l4](https://github.com/mholt/caddy-l4), [cache-handler (Souin)](https://github.com/caddyserver/cache-handler), [caddy-jwt](https://github.com/ggicci/caddy-jwt), [caddy-brotli](https://github.com/ueffel/caddy-brotli) |
| Traefik 3.7.13 | `traefik:v3` | [routers](https://doc.traefik.io/traefik/routing/routers/), [HTTP middlewares](https://doc.traefik.io/traefik/middlewares/http/overview/), [ACME](https://doc.traefik.io/traefik/https/acme/), [tracing](https://doc.traefik.io/traefik/observability/tracing/overview/), [Docker provider](https://doc.traefik.io/traefik/providers/docker/) |
| Envoy 1.39 | `envoyproxy/envoy:v1.39-latest` | [HTTP filters](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/http_filters), [load balancing](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/load_balancing), [xDS / filesystem subscriptions](https://www.envoyproxy.io/docs/envoy/latest/configuration/overview/xds_api), [HCM](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/http_conn_man), [ExtensionWithMatcher](https://www.envoyproxy.io/docs/envoy/latest/configuration/advanced/matching/matching_api) |
| Apache httpd 2.4.68 | `httpd:2.4` | [mod_proxy](https://httpd.apache.org/docs/2.4/mod/mod_proxy.html), [mod_proxy_balancer](https://httpd.apache.org/docs/2.4/mod/mod_proxy_balancer.html), [mod_proxy_hcheck](https://httpd.apache.org/docs/2.4/mod/mod_proxy_hcheck.html), [mod_md](https://httpd.apache.org/docs/2.4/mod/mod_md.html), [mod_cache](https://httpd.apache.org/docs/2.4/mod/mod_cache.html), [mod_remoteip](https://httpd.apache.org/docs/2.4/mod/mod_remoteip.html) |
| Varnish 8.0.2 + hitch 1.8 | `varnish:8.0`, `hitch:latest` | [VCL users guide](https://varnish-cache.org/docs/8.0/users-guide/vcl.html), [vmod_directors](https://varnish-cache.org/docs/8.0/reference/vmod_directors.html), [varnish-modules](https://github.com/varnish/varnish-modules), [hitch configuration](https://github.com/varnish/hitch/blob/master/docs/configuration.md), [vmod_reqwest](https://github.com/gquintard/vmod_reqwest) |
| OpenResty 1.27.1.2 | `openresty/openresty:1.27.1.2-alpine-fat` | [lua-nginx-module](https://github.com/openresty/lua-nginx-module), [lua-resty-limit-traffic](https://github.com/openresty/lua-resty-limit-traffic), [lua-resty-acme](https://github.com/fffonion/lua-resty-acme), [nginx-lua-prometheus](https://github.com/knyar/nginx-lua-prometheus), [lua-resty-jwt](https://github.com/SkyLothar/lua-resty-jwt) |
| Kong Gateway 3.9 OSS | `kong:3.9` | [DB-less & declarative config](https://docs.konghq.com/gateway/latest/production/deployment-topologies/db-less-and-declarative-config/), [expressions router](https://docs.konghq.com/gateway/latest/key-concepts/routes/expressions/), [plugin hub](https://docs.konghq.com/hub/), [kong.conf reference](https://docs.konghq.com/gateway/latest/reference/configuration/) |
| Apache APISIX 3.15.0 | `apache/apisix:3.15.0-debian` | [standalone mode](https://apisix.apache.org/docs/apisix/deployment-modes/#standalone), [traffic-split](https://apisix.apache.org/docs/apisix/plugins/traffic-split/), [health checks](https://apisix.apache.org/docs/apisix/tutorials/health-check/), [proxy-cache](https://apisix.apache.org/docs/apisix/plugins/proxy-cache/), [opentelemetry](https://apisix.apache.org/docs/apisix/plugins/opentelemetry/) |
| Pingora 0.9 | `rust:1-slim` build | [cloudflare/pingora](https://github.com/cloudflare/pingora), [user guide](https://github.com/cloudflare/pingora/blob/main/docs/user_guide/index.md), [ProxyHttp trait](https://docs.rs/pingora-proxy/latest/pingora_proxy/trait.ProxyHttp.html), [pingora-load-balancing](https://docs.rs/pingora-load-balancing/latest/), [pingora-cache](https://docs.rs/pingora-cache/latest/), [pingora-limits](https://docs.rs/pingora-limits/latest/) |
| Apache Traffic Server 9.2.3 | Ubuntu 24.04 `trafficserver` packages | [configuration guide](https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/configuration/index.en.html), [remap.config](https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/files/remap.config.en.html), [strategies.yaml](https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/files/strategies.yaml.en.html), [header_rewrite](https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/plugins/header_rewrite.en.html), [sni.yaml](https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/files/sni.yaml.en.html) |

## Tools and infrastructure

| component | source | why |
|---|---|---|
| oha 1.16 | [hatoo/oha](https://github.com/hatoo/oha) (`ghcr.io/hatoo/oha`) | h1/h2 closed-loop load with JSON output and latency percentiles; `-w` counts in-flight requests at the end as aborted, not errors |
| wrk | [wg/wrk](https://github.com/wg/wrk) | the classic reference number everybody quotes |
| fortio | [fortio/fortio](https://github.com/fortio/fortio) | open-loop (fixed QPS) latency without coordinated omission; gRPC health load |
| k6 v2.2 | [grafana/k6](https://github.com/grafana/k6) | WebSocket scenario |
| h3load (custom Go) | [quic-go v0.62](https://github.com/quic-go/quic-go) | HTTP/3 load - no maintained h3 load tool ships in a Debian image |
| grpcurl | [fullstorydev/grpcurl](https://github.com/fullstorydev/grpcurl) | gRPC capability probe |
| Pebble | [letsencrypt/pebble](https://github.com/letsencrypt/pebble) (`ghcr.io/letsencrypt/pebble`) | ACME test CA with HTTP-01 on real ports; `-dnsserver 127.0.0.11:53` resolves docker names |
| Jaeger 2.9 | [jaegertracing/jaeger](https://github.com/jaegertracing/jaeger) | OTLP gRPC/HTTP sink + query API for the tracing probe |
| Go backend / loadgen images | `shared/backend`, `shared/loadgen` | see `docs/contract.md` |
| CPU accounting | cgroup v2 `cpu.stat` / `memory.current` under `/sys/fs/cgroup/system.slice/docker-<id>.scope` | exact per-container cores and memory per scenario |

## Agent-skill survey (for `skills/vendor/`)

Method: GitHub code search for `filename:SKILL.md` + proxy names, vendor org search (`org:nginx`, `org:traefik`,
`org:envoyproxy`, `org:haproxytech`, `org:caddyserver`, `org:Kong`, `org:api7`), license check through the GitHub API,
then a read of each candidate's SKILL.md. Only permissive licenses (Apache-2.0 / MIT / BSD) with a LICENSE file in the
repository were vendored. Vendor orgs only host *repo-internal* skills (release / review / testing helpers for their own
code bases), not configuration skills, except API7 and Kong.

| repository | skill(s) | license | decision |
|---|---|---|---|
| [api7/agent-skills](https://github.com/api7/agent-skills) | `a6` (Apache APISIX via the a6 CLI; 29 plugin references, 8 recipes) | Apache-2.0 | **vendored** - vendor-authored, the most complete gateway skill found |
| [Kong/kongctl](https://github.com/Kong/kongctl) | `kongctl-declarative` (Konnect + decK declarative workflows) | Apache-2.0 | **vendored** - Kong-authored; the declarative model matches the lab's DB-less stack |
| [netdata/skills](https://github.com/netdata/skills) | `troubleshoot-nginx`, `-haproxy`, `-envoy`, `-traefik`, `-varnish`, `-apache-httpd` | Apache-2.0 | **vendored** - Netdata-authored diagnostic trees (connection exhaustion, backend collapse, TLS CPU, reload storms); MCP calls are optional context |
| [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | `traefik` (v3, providers, middlewares, TLS/ACME, templates + healthcheck script) | MIT | **vendored** - broadest Traefik skill found |
| [ddnetters/homelab-agent-skills](https://github.com/ddnetters/homelab-agent-skills) | `caddy-reverse-proxy` | MIT | **vendored** - concise Caddyfile patterns |
| [nejclovrencic/nginx-agent-skills](https://github.com/nejclovrencic/nginx-agent-skills) | nginx + OpenResty development | no LICENSE file | not vendored (referenced only) |
| [missBerg/envoy-skills](https://github.com/missBerg/envoy-skills) | Envoy Gateway / AI Gateway adopter + contributor skills | Apache-2.0 | not vendored - Kubernetes Gateway-API oriented, `proxy/` section empty |
| [koderover/devops-skills](https://github.com/koderover/devops-skills) | `apisix` (admin API curl recipes, Chinese) | MIT | not vendored - superseded by `a6` |
| [tspry/superpowers-devops](https://github.com/tspry/superpowers-devops), [ai-enhanced-engineer/aiee-skills](https://github.com/ai-enhanced-engineer/aiee-skills), [event4u-app/agent-config](https://github.com/event4u-app/agent-config) | reverse-proxy / caddy-tls-proxy / traefik | MIT | not vendored - short deployment recipes, covered by the first-party skills |
| [membranedev/application-skills](https://github.com/membranedev/application-skills), [SecureSkills-io/nginx-skill](https://github.com/SecureSkills-io/nginx-skill), [qwedsazxc78/devops-ai-skill](https://github.com/qwedsazxc78/devops-ai-skill), [dlimkin/agent-skills](https://github.com/dlimkin/agent-skills), [cloudthinker-ai/CloudSkills](https://github.com/cloudthinker-ai/CloudSkills) | nginx / haproxy / envoy / kong skills | no license | not vendored |
| [TerminalSkills/skills](https://github.com/TerminalSkills/skills), [agentskillexchange/skills](https://github.com/agentskillexchange/skills), `majiayu000/claude-skill-registry`, `sickn33/agentic-awesome-skills`, `G1Joshi/Agent-Skills`, `bytesagain/ai-skills`, `jeremylongshore/tons-of-skills-marketplace` | aggregated nginx/traefik/envoy/caddy/haproxy skills | Apache-2.0 / MIT / mixed | not vendored - aggregator/mirror catalogs of unclear provenance (same policy as the sibling labs) |
| `nginx/kubernetes-ingress`, `traefik/traefik`, `envoyproxy/gateway` `.claude/skills` | repo-internal (testing, release, review) | Apache-2.0 / MIT | not applicable |

No vendor-authored or permissively licensed skill was found for HAProxy configuration, Envoy Proxy (non-Gateway)
configuration, Varnish VCL, Pingora or Apache Traffic Server - the first-party skills in `skills/` cover them.

## Comparison articles consulted for the "choosing" guidance

* [Nginx, Caddy, Traefik, or HAProxy: how to pick the right reverse proxy (2026)](https://dev.to/shinagawa-web/nginx-caddy-traefik-or-haproxy-how-to-pick-the-right-reverse-proxy-for-your-stack-2026-2doj)
* [Compare Envoy, Traefik and Caddy for reverse proxy use cases (OneUptime, 2026)](https://github.com/OneUptime/blog/blob/master/posts/2026-03-04-compare-envoy-traefik-and-caddy-for-reverse-proxy-use-cases/README.md)

The lab's own numbers (`results/SUMMARY.md`) take precedence over any claim in those articles.
