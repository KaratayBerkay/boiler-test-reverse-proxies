---
title: "zipkin plugin"
description: "Skill for configuring the Apache APISIX zipkin plugin via the a6 CLI. Covers distributed tracing with Zipkin, Jaeger, or any Zipkin-compatible collector, B3 propagation headers, sampling, span versions, and trace variable logging."
metadata:
  category: plugin
  plugin_name: zipkin
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-zipkin/SKILL.md
---
# zipkin plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `zipkin` plugin sends distributed traces to Zipkin-compatible collectors
using the Zipkin v2 HTTP API. It supports B3 propagation headers for trace
context across services. Compatible backends include Zipkin, Jaeger, and
SkyWalking (via Zipkin receiver).

## When to Use

- Distributed tracing with Zipkin, Jaeger, or compatible collectors
- B3 header propagation across microservices
- Per-request sampling control via headers
- Trace ID injection into access logs

## Plugin Configuration Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `endpoint` | string | **Yes** | — | Zipkin collector URL (e.g. `http://zipkin:9411/api/v2/spans`) |
| `sample_ratio` | number | **Yes** | — | Sampling rate from 0.00001 to 1 |
| `service_name` | string | No | `"APISIX"` | Service name in Zipkin UI |
| `server_addr` | string | No | `$server_addr` | IPv4 address for span reporting |
| `span_version` | integer | No | `2` | Span format: 1 (legacy) or 2 (default) |

## B3 Propagation Headers

The plugin uses B3 propagation format:

### Injected to upstream

| Header | Description |
|--------|-------------|
| `x-b3-traceid` | Trace ID (16 or 32 hex chars) |
| `x-b3-spanid` | Span ID (16 hex chars) |
| `x-b3-parentspanid` | Parent span ID |
| `x-b3-sampled` | Sampling decision (1 or 0) |

### Extracted from client

| Header | Description |
|--------|-------------|
| `b3` | Single-header format: `{traceid}-{spanid}-{sampled}-{parentspanid}` |
| `x-b3-sampled` | `1` = force sample, `0` = skip, `d` = debug |
| `x-b3-flags` | `1` = force debug sampling |

Clients can override sampling per-request by setting `x-b3-sampled: 1`.

## Span Versions

**Version 2** (default, recommended):
```
request
├── proxy      (request start → header_filter)
└── response   (header_filter → log)
```

**Version 1** (legacy):
```
request
├── rewrite
├── access
└── proxy
    └── body_filter
```

## Step-by-Step: Enable Zipkin Tracing

### 1. Create a route with zipkin

```bash
a6 route create -f - <<'EOF'
{
  "id": "traced-api",
  "uri": "/api/*",
  "plugins": {
    "zipkin": {
      "endpoint": "http://zipkin:9411/api/v2/spans",
      "sample_ratio": 1,
      "service_name": "my-gateway",
      "span_version": 2
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "backend:8080": 1
    }
  }
}
EOF
```

### 2. Send a request

```bash
curl http://127.0.0.1:9080/api/hello
```

### 3. View traces in Zipkin UI

Open `http://zipkin:9411` and search for service `my-gateway`.

## Common Patterns

### Send traces to Jaeger

Jaeger supports the Zipkin v2 API:

```json
{
  "plugins": {
    "zipkin": {
      "endpoint": "http://jaeger-collector:9411/api/v2/spans",
      "sample_ratio": 1,
      "service_name": "my-gateway"
    }
  }
}
```

### Production sampling (10%)

```json
{
  "plugins": {
    "zipkin": {
      "endpoint": "http://zipkin:9411/api/v2/spans",
      "sample_ratio": 0.1,
      "service_name": "production-gateway"
    }
  }
}
```

### Trace IDs in access logs

Add to APISIX `config.yaml`:

```yaml
plugin_attr:
  zipkin:
    set_ngx_var: true

nginx_config:
  http:
    access_log_format: '{"trace_id":"$zipkin_trace_id","span_id":"$zipkin_span_id","traceparent":"$zipkin_context_traceparent"}'
    access_log_format_escape: json
```

Available variables:
- `$zipkin_trace_id` — Trace ID
- `$zipkin_span_id` — Span ID
- `$zipkin_context_traceparent` — W3C traceparent header

### External IP address

```json
{
  "plugins": {
    "zipkin": {
      "endpoint": "http://zipkin:9411/api/v2/spans",
      "sample_ratio": 1,
      "server_addr": "10.0.1.5"
    }
  }
}
```

## Config Sync Example

```yaml
version: "1"
routes:
  - id: traced-api
    uri: /api/*
    plugins:
      zipkin:
        endpoint: http://zipkin:9411/api/v2/spans
        sample_ratio: 1
        service_name: my-gateway
        span_version: 2
    upstream_id: my-upstream
upstreams:
  - id: my-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No traces in Zipkin UI | Wrong `endpoint` URL | Verify collector is reachable; must include `/api/v2/spans` |
| Traces not connected | B3 headers stripped by proxy | Ensure intermediate proxies forward `x-b3-*` headers |
| All requests sampled | `sample_ratio: 1` | Lower for production (e.g. 0.01-0.1) |
| Missing trace variables in logs | `set_ngx_var` not enabled | Set `plugin_attr.zipkin.set_ngx_var: true` in config.yaml |
| 400 from collector | Span version mismatch | Try `span_version: 1` if collector only supports v1 |
