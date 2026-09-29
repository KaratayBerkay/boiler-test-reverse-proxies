---
title: "circuit breaker recipe"
description: "Recipe skill for implementing circuit breaker patterns using the a6 CLI. Covers the api-breaker plugin for automatic upstream circuit breaking, configuring unhealthy thresholds, healthy recovery, response code classification, and integration with health checks."
metadata:
  category: recipe
  plugin_name: api-breaker
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 route get
  source: https://github.com/api7/a6/blob/main/skills/a6-recipe-circuit-breaker/SKILL.md
---
# circuit breaker recipe

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

A circuit breaker prevents cascading failures by detecting unhealthy upstream
services and temporarily stopping requests to them. When the upstream returns
too many errors, the circuit "opens" and APISIX returns errors immediately
without forwarding requests. After a cooldown period, it "half-opens" to test
if the upstream has recovered.

APISIX implements this via the `api-breaker` plugin, which tracks response
status codes and manages circuit state automatically.

## When to Use

- Protect your API from cascading failures when an upstream goes down
- Automatically stop sending traffic to failing backends
- Allow failing services time to recover before retrying
- Return fast error responses instead of waiting for timeouts

## Circuit Breaker States

```
          ┌─────────┐
          │ CLOSED   │ ← Normal operation: requests flow through
          │(healthy) │
          └────┬─────┘
               │ Error count exceeds threshold
               ▼
          ┌─────────┐
          │  OPEN    │ ← Breaker tripped: returns 502 immediately
          │(tripped) │
          └────┬─────┘
               │ After cooldown period
               ▼
         ┌──────────┐
         │HALF-OPEN │ ← Test: allows one request through
         │ (testing) │
         └─────┬────┘
               │
       ┌───────┴───────┐
       │               │
   Success          Failure
       │               │
       ▼               ▼
   CLOSED           OPEN (longer cooldown)
```

## Plugin Configuration Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `break_response_code` | integer | **Yes** | — | HTTP status code returned when circuit is open (e.g., 502, 503). |
| `break_response_body` | string | No | — | Response body returned when circuit is open. |
| `break_response_headers` | array[object] | No | — | Response headers when circuit is open. Format: `[{"key": "name", "value": "val"}]`. |
| `unhealthy.http_statuses` | array[integer] | No | `[500]` | HTTP status codes from upstream that count as unhealthy. |
| `unhealthy.failures` | integer | No | `3` | Number of consecutive unhealthy responses before opening the circuit. |
| `healthy.http_statuses` | array[integer] | No | `[200]` | HTTP status codes from upstream that count as healthy (for recovery). |
| `healthy.successes` | integer | No | `3` | Number of consecutive healthy responses to close the circuit. |
| `max_breaker_sec` | integer | No | `300` | Maximum circuit-open duration in seconds. Cooldown doubles each time but caps here. |

## Breaker Timing

When the circuit opens:
1. First open: **2 seconds** cooldown
2. If it opens again: **4 seconds** (doubles)
3. Next: **8 seconds**, **16 seconds**, ...
4. Caps at `max_breaker_sec` (default 300s = 5 minutes)

During cooldown, all requests get the `break_response_code` immediately.

## Step-by-Step: Enable Circuit Breaker

### 1. Basic circuit breaker

```bash
a6 route create -f - <<'EOF'
{
  "id": "protected-api",
  "uri": "/api/*",
  "plugins": {
    "api-breaker": {
      "break_response_code": 502,
      "unhealthy": {
        "http_statuses": [500, 502, 503],
        "failures": 3
      },
      "healthy": {
        "http_statuses": [200],
        "successes": 3
      },
      "max_breaker_sec": 300
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

After 3 consecutive 500/502/503 responses, the circuit opens and returns 502
immediately. After cooldown, it tests with one request. If 3 consecutive 200s
come back, the circuit closes and normal operation resumes.

### 2. Circuit breaker with custom error body

```bash
a6 route create -f - <<'EOF'
{
  "id": "api-with-error-body",
  "uri": "/api/*",
  "plugins": {
    "api-breaker": {
      "break_response_code": 503,
      "break_response_body": "{\"error\": \"service temporarily unavailable\", \"retry_after\": 30}",
      "break_response_headers": [
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Retry-After", "value": "30"}
      ],
      "unhealthy": {
        "http_statuses": [500, 502, 503, 504],
        "failures": 5
      },
      "healthy": {
        "http_statuses": [200, 201, 204],
        "successes": 2
      },
      "max_breaker_sec": 60
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

### 3. Sensitive circuit breaker (trips on first error)

```json
{
  "plugins": {
    "api-breaker": {
      "break_response_code": 503,
      "unhealthy": {
        "http_statuses": [500, 502, 503],
        "failures": 1
      },
      "healthy": {
        "http_statuses": [200],
        "successes": 1
      },
      "max_breaker_sec": 30
    }
  }
}
```

Trips on the very first 5xx error. Recovers after one successful response.

## Combining with Health Checks

For production, combine the circuit breaker with upstream health checks.
The circuit breaker handles per-route protection while health checks manage
per-node health at the upstream level.

```bash
# Create upstream with health checks
a6 upstream create -f - <<'EOF'
{
  "id": "monitored-backend",
  "type": "roundrobin",
  "nodes": {
    "backend-1:8080": 1,
    "backend-2:8080": 1
  },
  "checks": {
    "active": {
      "type": "http",
      "http_path": "/health",
      "healthy": {
        "interval": 5,
        "successes": 2
      },
      "unhealthy": {
        "interval": 3,
        "http_failures": 3
      }
    }
  }
}
EOF

# Create route with circuit breaker
a6 route create -f - <<'EOF'
{
  "id": "api",
  "uri": "/api/*",
  "plugins": {
    "api-breaker": {
      "break_response_code": 503,
      "unhealthy": {
        "http_statuses": [500, 502, 503],
        "failures": 3
      },
      "healthy": {
        "http_statuses": [200],
        "successes": 3
      }
    }
  },
  "upstream_id": "monitored-backend"
}
EOF
```

## Config Sync Example

```yaml
version: "1"
routes:
  - id: protected-api
    uri: /api/*
    plugins:
      api-breaker:
        break_response_code: 503
        break_response_body: '{"error": "service unavailable"}'
        break_response_headers:
          - key: Content-Type
            value: application/json
          - key: Retry-After
            value: "30"
        unhealthy:
          http_statuses: [500, 502, 503]
          failures: 3
        healthy:
          http_statuses: [200]
          successes: 3
        max_breaker_sec: 300
    upstream_id: backend
upstreams:
  - id: backend
    type: roundrobin
    nodes:
      "backend:8080": 1
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Circuit never opens | `unhealthy.http_statuses` doesn't include the error code | Add the actual error codes your upstream returns |
| Circuit stays open too long | `max_breaker_sec` too high | Lower `max_breaker_sec` for faster recovery |
| Circuit flaps open/closed | Threshold too low with intermittent errors | Increase `unhealthy.failures` threshold |
| 502 from APISIX (not circuit breaker) | Upstream truly unreachable (connection refused) | Connection errors also count toward unhealthy threshold |
| Recovery too slow | `healthy.successes` too high | Lower `healthy.successes` for faster recovery |
