---
title: "datadog plugin"
description: "Skill for configuring the Apache APISIX datadog plugin via the a6 CLI. Covers pushing custom metrics to Datadog via DogStatsD, metric tags, batching, plugin metadata for global DogStatsD server config, and Datadog Agent integration."
metadata:
  category: plugin
  plugin_name: datadog
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-datadog/SKILL.md
---
# datadog plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `datadog` plugin pushes per-request metrics to a Datadog Agent via the
DogStatsD protocol (UDP). It reports request counts, latency, bandwidth,
and upstream timing with automatic tags for route, service, consumer,
status code, and more.

## When to Use

- Monitor APISIX with Datadog APM and dashboards
- Track request rates, latency, and error rates per route
- Add custom tags for business-level metrics
- Integrate with existing Datadog infrastructure

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prefer_name` | boolean | No | `true` | Use route/service name instead of ID in tags |
| `include_path` | boolean | No | `false` | Include HTTP path pattern in tags |
| `include_method` | boolean | No | `false` | Include HTTP method in tags |
| `constant_tags` | array | No | `[]` | Static tags for this route (e.g. `["env:prod"]`) |
| `batch_max_size` | integer | No | `1000` | Max entries per batch |
| `inactive_timeout` | integer | No | `5` | Seconds before flushing batch |
| `buffer_duration` | integer | No | `60` | Max age of oldest entry |
| `max_retry_count` | integer | No | `0` | Retry attempts |

## Plugin Metadata (Global Configuration)

Set the DogStatsD server address for all routes:

```bash
curl "$(a6 context current -o json | jq -r .server)/apisix/admin/plugin_metadata/datadog" \
  -X PUT \
  -H "X-API-KEY: $(a6 context current -o json | jq -r .api_key)" \
  -d '{
    "host": "127.0.0.1",
    "port": 8125,
    "namespace": "apisix",
    "constant_tags": ["source:apisix"]
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | string | `"127.0.0.1"` | DogStatsD server host |
| `port` | integer | `8125` | DogStatsD server port |
| `namespace` | string | `"apisix"` | Metric name prefix |
| `constant_tags` | array | `["source:apisix"]` | Global tags for all metrics |

## Metrics Emitted

| Metric | Type | Description |
|--------|------|-------------|
| `{namespace}.request.counter` | counter | Request count |
| `{namespace}.request.latency` | histogram | Total request latency (ms) |
| `{namespace}.upstream.latency` | histogram | Upstream response time (ms) |
| `{namespace}.apisix.latency` | histogram | APISIX processing time (ms) |
| `{namespace}.ingress.size` | timer | Request body size (bytes) |
| `{namespace}.egress.size` | timer | Response body size (bytes) |

Default namespace is `apisix`, so metrics appear as `apisix.request.counter`.

## Automatic Tags

| Tag | Always Present | Description |
|-----|----------------|-------------|
| `route_name` | Yes | Route ID or name |
| `service_name` | If route has service | Service ID or name |
| `consumer` | If authenticated | Consumer username |
| `balancer_ip` | Yes | Upstream IP that handled the request |
| `response_status` | Yes | HTTP status code (e.g. `200`) |
| `response_status_class` | Yes | Status class (e.g. `2xx`, `5xx`) |
| `scheme` | Yes | `http`, `https`, `grpc`, `grpcs` |
| `path` | If `include_path: true` | HTTP path pattern |
| `method` | If `include_method: true` | HTTP method |

## Step-by-Step: Send Metrics to Datadog

### 1. Configure plugin metadata (DogStatsD address)

```bash
curl "$(a6 context current -o json | jq -r .server)/apisix/admin/plugin_metadata/datadog" \
  -X PUT \
  -H "X-API-KEY: $(a6 context current -o json | jq -r .api_key)" \
  -d '{
    "host": "127.0.0.1",
    "port": 8125,
    "namespace": "apisix",
    "constant_tags": ["source:apisix", "env:production"]
  }'
```

### 2. Enable on a route

```bash
a6 route create -f - <<'EOF'
{
  "id": "monitored-api",
  "name": "api-v1",
  "uri": "/api/v1/*",
  "plugins": {
    "datadog": {
      "prefer_name": true,
      "include_path": true,
      "include_method": true
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

### 3. Verify in Datadog

Open Datadog → Metrics Explorer → search for `apisix.request.counter`.

## Common Patterns

### Custom constant tags per route

```json
{
  "plugins": {
    "datadog": {
      "prefer_name": true,
      "constant_tags": [
        "team:platform",
        "api_version:v2",
        "tier:premium"
      ]
    }
  }
}
```

### Remote Datadog Agent

```bash
curl "$(a6 context current -o json | jq -r .server)/apisix/admin/plugin_metadata/datadog" \
  -X PUT \
  -H "X-API-KEY: $(a6 context current -o json | jq -r .api_key)" \
  -d '{
    "host": "datadog-agent.internal",
    "port": 8125,
    "namespace": "mycompany",
    "constant_tags": ["source:apisix", "datacenter:us-east-1"]
  }'
```

### Docker Compose with Datadog Agent

```yaml
services:
  apisix:
    image: apache/apisix:3.15.0-debian
    depends_on:
      - datadog-agent

  datadog-agent:
    image: datadog/agent:latest
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_SITE=datadoghq.com
      - DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true
    ports:
      - "8125:8125/udp"
```

## Datadog Dashboard Queries

```
# Request rate by route
sum:apisix.request.counter{*} by {route_name}.as_count()

# P95 latency
percentile:apisix.request.latency{*} by {route_name}, p:95

# Error rate
sum:apisix.request.counter{response_status_class:5xx}.as_count()

# Upstream health by IP
avg:apisix.upstream.latency{*} by {balancer_ip}
```

## Config Sync Example

```yaml
version: "1"
routes:
  - id: monitored-api
    name: api-v1
    uri: /api/v1/*
    plugins:
      datadog:
        prefer_name: true
        include_path: true
        include_method: true
        constant_tags:
          - "team:platform"
    upstream_id: my-upstream
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No metrics in Datadog | Agent not receiving UDP | Check `host`/`port` in plugin metadata; verify Agent config |
| Missing consumer tag | No authentication on route | Tag only appears for authenticated requests |
| Wrong metric namespace | Default `apisix` | Change `namespace` in plugin metadata |
| Tags rejected by Datadog | Invalid tag format | Tags must start with a letter, not end with `:` |
| Metrics delayed | Large `inactive_timeout` | Lower batch settings for faster delivery |
