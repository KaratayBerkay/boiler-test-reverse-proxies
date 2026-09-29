---
title: "traffic-split plugin"
description: "Skill for configuring the Apache APISIX traffic-split plugin via the a6 CLI. Covers weighted traffic splitting between upstreams with conditional match rules. Includes canary release, blue-green deployment, A/B testing patterns, and common operational workflows."
metadata:
  category: plugin
  plugin_name: traffic-split
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 route get
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-traffic-split/SKILL.md
---
# traffic-split plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `traffic-split` plugin dynamically directs portions of traffic to
different upstream services based on custom rules (`match`) and weighted
distributions (`weighted_upstreams`). Use it for canary releases, blue-green
deployments, and A/B testing — all without modifying DNS or load balancers.

## When to Use

- Canary release: gradually shift traffic to a new version (10% → 50% → 100%)
- Blue-green deployment: switch traffic based on request headers or cookies
- A/B testing: split traffic by user attributes (headers, query params, cookies)
- Feature flags: route specific users to feature branches
- Multi-version API: run multiple backend versions simultaneously

## Plugin Configuration Reference (Route/Service)

### Top-level

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `rules` | array[object] | Yes | — | List of traffic splitting rules. Each rule has optional `match` and required `weighted_upstreams`. |

### rules[].match

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `match` | array[object] | No | `[]` | Conditions to activate this rule. Empty = unconditional (all traffic uses weights). |
| `match[].vars` | array[array] | No | — | Variable expressions: `["variable", "operator", "value"]`. Uses Nginx variables. Multiple vars in one object = AND. Multiple objects in match = OR. |

**Operators**: `==`, `~=`, `>`, `<`, `>=`, `<=`, `~~` (regex match), `!~~`, `in`, `has`, `!` — see [lua-resty-expr](https://github.com/api7/lua-resty-expr#operator-list).

**Common variables**: `arg_name` (query param), `http_header-name` (request header), `cookie_name` (cookie value).

### rules[].weighted_upstreams[]

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `upstream_id` | string/integer | No | — | ID of a pre-configured upstream object. Use this to get health checks, retries, etc. |
| `upstream` | object | No | — | Inline upstream configuration (see below). |
| `weight` | integer | No | `1` | Traffic weight for this upstream. |

**If only `weight` is set** (no `upstream` or `upstream_id`), traffic goes to the route's default upstream.

### Inline upstream object

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | No | `"roundrobin"` | Load balancing: `"roundrobin"` or `"chash"`. |
| `nodes` | object | Yes | — | Backend nodes as `{"host:port": weight}`. |
| `timeout` | object | No | `15` (seconds) | `{"connect": N, "send": N, "read": N}` |
| `pass_host` | string | No | `"pass"` | `"pass"` = client host, `"node"` = upstream node, `"rewrite"` = use `upstream_host`. |
| `upstream_host` | string | No | — | Custom Host header. Only works with `pass_host: "rewrite"`. |
| `name` | string | No | — | Human-readable name for the upstream. |

**Not supported in inline upstream**: `service_name`, `discovery_type`, `checks`, `retries`, `retry_timeout`, `scheme`. Use `upstream_id` for these features.

## Step-by-Step: Enable traffic-split on a Route

### 1. Canary release — 20% to new version

```bash
a6 route create -f - <<'EOF'
{
  "id": "canary-release",
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream": {
                "name": "new-version-v2",
                "type": "roundrobin",
                "nodes": {
                  "backend-v2:8080": 1
                }
              },
              "weight": 2
            },
            {
              "weight": 8
            }
          ]
        }
      ]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "backend-v1:8080": 1
    }
  }
}
EOF
```

Result: 20% traffic → `backend-v2`, 80% → `backend-v1` (route default).

### 2. Blue-green deployment — header-based switching

```bash
a6 route create -f - <<'EOF'
{
  "id": "blue-green",
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [
            {
              "vars": [
                ["http_x-canary", "==", "true"]
              ]
            }
          ],
          "weighted_upstreams": [
            {
              "upstream": {
                "name": "green-env",
                "type": "roundrobin",
                "nodes": {
                  "green-backend:8080": 1
                }
              },
              "weight": 1
            }
          ]
        }
      ]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "blue-backend:8080": 1
    }
  }
}
EOF
```

Result: Requests with header `x-canary: true` → green, all others → blue.

### 3. Increase canary to 50%

```bash
a6 route update canary-release -f - <<'EOF'
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream": {
                "name": "new-version-v2",
                "type": "roundrobin",
                "nodes": {
                  "backend-v2:8080": 1
                }
              },
              "weight": 5
            },
            {
              "weight": 5
            }
          ]
        }
      ]
    }
  }
}
EOF
```

## Common Patterns

### A/B testing by query parameter

```json
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [
            {
              "vars": [
                ["arg_variant", "==", "B"]
              ]
            }
          ],
          "weighted_upstreams": [
            {
              "upstream": {
                "name": "variant-B",
                "type": "roundrobin",
                "nodes": {"variant-b:8080": 1}
              }
            }
          ]
        }
      ]
    }
  }
}
```

Requests with `?variant=B` → variant B backend.

### Multi-rule routing (OR logic)

```json
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [{"vars": [["http_x-api-id", "==", "1"]]}],
          "weighted_upstreams": [
            {"upstream": {"type": "roundrobin", "nodes": {"svc-a:8080": 1}}}
          ]
        },
        {
          "match": [{"vars": [["http_x-api-id", "==", "2"]]}],
          "weighted_upstreams": [
            {"upstream": {"type": "roundrobin", "nodes": {"svc-b:8080": 1}}}
          ]
        }
      ]
    }
  }
}
```

### Using upstream_id for health checks

```json
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream_id": "canary-upstream",
              "weight": 2
            },
            {
              "weight": 8
            }
          ]
        }
      ]
    }
  }
}
```

Pre-create the upstream with `a6 upstream create` to configure health checks, retries, and other advanced settings.

### Multi-condition AND match

```json
{
  "match": [
    {
      "vars": [
        ["arg_name", "==", "jack"],
        ["http_user-id", ">", "23"],
        ["http_x-env", "~~", "^(staging|canary)$"]
      ]
    }
  ]
}
```

All three conditions must be true (AND logic within a single `vars` array).

## Match Logic Reference

| Structure | Logic |
|-----------|-------|
| Multiple entries in one `vars` array | **AND** — all must match |
| Multiple objects in `match` array | **OR** — any can match |
| Empty `match` or no `match` | **Unconditional** — always applies weights |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Traffic ratio inaccurate | Round-robin algorithm causes slight deviation | Expected behavior; ratios converge over many requests |
| Match rule not triggering | Variable name wrong or operator mismatch | Use `http_header-name` for headers, `arg_name` for query params |
| Health checks not working | Inline upstream doesn't support `checks` | Use `upstream_id` referencing a pre-created upstream with health checks |
| All traffic going to default | Match conditions never true | Debug with `a6 route get` and verify header/param names |
| Weight 0 not blocking traffic | Weight 0 means "never forward" to that upstream | Correct — set weight to 0 to exclude an upstream |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: canary-api
    uri: /api/*
    plugins:
      traffic-split:
        rules:
          - weighted_upstreams:
              - upstream_id: canary-upstream
                weight: 2
              - weight: 8
    upstream_id: stable-upstream
upstreams:
  - id: stable-upstream
    type: roundrobin
    nodes:
      "stable-backend:8080": 1
  - id: canary-upstream
    type: roundrobin
    nodes:
      "canary-backend:8080": 1
```
