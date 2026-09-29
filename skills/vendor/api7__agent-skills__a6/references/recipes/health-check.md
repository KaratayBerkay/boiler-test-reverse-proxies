---
title: "health check recipe"
description: "Recipe skill for configuring upstream health checks using the a6 CLI. Covers active health checks (HTTP probing), passive health checks (response analysis), combining both, configuring healthy/unhealthy thresholds, and monitoring upstream node status."
metadata:
  category: recipe
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 upstream create
    - a6 upstream update
    - a6 upstream get
    - a6 upstream health
  source: https://github.com/api7/a6/blob/main/skills/a6-recipe-health-check/SKILL.md
---
# health check recipe

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

Health checks monitor upstream backend nodes and automatically remove
unhealthy nodes from the load balancer pool. APISIX supports two types:

- **Active**: APISIX periodically probes each node with HTTP/HTTPS/TCP requests
- **Passive**: APISIX analyzes real traffic responses to detect failures

Use both together for the most robust setup.

## When to Use

- Automatically remove failing backend nodes from rotation
- Detect and recover from backend failures without manual intervention
- Ensure high availability across multiple backend instances
- Monitor backend health status via the a6 CLI

## Health Check Configuration Reference

### Active Health Check

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `checks.active.type` | string | `"http"` | Check type: `"http"`, `"https"`, or `"tcp"` |
| `checks.active.http_path` | string | `"/"` | HTTP path to probe |
| `checks.active.host` | string | — | Host header for HTTP probes |
| `checks.active.port` | integer | — | Override port for probing (default: use node port) |
| `checks.active.timeout` | number | `1` | Probe timeout in seconds |
| `checks.active.concurrency` | integer | `10` | Number of concurrent probes |
| `checks.active.https_verify_certificate` | boolean | `true` | Verify TLS certificate for HTTPS probes |
| `checks.active.req_headers` | array[string] | — | Additional request headers for probes |
| `checks.active.healthy.interval` | integer | `1` | Seconds between probes for healthy nodes |
| `checks.active.healthy.successes` | integer | `2` | Consecutive successes to mark node healthy |
| `checks.active.healthy.http_statuses` | array[integer] | `[200, 302]` | HTTP codes considered healthy |
| `checks.active.unhealthy.interval` | integer | `1` | Seconds between probes for unhealthy nodes |
| `checks.active.unhealthy.http_failures` | integer | `5` | Consecutive HTTP failures to mark unhealthy |
| `checks.active.unhealthy.tcp_failures` | integer | `2` | Consecutive TCP failures to mark unhealthy |
| `checks.active.unhealthy.timeouts` | integer | `3` | Consecutive timeouts to mark unhealthy |
| `checks.active.unhealthy.http_statuses` | array[integer] | `[429, 404, 500, 501, 502, 503, 504, 505]` | HTTP codes considered unhealthy |

### Passive Health Check

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `checks.passive.type` | string | `"http"` | Check type: `"http"`, `"https"`, or `"tcp"` |
| `checks.passive.healthy.successes` | integer | `5` | Consecutive successes to mark healthy |
| `checks.passive.healthy.http_statuses` | array[integer] | `[200, 201, 202, ..., 399]` | HTTP codes considered healthy |
| `checks.passive.unhealthy.http_failures` | integer | `5` | Consecutive failures to mark unhealthy |
| `checks.passive.unhealthy.tcp_failures` | integer | `2` | Consecutive TCP failures to mark unhealthy |
| `checks.passive.unhealthy.timeouts` | integer | `7` | Consecutive timeouts to mark unhealthy |
| `checks.passive.unhealthy.http_statuses` | array[integer] | `[429, 500, 503]` | HTTP codes considered unhealthy |

## Step-by-Step: Configure Health Checks

### 1. Active HTTP health check

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "backend",
  "type": "roundrobin",
  "nodes": {
    "backend-1:8080": 1,
    "backend-2:8080": 1,
    "backend-3:8080": 1
  },
  "checks": {
    "active": {
      "type": "http",
      "http_path": "/health",
      "healthy": {
        "interval": 5,
        "successes": 2,
        "http_statuses": [200]
      },
      "unhealthy": {
        "interval": 3,
        "http_failures": 3,
        "http_statuses": [500, 502, 503]
      }
    }
  }
}
EOF
```

APISIX probes `/health` on each node:
- Every 5s for healthy nodes
- Every 3s for unhealthy nodes
- 3 consecutive failures → node removed
- 2 consecutive successes → node restored

### 2. Passive health check (analyze real traffic)

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "backend-passive",
  "type": "roundrobin",
  "nodes": {
    "backend-1:8080": 1,
    "backend-2:8080": 1
  },
  "checks": {
    "passive": {
      "type": "http",
      "unhealthy": {
        "http_failures": 3,
        "http_statuses": [500, 502, 503],
        "timeouts": 3
      },
      "healthy": {
        "successes": 5,
        "http_statuses": [200, 201, 202, 203, 204]
      }
    }
  }
}
EOF
```

No probing — APISIX watches real traffic responses. After 3 consecutive 5xx
errors, the node is removed. After 5 consecutive successes, it's restored.

**Note**: Passive-only health checks cannot recover a node that receives no
traffic. Combine with active checks for full coverage.

### 3. Combined active + passive (recommended for production)

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "production-backend",
  "type": "roundrobin",
  "nodes": {
    "backend-1:8080": 1,
    "backend-2:8080": 1,
    "backend-3:8080": 1
  },
  "checks": {
    "active": {
      "type": "http",
      "http_path": "/health",
      "healthy": {
        "interval": 5,
        "successes": 2,
        "http_statuses": [200]
      },
      "unhealthy": {
        "interval": 2,
        "http_failures": 3,
        "timeouts": 2,
        "http_statuses": [500, 502, 503, 504]
      }
    },
    "passive": {
      "type": "http",
      "unhealthy": {
        "http_failures": 3,
        "http_statuses": [500, 502, 503],
        "timeouts": 3
      },
      "healthy": {
        "successes": 3,
        "http_statuses": [200, 201, 204]
      }
    }
  }
}
EOF
```

### 4. Check upstream health status

```bash
# View health status of all nodes
a6 upstream health backend
```

## Common Patterns

### TCP health check (non-HTTP services)

```json
{
  "checks": {
    "active": {
      "type": "tcp",
      "healthy": {
        "interval": 5,
        "successes": 2
      },
      "unhealthy": {
        "interval": 2,
        "tcp_failures": 3,
        "timeouts": 2
      }
    }
  }
}
```

### HTTPS health check with certificate verification

```json
{
  "checks": {
    "active": {
      "type": "https",
      "http_path": "/health",
      "https_verify_certificate": true,
      "healthy": {
        "interval": 10,
        "successes": 2,
        "http_statuses": [200]
      },
      "unhealthy": {
        "interval": 5,
        "http_failures": 3
      }
    }
  }
}
```

### Custom probe headers (for auth-protected health endpoints)

```json
{
  "checks": {
    "active": {
      "type": "http",
      "http_path": "/internal/health",
      "host": "health.internal",
      "req_headers": [
        "Authorization: Bearer health-check-token",
        "X-Health-Check: true"
      ],
      "healthy": {
        "interval": 10,
        "successes": 2
      },
      "unhealthy": {
        "interval": 5,
        "http_failures": 3
      }
    }
  }
}
```

### Aggressive unhealthy detection (fast failover)

```json
{
  "checks": {
    "active": {
      "type": "http",
      "http_path": "/health",
      "timeout": 2,
      "healthy": {
        "interval": 3,
        "successes": 1
      },
      "unhealthy": {
        "interval": 1,
        "http_failures": 1,
        "timeouts": 1
      }
    }
  }
}
```

Detects failures within 1 second and recovers within 3 seconds.

## Config Sync Example

```yaml
version: "1"
upstreams:
  - id: production-backend
    type: roundrobin
    nodes:
      "backend-1:8080": 1
      "backend-2:8080": 1
      "backend-3:8080": 1
    checks:
      active:
        type: http
        http_path: /health
        healthy:
          interval: 5
          successes: 2
          http_statuses: [200]
        unhealthy:
          interval: 2
          http_failures: 3
          timeouts: 2
          http_statuses: [500, 502, 503, 504]
      passive:
        type: http
        unhealthy:
          http_failures: 3
          http_statuses: [500, 502, 503]
          timeouts: 3
        healthy:
          successes: 3
          http_statuses: [200, 201, 204]
routes:
  - id: api
    uri: /api/*
    upstream_id: production-backend
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Health checks not running | No route references the upstream | Health checks only run for upstreams attached to at least one route |
| All nodes marked unhealthy | Health endpoint returns wrong status code | Verify `http_statuses` includes your health endpoint's response code |
| Node not recovering | Passive-only: no traffic reaches unhealthy node | Add active health checks for recovery |
| Probe hitting wrong endpoint | Default `http_path` is `/` | Set `http_path` to your actual health endpoint |
| TLS probe fails | Certificate verification fails | Set `https_verify_certificate: false` or fix certificates |
| Health checks too aggressive | Low thresholds with flaky endpoints | Increase `failures` threshold and `interval` |
| `a6 upstream health` shows no data | APISIX hasn't started health checks yet | Wait for the first probe interval to complete |
