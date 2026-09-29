# Apache APISIX 3.15 (standalone) - config walkthrough

Stack: `stacks/apisix/` - image `apache/apisix:3.15.0-debian`. Two files:

* `config.yaml` - static: deployment mode, listeners, nginx tuning, the enabled plugin list, prometheus export.
* `apisix.src.yaml` -> `gen.py` -> `apisix.yaml` - the route table for **standalone** mode (`config_provider: yaml`):
  upstreams, routes, consumers, ssls, stream_routes, global_rules, plugin_metadata. PEMs are inlined by the generator
  (JSON-escaped strings), the file must end with `#END`, and touching it is the reload (APISIX re-reads it when the
  mtime changes).

Read this next to those files.

## `config.yaml`

```yaml
deployment: { role: data_plane, role_data_plane: { config_provider: yaml } }
apisix:
  node_listen: [{ port: 8080 }, { port: 80 }]
  enable_http2: true                 # 3.9+: apisix-level; h2 on TLS, h2c prior knowledge on plain ports
  proxy_mode: http&stream            # stream routes need the stream proxy enabled
  proxy_protocol: { listen_http_port: 8082 }      # extra listener accepting PROXY protocol
  stream_proxy: { tcp: [9000], udp: [9001] }
  ssl:
    listen: [{ port: 8443, enable_http3: true }, { port: 8444 }]
    ssl_trusted_certificate: /certs/ca.crt        # verify upstream TLS
  control: { ip: 0.0.0.0, port: 9101 }            # /v1/routes, /v1/upstreams, /v1/healthcheck
nginx_config:
  worker_processes: 4
  http: { access_log_format: '{"time":"$time_iso8601",...}', access_log_format_escape: json,
          upstream: { keepalive: 320, keepalive_requests: 10000 } }
plugins: [real-ip, client-control, request-id, fault-injection, serverless-pre-function, serverless-post-function,
          cors, ip-restriction, basic-auth, jwt-auth, forward-auth, proxy-cache, proxy-mirror, proxy-rewrite,
          limit-conn, limit-req, gzip, brotli, traffic-split, redirect, response-rewrite, prometheus, opentelemetry]
plugin_attr: { prometheus: { export_uri: /metrics, export_addr: { ip: 0.0.0.0, port: 9100 } } }
```

The `plugins:` list **replaces** the default list; anything not named is not loaded.

## Upstreams (`apisix.src.yaml`)

| id | type / options | contract |
|---|---|---|
| `app` | `roundrobin`, `retries: 3`, `timeout {3,30,30}`, `checks.active` (`/healthz` every 2 s) + `checks.passive` | default pool |
| `weighted` | nodes `app1:8080: 3, app2:8080: 1` | weighted RR |
| `leastconn` | `least_conn` | |
| `hash` | `chash`, `hash_on: header`, `key: x-user` | consistent hashing |
| `retry` | RR incl. `app3:8099`, `retries: 3` | retry hides the dead node |
| `cb` | passive `http_failures: 3` on 5xx + active every 5 s | outlier ejection |
| `health` | active every 1 s | |
| `app1`, `app2`, `app3` | single-node upstreams used by the sticky rules | |
| `app_t2` | `timeout.read: 2`, `retries: 0` | `/timeout` |
| `app_tls` | `scheme: https`, `pass_host: rewrite`, `upstream_host: backend.lab`, `tls: { verify: true }` | TLS re-encryption |
| `grpc` | `scheme: grpc` | gRPC (h2c) |

## Routes

Host routes have `priority: 100`, path routes 50-60, `catch-all` 1. A route names its `upstream_id` and a `plugins`
map:

| route | match | plugins |
|---|---|---|
| `a`, `b` | `hosts: [a.lab]` | `proxy-rewrite { headers.set X-Route }` |
| `redirect` | `redirect.lab` | `redirect { http_to_https: true, ret_code: 301 }` |
| `sticky` | `sticky.lab` | `traffic-split` rules matching `cookie_lab_sticky == app1/2/3` -> single-node upstreams; `serverless-post-function` (header_filter) sets `Set-Cookie: lab_sticky=<X-Instance>` on the first visit |
| `canary` | `canary.lab` | `traffic-split { weighted_upstreams: [{ upstream_id: canary, weight: 10 }, { weight: 90 }] }` (the weight without an upstream = the route's own upstream) |
| `mirror` | `mirror.lab` | `proxy-mirror { host: http://shadow:8080, sample_ratio: 1 }` |
| `auth` | `auth.lab` | `forward-auth { uri: http://app1:8080/auth, request_headers, upstream_headers: [X-Auth-User, X-Auth-Groups], client_headers: [WWW-Authenticate] }` |
| `jwt` | `jwt.lab` | `jwt-auth { key_claim_name: iss, header: Authorization }` (consumer `lab`, key `pxlab`, HS256) |
| `mtls` | `mtls.lab` | `proxy-rewrite` sets `X-Client-Cert-CN: $ssl_client_s_dn`; the client CA is on the `ssls` entry |
| `api-delete` (60) | `uri: /api/*`, `methods: [DELETE]` | `fault-injection { abort: { http_status: 405 } }` |
| `canary-header/-query` (55) | `vars: [["http_x_canary", "==", "1"]]` / `[["arg_beta", "==", "1"]]` | |
| `api` | `/api/*` | `proxy-rewrite { regex_uri: ["^/api/(.*)", "/$1"] }` + `X-Route: api` |
| `versioned` | `uri: /v*` + `vars: [["uri", "~~", "^/v[0-9]+/"]]` | |
| `old` | `/old/*` | `regex_uri: ["^/old/(.*)", "/new/$1"]` |
| `redirect-me` | | `redirect { uri: /landing, ret_code: 301 }` |
| `ws` | `/ws` | `enable_websocket: true` |
| `grpc` | `/grpc.health.v1.Health/*` | upstream `grpc` |
| `limited` | | `limit-req { rate: 10, burst: 5, key: remote_addr, rejected_code: 429, nodelay: true }` |
| `conn-limited` | | `limit-conn { conn: 3, burst: 0, key: remote_addr, rejected_code: 429 }` |
| `allowed` / `denied` | | `ip-restriction { whitelist }` / `{ blacklist }` |
| `basic` | | `basic-auth` |
| `upload` | | `client-control { max_body_size: 1048576 }` |
| `fault` | | `fault-injection { abort: { http_status: 503, percentage: 20 } }` |
| `bw` | | `serverless-pre-function` (access) sets `ngx.var.limit_rate = 500000` |
| `static` | | `serverless-pre-function` reads `/static/index.html` and `ngx.exit(200)` |
| `error-page` | | `proxy-rewrite -> /status/503` + `response-rewrite { vars: [["status", "==", 503]], headers.set X-Error-Page, body }` |
| `cors` | | `cors { allow_origins: "*", ... }` |
| `secure` | | `response-rewrite { headers.set ... }` |
| `cacheable` | `/cacheable*` | `proxy-cache { cache_strategy: disk, cache_zone: disk_cache_one, cache_key: [$host, $request_uri], cache_control: true }`; `PURGE` works with the disk strategy (`Apisix-Cache-Status`) |
| `catch-all` | `/*` | |

`global_rules` apply to every route: `real-ip { source: proxy_protocol_addr, trusted_addresses: [10.77.0.0/24] }`
(the client IP from PROXY protocol on :8082), `proxy-rewrite` (`X-Lab-Proxy`, `X-Real-IP`, RFC 7239 `Forwarded`),
`response-rewrite` (remove `X-Powered-By`, add `Alt-Svc`), `request-id`, `gzip`, `brotli`, `prometheus`,
`opentelemetry` with a `parent_base` sampler (`trace_id_ratio 0.001` for roots).

`plugin_metadata` holds the opentelemetry collector (`jaeger:4318`) - in 3.x this is metadata, not `plugin_attr`.
`consumers.lab` carries `basic-auth` and `jwt-auth` credentials. `ssls` map SNIs to certificates; entry 3
(`mtls.lab`) adds `client: { ca, depth }` = mTLS only for that SNI. `stream_routes` bind `server_port` 9000 (TCP ->
`app1:8080`) and 9001 (`scheme: udp` -> `app1:9002`).

## Operations

* Reload: `python3 gen.py && touch apisix.yaml` (standalone mode watches the mtime).
* Control API :9101 (`/v1/routes`, `/v1/healthcheck`); Prometheus :9100 `/metrics`; no curl in the image, the compose
  healthcheck uses bash `/dev/tcp` against `/v1/healthcheck`.

## Unsupported here (and why)

`h2_upstream` (gRPC only), `proxy_protocol_upstream` (stream only), `tls_passthrough_sni` (stream `sni` routes
terminate TLS), `acme_auto_cert`, `cache_stale_on_error`, `compress_zstd`, `docker_label_discovery`.

## Gotchas we hit

1. `enable_http2` moved from `ssl:` to the `apisix:` level (3.9+).
2. A schema violation in one route (`cache_bypass: []`) silently drops **that route** - check the error log after
   every reload.
3. `opentelemetry` needs `plugin_metadata` for the collector; `plugin_attr` is ignored in 3.x.
4. PROXY protocol on :8082 only sets `$proxy_protocol_addr`; the `real-ip` plugin turns it into `$remote_addr`.
5. Stream routes need `proxy_mode: http&stream`.
6. `PURGE` on a keep-alive connection was unreliable in the probe; a fresh connection works (noted as
   `keepalive_quirk` in the results).
