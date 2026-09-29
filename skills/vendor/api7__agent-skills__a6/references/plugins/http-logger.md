---
title: "http-logger plugin"
description: "Skill for configuring the Apache APISIX http-logger plugin via the a6 CLI. Covers pushing access logs to HTTP/HTTPS endpoints in batches, custom log formats with NGINX variables, conditional request/response body logging, batch processing tuning, and integration with external logging systems."
metadata:
  category: plugin
  plugin_name: http-logger
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-http-logger/SKILL.md
---
# http-logger plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `http-logger` plugin pushes request/response logs as JSON to HTTP or
HTTPS endpoints. Logs are batched for efficiency and support custom formats
using NGINX variables. Use it to send structured logs to any HTTP-based
logging backend (Elasticsearch, Loki, custom APIs, etc.).

## When to Use

- Ship access logs to an HTTP-based logging backend
- Custom log formats with selected fields only
- Conditional request/response body capture
- Batch log delivery with retry on failure

## Plugin Configuration Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `uri` | string | **Yes** | — | HTTP/HTTPS endpoint for log delivery |
| `auth_header` | string | No | — | Authorization header value |
| `timeout` | integer | No | `3` | Connection timeout in seconds |
| `log_format` | object | No | — | Custom log format (supports `$variable` syntax) |
| `include_req_body` | boolean | No | `false` | Include request body in logs |
| `include_req_body_expr` | array | No | — | Conditional expression for request body logging |
| `include_resp_body` | boolean | No | `false` | Include response body in logs |
| `include_resp_body_expr` | array | No | — | Conditional expression for response body logging |
| `concat_method` | string | No | `"json"` | Batch format: `json` (array) or `new_line` (newline-separated) |
| `ssl_verify` | boolean | No | `false` | Verify SSL certificate for HTTPS endpoints |

### Batch Processing Parameters

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `batch_max_size` | integer | `1000` | Max entries per batch |
| `inactive_timeout` | integer | `5` | Seconds before flushing incomplete batch |
| `buffer_duration` | integer | `60` | Max age of oldest entry before forced flush |
| `max_retry_count` | integer | `0` | Retry attempts on failure |
| `retry_delay` | integer | `1` | Seconds between retries |

## Default Log Entry Format

When no custom `log_format` is set, each log entry contains:

```json
{
  "client_ip": "127.0.0.1",
  "route_id": "1",
  "service_id": "",
  "start_time": 1703907485819,
  "latency": 101.9,
  "apisix_latency": 100.9,
  "upstream_latency": 1,
  "upstream": "127.0.0.1:8080",
  "request": {
    "method": "GET",
    "uri": "/api/users",
    "url": "http://127.0.0.1:9080/api/users",
    "size": 194,
    "headers": { "host": "...", "user-agent": "..." },
    "querystring": {}
  },
  "response": {
    "status": 200,
    "size": 123,
    "headers": { "content-type": "...", "content-length": "..." }
  },
  "server": {
    "hostname": "gateway-1",
    "version": "3.15.0"
  }
}
```

## Step-by-Step: Ship Logs to an HTTP Endpoint

### 1. Create a route with http-logger

```bash
a6 route create -f - <<'EOF'
{
  "id": "logged-api",
  "uri": "/api/*",
  "plugins": {
    "http-logger": {
      "uri": "http://log-collector:8080/logs",
      "batch_max_size": 100,
      "inactive_timeout": 10
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

### 2. Verify logs are arriving

```bash
curl http://127.0.0.1:9080/api/hello
# Check your log collector for the entry
```

## Common Patterns

### Custom log format with NGINX variables

```json
{
  "plugins": {
    "http-logger": {
      "uri": "http://log-collector:8080/logs",
      "log_format": {
        "@timestamp": "$time_iso8601",
        "client_ip": "$remote_addr",
        "host": "$host",
        "method": "$request_method",
        "uri": "$request_uri",
        "status": "$status",
        "latency": "$request_time",
        "upstream_addr": "$upstream_addr"
      }
    }
  }
}
```

### Authenticated endpoint

```json
{
  "plugins": {
    "http-logger": {
      "uri": "https://log-service.example.com/api/v1/logs",
      "auth_header": "Bearer eyJhbGciOiJIUzI1NiIs...",
      "ssl_verify": true,
      "timeout": 5
    }
  }
}
```

### Conditional request body logging

Log request bodies only when a query parameter is present:

```json
{
  "plugins": {
    "http-logger": {
      "uri": "http://log-collector:8080/logs",
      "include_req_body": true,
      "include_req_body_expr": [
        ["arg_debug", "==", "true"]
      ]
    }
  }
}
```

### Newline-delimited JSON (for Elasticsearch bulk API)

```json
{
  "plugins": {
    "http-logger": {
      "uri": "http://elasticsearch:9200/_bulk",
      "concat_method": "new_line"
    }
  }
}
```

### Aggressive batching for high-traffic routes

```json
{
  "plugins": {
    "http-logger": {
      "uri": "http://log-collector:8080/logs",
      "batch_max_size": 5000,
      "inactive_timeout": 30,
      "buffer_duration": 120,
      "max_retry_count": 3,
      "retry_delay": 2
    }
  }
}
```

## Config Sync Example

```yaml
version: "1"
routes:
  - id: logged-api
    uri: /api/*
    plugins:
      http-logger:
        uri: http://log-collector:8080/logs
        batch_max_size: 200
        inactive_timeout: 10
        log_format:
          timestamp: "$time_iso8601"
          client_ip: "$remote_addr"
          method: "$request_method"
          uri: "$request_uri"
          status: "$status"
    upstream_id: my-upstream
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No logs arriving | Wrong `uri` or endpoint down | Verify endpoint is reachable from APISIX |
| SSL handshake failure | Certificate not trusted | Set `ssl_verify: false` for self-signed certs |
| Logs delayed | Large `inactive_timeout` | Lower `inactive_timeout` for faster delivery |
| Logs dropped | Buffer overflow | Increase `batch_max_size`; reduce delivery latency |
| Missing request body | `include_req_body: false` | Set to `true` (caution: memory impact) |
| Auth rejected | Wrong `auth_header` value | Include full header value (e.g. `Bearer <token>`) |
