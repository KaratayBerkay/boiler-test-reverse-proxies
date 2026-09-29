---
name: reverse-proxy-observability
description: Make a reverse proxy or gateway observable - structured JSON access logs with the fields that matter (upstream, timings, cache status, request id), Prometheus metrics natively or via the right exporter sidecar, OpenTelemetry tracing to Jaeger/OTLP with parent-based sampling so load does not drown the collector, request-id propagation, admin/status endpoints, and health checks for orchestration - for NGINX, HAProxy, Caddy, Traefik, Envoy, Apache, Varnish, OpenResty, Kong, APISIX, Pingora and ATS. Use whenever a task involves proxy logs, metrics, dashboards, tracing, debugging 502/504s through a proxy, or wiring a proxy into Prometheus/Grafana/Jaeger/OTel, even if the word observability is not used.
---

# Observability for reverse proxies

Verified in the reverse-proxies lab (`access_log_json`, `metrics_prometheus`, `tracing_otel`, `admin_api`, `request_id`
probes on 12 proxies). Per-proxy constructs: `reverse-proxy-capability-mapping/references/operations.md`.

## Access logs: JSON, one line, these fields
`time`, `remote_addr` (the *real* client after the trust boundary), `method`, `uri` (with query), `host`, `status`,
`bytes` (sent), `request_time`/`duration_ms`, `upstream` (which backend), `upstream_time`, `upstream_status` (when the
proxy retried, nginx joins them with commas - keep the string), `cache` (HIT/MISS/…), `request_id`, `proto`
(HTTP/1.1, HTTP/2, HTTP/3), `ssl` (TLS version), `ua`. Every proxy in the lab emits this set (nginx `log_format
escape=json`, HAProxy `%{+json}o`, Caddy JSON logs, Traefik `accessLog.format: json`, Envoy `json_format`, Apache
`LogFormat` with `%O`/`%D`/`%{UNIQUE_ID}e`, varnishncsa `-F`, Kong `KONG_NGINX_HTTP_LOG_FORMAT`, APISIX
`access_log_format` + `access_log_format_escape: json`, Pingora `serde_json`, ATS `logging.yaml`).
- Write to stdout (`/dev/stdout`, `/proc/self/fd/1`) so `docker logs`/the log driver ships it; nginx: `buffer=64k flush=1s`
  keeps the write out of the request path. ATS writes a file (`/var/log/trafficserver/access.log`); Varnish's log comes
  from the `varnishncsa` sidecar reading shared memory.
- Skip logging on the hottest benchmark paths only when you know why (`access_log off` on `/small` in the lab).
- Log the request id you *propagate*: generate when absent (`$request_id` map, `unique-id`, `{http.request.uuid}`,
  `generate_request_id` + `preserve_external_request_id`, mod_unique_id, `correlation-id`, `request-id`) and return it
  downstream so a user can quote it. Traefik has none - the app must generate it.

## Metrics
| proxy | native | sidecar | what you get |
|---|---|---|---|
| nginx OSS | `stub_status` only | `nginx/nginx-prometheus-exporter` | connections, requests - no per-upstream / status metrics (Plus API) |
| OpenResty | `nginx-lua-prometheus` | - | counters/histograms you define in `log_by_lua` |
| HAProxy | `prometheus-exporter` service | - | frontend/backend/server metrics incl. health state, queue, response codes |
| Caddy | `metrics` global + `metrics` handler | - | per-server request metrics, Go runtime |
| Traefik | `metrics.prometheus` | - | entrypoint/router/service labels, retries, TLS |
| Envoy | admin `/stats/prometheus` | - | the richest set: cluster health, outlier ejections, retries, circuit breakers |
| Apache | `server-status?auto` | `lusotycoon/apache-exporter` | workers, req/s, bytes; balancer state via `balancer-manager` |
| Varnish | `varnishstat` | `prometheus_varnish_exporter` | hit/miss, backend health, threads |
| Kong | `prometheus` plugin on the status API | - | status codes, latency histograms, bandwidth, upstream health |
| APISIX | `prometheus` plugin (`export_addr`) | - | similar to Kong |
| Pingora | your own counters (`prometheus` crate) | - | whatever you instrument |
| ATS | `stats_over_http` JSON, `traffic_ctl metric` | needs an exporter | ATS counters |
Scrape the metrics port on a management network; the lab publishes it as `:9100/metrics` for every stack so one Prometheus
job covers all.

## Tracing
- OTLP to a collector/Jaeger: nginx `ngx_otel_module`, Caddy `tracing` (OTEL_* env), Traefik `tracing.otlp`, Envoy
  `envoy.tracers.opentelemetry`, Kong `opentelemetry`, APISIX `opentelemetry`. Not in the official builds of HAProxy,
  Apache, Varnish, OpenResty, ATS; Pingora only if you add it.
- **Sample parent-based.** Tracing 100 % of requests cost nginx ~15 % CPU at 60k rps and would drown the collector. Let
  callers with a sampled `traceparent` (`-01` flag) be traced always, roots at 0.1 %: nginx `map $http_traceparent`
  + `otel_trace $var`, Caddy `OTEL_TRACES_SAMPLER=parentbased_traceidratio`, Traefik `sampleRate`, Envoy
  `client_sampling: 100` + `random_sampling: 0.1`, Kong `sampling_rate` with w3c header type, APISIX `parent_base` sampler.
- Propagate `traceparent` to upstreams (`otel_trace_context propagate`, on by default elsewhere) and log the trace id in
  the access log where the proxy exposes it.
- Verify with Jaeger's API: `GET /api/services` must list the proxy's service name; send one request with
  `traceparent: 00-<32hex>-<16hex>-01` and look it up by trace id.

## Admin surfaces and health
- Each proxy has a status/admin endpoint (see operations reference); bind it to a management port, never the public one.
- Container healthchecks: the admin endpoint or the CLI (`kong health`, `traefik healthcheck`, `varnishadm status`),
  via bash `/dev/tcp` when the image has no curl (Envoy's admin needs HTTP/1.1 with a Host header).
- Readiness = "can proxy to at least one healthy upstream"; Envoy `/ready`, HAProxy `show info`/`show servers state`,
  Kong `/status`, APISIX `/v1/healthcheck` expose upstream health; nginx OSS does not (use the app's health).

## Debugging a 502/504 through the proxy (order of questions)
1. Access log: `upstream` empty -> no member selected (all unhealthy / no live upstreams); `upstream_status` 502 vs 504
   -> refused/reset vs timeout; comma-joined upstreams -> retries happened.
2. Metrics: health state per member (HAProxy/Envoy/Kong/APISIX), ejections (Envoy `outlier_detection`), retries.
3. Proxy error log at `warn`: TLS verify failures ("unable to verify the first certificate" = regenerated certs),
   "no live upstreams", "upstream prematurely closed" (keep-alive race: retry idempotent requests or lower
   `keepalive_timeout` below the backend's idle timeout).
4. Trace: the span for the upstream call shows whether time went to connect, TTFB or transfer.
