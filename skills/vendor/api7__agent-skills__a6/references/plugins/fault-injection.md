---
title: "fault-injection plugin"
description: "Skill for configuring the Apache APISIX fault-injection plugin via the a6 CLI. Covers injecting delays and HTTP aborts for chaos engineering, percentage-based sampling, conditional injection via vars expressions, custom response headers and body with Nginx variable interpolation."
metadata:
  category: plugin
  plugin_name: fault-injection
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-fault-injection/SKILL.md
---
# fault-injection plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `fault-injection` plugin injects faults — delays and HTTP aborts — into
requests for chaos engineering and resiliency testing. It runs in the `rewrite`
phase with priority 11000 (very early), meaning it executes before most other
plugins including authentication and rate limiting.

**Execution order:** delay first → abort second. If abort fires, subsequent
plugins do NOT execute.

## When to Use

- Chaos engineering: simulate upstream failures and slowdowns
- Resiliency testing: verify timeout handling and circuit breakers
- Load testing: add artificial latency to measure degradation
- Canary fault testing: inject faults for specific users or conditions

## Plugin Configuration Reference

At least one of `abort` or `delay` must be specified.

### abort Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `http_status` | integer | **Yes** | — | HTTP status code (≥ 200) |
| `body` | string | No | — | Response body; supports Nginx variables (`$remote_addr`) |
| `headers` | object | No | — | Response headers; values support Nginx variables |
| `percentage` | integer | No | 100 (always) | Percentage of requests to abort (0–100) |
| `vars` | array | No | — | Conditional rules using lua-resty-expr (max 20 items) |

### delay Object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `duration` | number | **Yes** | — | Delay in seconds (supports decimals: 0.5, 1.5) |
| `percentage` | integer | No | 100 (always) | Percentage of requests to delay (0–100) |
| `vars` | array | No | — | Conditional rules using lua-resty-expr (max 20 items) |

## Vars Expression Syntax

The `vars` field uses lua-resty-expr for conditional fault injection.

### Structure

```json
[
  [["condition1a"], ["condition1b"]],  // AND group 1
  [["condition2a"]]                     // AND group 2
]
// Groups joined by OR — first matching group triggers the fault
```

### Variable Access

| Prefix | Source | Example |
|--------|--------|---------|
| `arg_*` | Query parameters | `arg_name` → `?name=value` |
| `http_*` | Request headers | `http_apikey` → `X-Api-Key` header |
| (none) | Nginx built-ins | `remote_addr`, `uri`, `request_method` |

### Operators

| Operator | Example |
|----------|---------|
| `==` | `["arg_name", "==", "jack"]` |
| `~=` | `["arg_env", "~=", "prod"]` |
| `>`, `>=`, `<`, `<=` | `["arg_age", ">", 18]` |
| `~~` | `["arg_env", "~~", "[Dd]ev"]` (regex) |
| `~*` | `["arg_env", "~*", "dev"]` (case-insensitive regex) |
| `in` | `["arg_ver", "in", ["v1","v2"]]` |
| `!` | `["arg_age", "!", "<", 18]` (negation → `>=`) |
| `ipmatch` | `["remote_addr", "ipmatch", ["10.0.0.0/8"]]` |

## Step-by-Step Examples

### 1. Fixed Delay (3 Seconds)

```bash
a6 route create -f - <<'EOF'
{
  "id": "delay-test",
  "uri": "/api/*",
  "plugins": {
    "fault-injection": {
      "delay": {
        "duration": 3
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 2. Percentage-Based Abort (50% Return 503)

```bash
a6 route create -f - <<'EOF'
{
  "id": "abort-test",
  "uri": "/api/*",
  "plugins": {
    "fault-injection": {
      "abort": {
        "http_status": 503,
        "body": "Service temporarily unavailable",
        "percentage": 50
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 3. Conditional Abort Based on Query Parameter

Only abort when `?name=jack`:

```bash
a6 route create -f - <<'EOF'
{
  "id": "conditional-abort",
  "uri": "/api/*",
  "plugins": {
    "fault-injection": {
      "abort": {
        "http_status": 403,
        "body": "Fault Injection!\n",
        "vars": [
          [["arg_name", "==", "jack"]]
        ]
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 4. Complex Conditional Logic (AND/OR)

Abort when `(name=jack AND age≥18) OR (has api-key header)`:

```bash
a6 route create -f - <<'EOF'
{
  "id": "complex-fault",
  "uri": "/api/*",
  "plugins": {
    "fault-injection": {
      "abort": {
        "http_status": 403,
        "body": "Fault Injection!\n",
        "vars": [
          [
            ["arg_name", "==", "jack"],
            ["arg_age", "!", "<", 18]
          ],
          [
            ["http_apikey", "==", "api-key"]
          ]
        ]
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 5. Custom Headers with Nginx Variables

```bash
a6 route create -f - <<'EOF'
{
  "id": "headers-fault",
  "uri": "/api/*",
  "plugins": {
    "fault-injection": {
      "abort": {
        "http_status": 200,
        "body": "{\"uri\": \"$uri\"}",
        "headers": {
          "X-Fault-Injected": "true",
          "X-Request-URI": "$uri"
        }
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 6. Canary Fault Testing

Only users with `X-Canary: true` header experience 10% fault rate:

```bash
a6 route create -f - <<'EOF'
{
  "id": "canary-fault",
  "uri": "/api/*",
  "plugins": {
    "fault-injection": {
      "abort": {
        "http_status": 500,
        "percentage": 10,
        "vars": [
          [["http_x_canary", "==", "true"]]
        ]
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 7. Combined Delay + Abort with Different Conditions

```bash
a6 route create -f - <<'EOF'
{
  "id": "combined-fault",
  "uri": "/api/*",
  "plugins": {
    "fault-injection": {
      "delay": {
        "duration": 2,
        "vars": [
          [["http_x_slow", "==", "true"]]
        ]
      },
      "abort": {
        "http_status": 503,
        "vars": [
          [["http_x_fail", "==", "true"]]
        ]
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

## Config Sync Example

```yaml
version: "1"
routes:
  - id: fault-injection-demo
    uri: /api/*
    plugins:
      fault-injection:
        delay:
          duration: 1
          percentage: 25
        abort:
          http_status: 503
          body: "Service unavailable"
          percentage: 5
    upstream_id: my-upstream
```

## Execution Behavior

1. **Delay evaluated first**: if vars match and percentage sampled → `sleep(duration)`
2. **Abort evaluated second**: if vars match and percentage sampled → return immediately
3. **Percentage sampling**: `math.random(1, 100) <= percentage`
4. **When abort fires**: subsequent plugins (auth, rate limiting) are **skipped**

## Plugin Priority Context

Priority 11000 means fault-injection runs **very early**:

- ✅ Tracing plugins (zipkin, skywalking) capture faults
- ❌ Rate limiting won't prevent faults
- ❌ Authentication won't block faults

To apply faults only to authenticated users, use `vars` to check auth-related
variables or headers.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Fault never triggers | `percentage: 0` or `vars` never match | Check vars expressions; set percentage > 0 |
| Fault always triggers | No percentage set (defaults to 100%) | Set `percentage` to desired value |
| Auth bypass via fault | Plugin runs before auth (priority 11000) | Use `vars` to restrict fault scope |
| Body not interpolated | Missing `$` prefix on variable | Use `$uri` not `uri` in body/headers |
| Abort + delay both fire | Delay runs first, then abort | This is expected behavior; delay always executes before abort check |
