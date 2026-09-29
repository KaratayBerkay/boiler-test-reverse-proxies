---
title: "skywalking plugin"
description: "Skill for configuring the Apache APISIX skywalking plugin via the a6 CLI. Covers distributed tracing with Apache SkyWalking OAP, sampling configuration, service topology, and integration with skywalking-logger for trace-log correlation."
metadata:
  category: plugin
  plugin_name: skywalking
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-skywalking/SKILL.md
---
# skywalking plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `skywalking` plugin integrates APISIX with Apache SkyWalking for
distributed tracing. It creates entry and exit spans for each request,
reports them to SkyWalking OAP via HTTP, and enables service topology
visualization and performance analysis.

## When to Use

- Trace requests across microservices via SkyWalking
- Visualize service topology and dependency maps
- Analyze per-route and per-service latency
- Correlate traces with logs using `skywalking-logger`

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `sample_ratio` | number | No | `1` | Sampling rate from 0.00001 to 1 (1 = trace all) |

## Global Configuration (config.yaml)

Configure in APISIX `config.yaml` under `plugin_attr`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `service_name` | string | `"APISIX"` | Service name in SkyWalking UI |
| `service_instance_name` | string | `"APISIX Instance Name"` | Instance name (use `$hostname` for dynamic) |
| `endpoint_addr` | string | `http://127.0.0.1:12800` | SkyWalking OAP HTTP endpoint |
| `report_interval` | integer | `3` | Reporting interval in seconds |

```yaml
plugin_attr:
  skywalking:
    service_name: api-gateway
    service_instance_name: "$hostname"
    endpoint_addr: http://skywalking-oap:12800
    report_interval: 5
```

## Step-by-Step: Enable SkyWalking Tracing

### 1. Ensure SkyWalking OAP is running

```bash
# Docker example
docker run -d --name skywalking-oap \
  -p 12800:12800 -p 11800:11800 \
  apache/skywalking-oap-server:latest
```

### 2. Configure APISIX global settings

Add to `config.yaml`:

```yaml
plugin_attr:
  skywalking:
    service_name: my-gateway
    service_instance_name: "$hostname"
    endpoint_addr: http://skywalking-oap:12800
```

### 3. Enable on a route

```bash
a6 route create -f - <<'EOF'
{
  "id": "traced-api",
  "uri": "/api/*",
  "plugins": {
    "skywalking": {
      "sample_ratio": 1
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

### 4. Send a request and view traces

```bash
curl http://127.0.0.1:9080/api/hello
```

View traces in SkyWalking UI at `http://skywalking-ui:8080`.

## Common Patterns

### Partial sampling (production)

```json
{
  "plugins": {
    "skywalking": {
      "sample_ratio": 0.1
    }
  }
}
```

Traces 10% of requests. Sufficient for production traffic analysis without
excessive overhead.

### Trace-log correlation with skywalking-logger

```json
{
  "plugins": {
    "skywalking": {
      "sample_ratio": 1
    },
    "skywalking-logger": {
      "endpoint_addr": "http://skywalking-oap:12800"
    }
  }
}
```

Associates access logs with trace IDs in the SkyWalking UI, enabling
click-through from traces to logs.

### Enable globally

```bash
curl "$(a6 context current -o json | jq -r .server)/apisix/admin/global_rules" \
  -X PUT \
  -H "X-API-KEY: $(a6 context current -o json | jq -r .api_key)" \
  -d '{
    "id": "skywalking-global",
    "plugins": {
      "skywalking": {
        "sample_ratio": 0.5
      }
    }
  }'
```

## Span Structure

The plugin creates two spans per request:

- **entrySpan**: From request arrival to response completion (component ID 6002)
- **exitSpan**: From upstream call start to response received (component ID 6002)

## Config Sync Example

```yaml
version: "1"
routes:
  - id: traced-api
    uri: /api/*
    plugins:
      skywalking:
        sample_ratio: 1
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
| No traces in SkyWalking UI | Wrong `endpoint_addr` | Verify OAP is reachable at the configured address |
| Missing service in topology | `service_name` mismatch | Check `plugin_attr.skywalking.service_name` in config.yaml |
| High overhead | `sample_ratio: 1` in production | Lower to 0.01-0.1 for high-traffic routes |
| Traces not correlated | Backend not instrumented | Install SkyWalking agent in upstream services |
| Plugin not working | Not in plugins list | Ensure `skywalking` is in the `plugins` array in config.yaml |
