---
title: "limit-count plugin"
description: "Skill for configuring the APISIX limit-count plugin via the a6 CLI. Covers fixed and sliding windows, Redis Sentinel, delayed sync, and shared quotas."
metadata:
  category: plugin
  plugin_name: limit-count
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 consumer create
    - a6 consumer update
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-limit-count/SKILL.md
---
# limit-count plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `limit-count` plugin rate-limits requests using a counter in a time window.
Define a maximum number of requests (`count`) within an interval (`time_window`).
The default `window_type` is `fixed`. Set `window_type: sliding` to smooth bursts
at window boundaries. Supports per-IP, per-consumer, per-header, or custom
variable keys. For distributed APISIX deployments, share counters through Redis,
Redis Cluster, or Redis Sentinel (`policy: redis-sentinel`).

Redis Sentinel, sliding windows, and delayed Redis synchronization (`sync_interval`)
are available from APISIX 3.18.0. Field tables and examples:
https://docs.api7.ai/hub/limit-count

## When to Use

- Simple request counting (e.g., 100 requests per hour)
- API quota enforcement per consumer or API key
- Shared rate limits across multiple APISIX nodes (via Redis)
- Grouped quotas across multiple routes

## Plugin Configuration Reference

### Core Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `count` | integer | Yes* | — | Max requests allowed in the time window. > 0 |
| `time_window` | integer | Yes* | — | Time window in seconds. > 0 |
| `key_type` | string | No | `"var"` | Key type: `"var"`, `"var_combination"`, or `"constant"` |
| `key` | string | No | `"remote_addr"` | Variable name or combination for counting |
| `rejected_code` | integer | No | `503` | HTTP status on rejection (200–599) |
| `rejected_msg` | string | No | — | Custom rejection message body |
| `group` | string | No | — | Share counters across routes with same group ID |
| `policy` | string | No | `"local"` | Storage: `"local"`, `"redis"`, `"redis-cluster"`, or `"redis-sentinel"` |
| `window_type` | string | No | `"fixed"` | `"fixed"` or `"sliding"` (APISIX 3.18.0+) |
| `sync_interval` | number | No | `-1` | Redis sync interval in seconds. `-1` syncs every request. Min `0.1` when enabled; must be smaller than a numeric `time_window` |
| `show_limit_quota_header` | boolean | No | `true` | Include X-RateLimit-* headers in responses |
| `allow_degradation` | boolean | No | `false` | Allow requests when plugin fails |

*Required unless using `rules` array.

### Redis Fields (when `policy: "redis"`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `redis_host` | string | **Yes** | — | Redis server address |
| `redis_port` | integer | No | `6379` | Redis port |
| `redis_username` | string | No | — | Redis ACL username |
| `redis_password` | string | No | — | Redis password |
| `redis_database` | integer | No | `0` | Redis database index |
| `redis_timeout` | integer | No | `1000` | Timeout in milliseconds |
| `redis_ssl` | boolean | No | `false` | Enable TLS to Redis |

### Redis Cluster Fields (when `policy: "redis-cluster"`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `redis_cluster_nodes` | array[string] | **Yes** | — | Array of `"host:port"` (min 2) |
| `redis_cluster_name` | string | **Yes** | — | Cluster name |
| `redis_password` | string | No | — | Cluster password |
| `redis_timeout` | integer | No | `1000` | Timeout in milliseconds |
| `redis_cluster_ssl` | boolean | No | `false` | Enable TLS |

### Redis Sentinel Fields (when `policy: "redis-sentinel"`, APISIX 3.18.0+)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `redis_sentinels` | array[object] | **Yes** | — | Sentinel nodes: `{ "host": "...", "port": 26379 }` |
| `redis_master_name` | string | **Yes** | — | Sentinel-monitored master name |
| `redis_role` | string | No | `"master"` | `"master"` or `"slave"` |
| `redis_username` | string | No | — | Redis ACL username |
| `redis_password` | string | No | — | Redis password |
| `redis_database` | integer | No | `0` | Redis database index |
| `sentinel_username` | string | No | — | Redis Sentinel ACL username |
| `sentinel_password` | string | No | — | Redis Sentinel password |
| `redis_connect_timeout` | integer | No | `1000` | Connection timeout in milliseconds |
| `redis_read_timeout` | integer | No | `1000` | Read timeout in milliseconds |
| `redis_keepalive_timeout` | integer | No | `60000` | Keepalive timeout in milliseconds |

## Key Types

| `key_type` | `key` Format | Example | Description |
|------------|-------------|---------|-------------|
| `"var"` | NGINX variable (no `$`) | `"remote_addr"` | Single variable |
| `"var_combination"` | `$var1 $var2` | `"$remote_addr $consumer_name"` | Multiple variables combined |
| `"constant"` | Any string | `"global"` | Same counter for all requests |

## Response Headers

When `show_limit_quota_header: true` (default):

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Total quota for the time window |
| `X-RateLimit-Remaining` | Remaining requests in current window |
| `X-RateLimit-Reset` | Seconds until counter resets |

## Step-by-Step: Basic Rate Limiting

### 1. Rate limit by client IP (route-level)

```bash
a6 route create -f - <<'EOF'
{
  "id": "rate-limited-api",
  "uri": "/api/*",
  "plugins": {
    "limit-count": {
      "count": 100,
      "time_window": 60,
      "key_type": "var",
      "key": "remote_addr",
      "rejected_code": 429,
      "rejected_msg": "Rate limit exceeded. Try again later."
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

100 requests per 60 seconds per client IP.

### 2. Rate limit per consumer

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "free-tier",
  "plugins": {
    "limit-count": {
      "count": 100,
      "time_window": 3600,
      "rejected_code": 429
    }
  }
}
EOF

a6 consumer create -f - <<'EOF'
{
  "username": "premium",
  "plugins": {
    "limit-count": {
      "count": 10000,
      "time_window": 3600,
      "rejected_code": 429
    }
  }
}
EOF
```

Consumer-level limits apply across all routes the consumer accesses.

## Common Patterns

### Shared quota across routes (group)

```json
{
  "plugins": {
    "limit-count": {
      "count": 1000,
      "time_window": 3600,
      "group": "api-v1",
      "rejected_code": 429
    }
  }
}
```

All routes with `"group": "api-v1"` share the same 1000 req/hour counter.
**Important**: All routes in a group must have identical `limit-count` config.

### Multi-variable key (IP + consumer)

```json
{
  "plugins": {
    "limit-count": {
      "count": 50,
      "time_window": 60,
      "key_type": "var_combination",
      "key": "$remote_addr $consumer_name",
      "rejected_code": 429
    }
  }
}
```

### Global rate limit (all requests share one counter)

```json
{
  "plugins": {
    "limit-count": {
      "count": 10000,
      "time_window": 60,
      "key_type": "constant",
      "key": "global",
      "rejected_code": 429
    }
  }
}
```

### Distributed rate limiting with Redis

```json
{
  "plugins": {
    "limit-count": {
      "count": 1000,
      "time_window": 60,
      "key": "remote_addr",
      "policy": "redis",
      "redis_host": "redis.example.com",
      "redis_port": 6379,
      "redis_password": "secret",
      "redis_database": 0,
      "redis_ssl": true,
      "rejected_code": 429
    }
  }
}
```

Use Redis when running multiple APISIX nodes to share counters.

### Redis Sentinel

```json
{
  "plugins": {
    "limit-count": {
      "count": 1000,
      "time_window": 60,
      "key": "remote_addr",
      "policy": "redis-sentinel",
      "redis_master_name": "mymaster",
      "redis_sentinels": [
        { "host": "192.168.1.10", "port": 26379 },
        { "host": "192.168.1.11", "port": 26379 }
      ],
      "rejected_code": 429
    }
  }
}
```

### Sliding window and delayed Redis sync

```json
{
  "plugins": {
    "limit-count": {
      "count": 1000,
      "time_window": 60,
      "window_type": "sliding",
      "policy": "redis",
      "redis_host": "redis.example.com",
      "sync_interval": 1,
      "rejected_code": 429
    }
  }
}
```

`sync_interval` also works with `redis-cluster` and `redis-sentinel`. A numeric
`time_window` must be greater than `sync_interval`, or APISIX rejects the plugin
configuration. If a variable-based `time_window` resolves to a value less than
or equal to `sync_interval` at request time, APISIX falls back to per-request
synchronization.

### Redis cluster

```json
{
  "plugins": {
    "limit-count": {
      "count": 1000,
      "time_window": 60,
      "key": "remote_addr",
      "policy": "redis-cluster",
      "redis_cluster_nodes": [
        "192.168.1.10:6379",
        "192.168.1.11:6379",
        "192.168.1.12:6379"
      ],
      "redis_cluster_name": "apisix-cluster",
      "redis_password": "secret",
      "rejected_code": 429
    }
  }
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Limits not shared across APISIX nodes | Using `policy: "local"` (default) | Switch to `"redis"`, `"redis-cluster"`, or `"redis-sentinel"` |
| Group config rejected | Mismatched configs in same group | Ensure all routes in group have identical limit-count config |
| Unexpected counter reset | Fixed-window boundary | Normal for `window_type: fixed`; use `"sliding"` to smooth bursts |
| Key empty, all clients share one counter | Variable doesn't exist | Verify key variable name; falls back to `remote_addr` |
| Rate limit headers missing | `show_limit_quota_header: false` | Set to `true` (default) |
| 503 instead of 429 | Default `rejected_code` is 503 | Set `rejected_code: 429` explicitly |

## Fixed-Window Algorithm Note

`limit-count` defaults to a fixed-window algorithm. Counters reset at exact
intervals, so a burst at the boundary of two windows can temporarily exceed the
intended rate (for example, 100 req/min allows 200 requests if 100 come at
t=59s and 100 at t=61s). Set `window_type: sliding` to weight the previous
window, or combine with `limit-req` (leaky bucket).

## Config Sync Example

```yaml
version: "1"
consumers:
  - username: free-tier
    plugins:
      limit-count:
        count: 100
        time_window: 3600
        rejected_code: 429
routes:
  - id: rate-limited-api
    uri: /api/*
    plugins:
      limit-count:
        count: 1000
        time_window: 60
        key: remote_addr
        rejected_code: 429
    upstream_id: api-upstream
upstreams:
  - id: api-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```
