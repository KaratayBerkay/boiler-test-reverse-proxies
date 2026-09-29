---
title: "limit-req plugin"
description: "Skill for configuring the Apache APISIX limit-req plugin via the a6 CLI. Covers leaky-bucket rate limiting, rate/burst configuration, nodelay behavior, key types, Redis policies for distributed limiting, traffic smoothing, and common operational patterns including combination with limit-count."
metadata:
  category: plugin
  plugin_name: limit-req
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 consumer create
    - a6 consumer update
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-limit-req/SKILL.md
---
# limit-req plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `limit-req` plugin rate-limits requests using the leaky bucket algorithm.
Unlike `limit-count` (fixed window), it provides smooth traffic shaping by
throttling burst requests with configurable delays. This prevents traffic spikes
from overwhelming upstream services.

## When to Use

- Smooth traffic to protect upstream from sudden spikes
- Enforce per-second QPS limits
- Throttle (delay) excess requests instead of rejecting them immediately
- Combine with `limit-count` for both per-second and per-hour limits

## Plugin Configuration Reference

### Core Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `rate` | number | **Yes** | — | Sustained requests per second (QPS). > 0 |
| `burst` | number | **Yes** | — | Extra burst capacity above rate. >= 0 |
| `key` | string | **Yes** | — | Variable to count requests by |
| `key_type` | string | No | `"var"` | Key type: `"var"` or `"var_combination"` |
| `rejected_code` | integer | No | `503` | HTTP status on rejection (200–599) |
| `rejected_msg` | string | No | — | Custom rejection message body |
| `nodelay` | boolean | No | `false` | If true, don't delay burst requests |
| `allow_degradation` | boolean | No | `false` | Allow requests when plugin fails |
| `policy` | string | No | `"local"` | Storage: `"local"`, `"redis"`, or `"redis-cluster"` |

### Redis Fields (when `policy: "redis"`)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `redis_host` | string | **Yes** | — |
| `redis_port` | integer | No | `6379` |
| `redis_username` | string | No | — |
| `redis_password` | string | No | — |
| `redis_database` | integer | No | `0` |
| `redis_timeout` | integer | No | `1000` |
| `redis_ssl` | boolean | No | `false` |

### Redis Cluster Fields (when `policy: "redis-cluster"`)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `redis_cluster_nodes` | array[string] | **Yes** | — |
| `redis_cluster_name` | string | **Yes** | — |
| `redis_password` | string | No | — |
| `redis_timeout` | integer | No | `1000` |
| `redis_cluster_ssl` | boolean | No | `false` |

## Leaky Bucket Algorithm

```
Incoming requests → [   Bucket (burst capacity)   ] → Leak at 'rate' per second → Upstream
                    ↓ overflow (> rate + burst)
                    Rejected (503/429)
```

| Request Rate | Behavior |
|-------------|----------|
| ≤ `rate` | Processed immediately |
| > `rate` but ≤ `rate + burst` | **Delayed** (smoothed) if `nodelay: false`; **immediate** if `nodelay: true` |
| > `rate + burst` | **Rejected** with `rejected_code` |

### nodelay Explained

- **`nodelay: false`** (default): Burst requests are delayed (APISIX sleeps)
  to smooth traffic. Higher latency for burst requests but protects upstream.
- **`nodelay: true`**: Burst requests are processed immediately without delay.
  Better latency but upstream sees spikes up to `rate + burst`.

## Step-by-Step: Basic Rate Limiting

### 1. Strict QPS limit (no burst)

```bash
a6 route create -f - <<'EOF'
{
  "id": "strict-qps",
  "uri": "/api/*",
  "plugins": {
    "limit-req": {
      "rate": 10,
      "burst": 0,
      "key": "remote_addr",
      "rejected_code": 429,
      "nodelay": true
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

10 requests per second per IP. Anything above is immediately rejected.

### 2. Smooth traffic with burst allowance

```bash
a6 route create -f - <<'EOF'
{
  "id": "smooth-api",
  "uri": "/api/*",
  "plugins": {
    "limit-req": {
      "rate": 5,
      "burst": 10,
      "key": "remote_addr",
      "rejected_code": 429
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

- 5 req/s sustained rate
- Up to 10 extra burst requests (delayed to smooth traffic)
- Requests above 15/s rejected with 429

## Common Patterns

### Multi-variable key

```json
{
  "plugins": {
    "limit-req": {
      "rate": 10,
      "burst": 5,
      "key_type": "var_combination",
      "key": "$remote_addr $http_x_api_version",
      "rejected_code": 429
    }
  }
}
```

Separate buckets per (IP + API version header) combination.

### Combine limit-req + limit-count

```json
{
  "plugins": {
    "limit-req": {
      "rate": 10,
      "burst": 20,
      "key": "remote_addr",
      "rejected_code": 429
    },
    "limit-count": {
      "count": 1000,
      "time_window": 3600,
      "key": "remote_addr",
      "rejected_code": 429
    }
  }
}
```

- `limit-req`: Smooths per-second traffic (10 QPS with burst)
- `limit-count`: Enforces hourly quota (1000/hour)

This prevents both short-term spikes and long-term abuse.

### Distributed rate limiting with Redis

```json
{
  "plugins": {
    "limit-req": {
      "rate": 100,
      "burst": 50,
      "key": "remote_addr",
      "policy": "redis",
      "redis_host": "redis.example.com",
      "redis_port": 6379,
      "redis_password": "secret",
      "rejected_code": 429
    }
  }
}
```

## limit-req vs limit-count

| Aspect | limit-req | limit-count |
|--------|-----------|-------------|
| Algorithm | Leaky bucket | Fixed window |
| Unit | Requests per second | Requests per time window |
| Burst handling | Delays or allows | Hard reject |
| Traffic shaping | Smooth | Bursty at window boundaries |
| Response headers | None | X-RateLimit-* |
| Group support | No | Yes |
| Best for | QPS protection, traffic smoothing | Quota enforcement, API plans |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| High latency on burst | `nodelay: false` delays requests | Set `nodelay: true` for lower latency |
| All burst requests rejected | `burst: 0` | Increase `burst` to allow some excess |
| No rate limit headers | `limit-req` doesn't add headers | Use `limit-count` if headers needed |
| Limits not shared across nodes | `policy: "local"` | Switch to `"redis"` or `"redis-cluster"` |
| Key empty, single bucket for all | Variable doesn't exist | Verify key variable name |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: smooth-api
    uri: /api/*
    plugins:
      limit-req:
        rate: 10
        burst: 20
        key: remote_addr
        rejected_code: 429
    upstream_id: api-upstream
upstreams:
  - id: api-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```
