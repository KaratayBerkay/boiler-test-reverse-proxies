# Operations - construct per proxy

Probe ids: `access_log_json`, `metrics_prometheus`, `tracing_otel`, `admin_api`, `hot_reload`, `docker_label_discovery`,
plus the chaos phase (failover under load, reload under load).

## JSON access log
- nginx / OpenResty: `log_format json escape=json '{...}'; access_log /dev/stdout json buffer=64k flush=1s;`
- HAProxy 3.x: `log-format '%{+json}o %(time)t %(client_ip)ci %(status)ST ...'` + `log stdout format raw local0`.
- Caddy: global `log { output stdout  format json }` + `log` in the site.
- Traefik: `accessLog: { format: json, fields: { headers: { names: { X-Request-ID: keep } } } }`.
- Envoy: `envoy.access_loggers.stdout` with `log_format: { json_format: {...} }` (`%START_TIME%`, `%RESPONSE_CODE%`, `%UPSTREAM_HOST%`, `%DURATION%`, `%REQ(X-REQUEST-ID)%`).
- Apache: `LogFormat "{...\"bytes\":%O,\"duration_us\":%D...}" json` (`%O` needs mod_logio) + `CustomLog /proc/self/fd/1 json`.
- Varnish: `varnishncsa -F '{...%{Varnish:handling}x...}'` as a sidecar on the shared VSM directory.
- Kong: `KONG_NGINX_HTTP_LOG_FORMAT='json_lab escape=json {...}'` + `KONG_PROXY_ACCESS_LOG=/dev/stdout json_lab` (`$$` in compose).
- APISIX: `nginx_config.http.access_log_format` + `access_log_format_escape: json`.
- Pingora: `logging()` hook printing `serde_json::json!({...})`.
- ATS: `logging.yaml` `formats: [{ name: json, format: '{"time":"%<cqtq>", "status":%<pssc>, "cache":"%<crc>", ...}' }]` (a log-config change needs a restart).

## Prometheus metrics
- nginx: `stub_status` + `nginx/nginx-prometheus-exporter` sidecar (`--nginx.scrape-uri`); per-upstream metrics are Plus.
- HAProxy: `http-request use-service prometheus-exporter if { path /metrics }` (built in).
- Caddy: global `metrics` + `:9100 { metrics /metrics }`.
- Traefik: `metrics.prometheus: { entryPoint: metrics, addEntryPointsLabels: true, addServicesLabels: true }`.
- Envoy: admin `/stats/prometheus` (re-exposed through a small HCM on :9100).
- Apache: `server-status` + `lusotycoon/apache-exporter --scrape_uri=.../server-status?auto`.
- Varnish: `prometheus_varnish_exporter -n <vsm dir>` sidecar.
- OpenResty: `nginx-lua-prometheus` (`init_worker` registry, `log_by_lua` counters, `content_by_lua { prometheus:collect() }`).
- Kong: `prometheus` plugin + `KONG_STATUS_LISTEN` (`/metrics` on the status API).
- APISIX: `prometheus` plugin + `plugin_attr.prometheus.export_addr` (:9100 `/metrics`).
- Pingora: the `prometheus` crate + a `ServeHttp` app.
- ATS: **unsupported** (`stats_over_http.so` JSON at `/_stats`; needs an exporter).

## OpenTelemetry tracing (parent-based sampling so load tests are not traced)
- nginx: `ngx_otel_module` - `otel_exporter { endpoint jaeger:4317; } otel_service_name nginx; map $http_traceparent $on { "~-01$" 1; default 0; } otel_trace $on; otel_trace_context propagate;`
- Caddy: `tracing { span pxlab }` + `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_TRACES_SAMPLER=parentbased_traceidratio`, `OTEL_TRACES_SAMPLER_ARG=0.001`.
- Traefik: `tracing: { otlp: { http: { endpoint: http://jaeger:4318/v1/traces } }, sampleRate: 0.001 }`.
- Envoy: HCM `tracing.provider envoy.tracers.opentelemetry` (grpc_service -> cluster jaeger) with `client_sampling 100`, `random_sampling 0.1`.
- Kong: `opentelemetry` plugin (`traces_endpoint`, `sampling_rate: 0.001`, `header_type: w3c`) + `KONG_TRACING_INSTRUMENTATIONS=all`.
- APISIX: `opentelemetry` plugin with `sampler: { name: parent_base, options: { root: { name: trace_id_ratio, options: { fraction: 0.001 } } } }` + `plugin_metadata` collector `jaeger:4318`.
- HAProxy, Apache, Varnish, OpenResty, Pingora, ATS: **unsupported** in the official builds (HAProxy OpenTracing addon, Apache otel-webserver-module, opentelemetry-lua are separate builds).

## Admin / status API and reload
| proxy | admin surface | reload command | what happens |
|---|---|---|---|
| nginx / OpenResty | `stub_status` on :9101 | `nginx -s reload` (SIGHUP) | new workers, old ones finish requests; idle keep-alive connections are closed (a few client errors) |
| HAProxy | runtime API socket (`show info`, `set server`, `acme renew`), stats page | `haproxy -c ... && kill -USR2 1` (master-worker) | new worker, listeners handed over (`expose-fd listeners`), old worker drains |
| Caddy | admin API :2019 (`GET /config/`, `POST /load`) | `caddy reload --config ... --adapter caddyfile` | config swapped through the API, sockets kept |
| Traefik | `/api/rawdata`, dashboard, `/ping` | edit the dynamic file (file provider `watch: true`) | routers/services rebuilt, no restart |
| Envoy | admin :9101 (`/ready`, `/stats`, `/config_dump`, `/clusters`) | bump `version_info` in the watched xDS file (write + rename) | resources swapped; for the bootstrap: hot restart |
| Apache | `server-status`, `balancer-manager`, `md-status` | `httpd -k graceful` | children finish, new ones start |
| Varnish | `varnishadm` (`vcl.load`, `vcl.use`, `backend.list`) | `varnishreload` | new VCL active instantly |
| Kong | admin API :8001 (`/status`, `/config`) | `POST /config -F config=@kong.yml` (DB-less) | atomic re-apply; `kong reload` alone does **not** re-read the file |
| APISIX | control API :9101 (`/v1/routes`, `/v1/healthcheck`) | `touch apisix.yaml` (standalone) | routes re-read on mtime change |
| Pingora | custom status app | start `pingora-lab -u`, then SIGQUIT the old pid | listening sockets transferred over the upgrade socket, old process drains |
| ATS | `traffic_ctl metric get`, `stats_over_http` | `traffic_ctl config reload` | remap/records/plugins re-read (logging needs restart) |

Measured in the lab's chaos phase: no proxy lost a timeline request on reload; nginx-family reloads close idle
keep-alive connections (clients must retry), API/file-watch reloads (Caddy, Traefik, Envoy, Kong, APISIX) and
HAProxy's fd hand-over kept every connection.

## Failover under load (backend stopped 8 s, 1 000 rps)
All proxies with connection-level retries hid the stop (0 non-2xx). The differences are in the re-admission time after
the backend returns (health-check interval + rise count) and in the p999/max latency during the stop (a connect
timeout of 3 s shows up as a ~3 s max). See `results/SUMMARY.md` chaos table.

## Docker label discovery
Only Traefik (`providers.docker` with `exposedByDefault: false`, `defaultRule`, labels on the container). Others need a
generator (nginx-proxy/docker-gen, caddy-docker-proxy, Kong/APISIX ingress controllers on Kubernetes).
