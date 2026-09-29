---
title: "consumer-restriction plugin"
description: "Skill for configuring the Apache APISIX consumer-restriction plugin via the a6 CLI. Covers restricting access by consumer name, consumer group ID, service ID, or route ID using whitelist/blacklist modes and per-consumer HTTP method restrictions."
metadata:
  category: plugin
  plugin_name: consumer-restriction
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 consumer create
    - a6 consumer update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-consumer-restriction/SKILL.md
---
# consumer-restriction plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `consumer-restriction` plugin restricts access to routes or services based
on the authenticated consumer's identity. It supports four restriction types
and three matching modes (blacklist, whitelist, method-level).

**Priority:** 2400 (runs in the `access` phase after authentication plugins).

**Prerequisite:** MUST be paired with an authentication plugin (`key-auth`,
`basic-auth`, `jwt-auth`, `hmac-auth`, `wolf-rbac`, etc.) to identify the
consumer.

## When to Use

- Restrict specific routes to certain consumers or consumer groups
- Implement tiered access (free vs premium consumers)
- Control which HTTP methods each consumer can use
- Restrict consumers to specific services or routes

## Plugin Configuration Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | No | `consumer_name` | Restriction type: `consumer_name`, `consumer_group_id`, `service_id`, `route_id` |
| `whitelist` | array[string] | One of three\* | — | Allowed identifiers |
| `blacklist` | array[string] | One of three\* | — | Blocked identifiers |
| `allowed_by_methods` | array[object] | One of three\* | — | Per-consumer HTTP method restrictions |
| `allowed_by_methods[].user` | string | No | — | Consumer username |
| `allowed_by_methods[].methods` | array[string] | No | — | Allowed HTTP methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, CONNECT, TRACE, PURGE |
| `rejected_code` | integer | No | `403` | HTTP status code for rejected requests (≥ 200) |
| `rejected_msg` | string | No | `"The {type} is forbidden."` | Custom rejection message |

\* At least one of `whitelist`, `blacklist`, or `allowed_by_methods` is required.

## Evaluation Priority

```
blacklist (highest) > whitelist > allowed_by_methods (lowest)
```

1. **Blacklist**: if consumer matches → **403 immediately**
2. **Whitelist**: if consumer NOT in whitelist → blocked (unless allowed_by_methods permits)
3. **allowed_by_methods**: if consumer's method not in allowed list → blocked

## Restriction Type Placement

| Type | Configure On | Description |
|------|-------------|-------------|
| `consumer_name` | Route/Service | Restrict which consumers can access this route |
| `consumer_group_id` | Route/Service | Restrict which consumer groups can access this route |
| `service_id` | **Consumer** | Restrict which services this consumer can access |
| `route_id` | **Consumer** | Restrict which routes this consumer can access |

## Step-by-Step Examples

### 1. Whitelist by Consumer Name

Only allow `jack1` to access the route:

```bash
# Create consumers with auth
a6 consumer create -f - <<'EOF'
{
  "username": "jack1",
  "plugins": {
    "key-auth": {"key": "jack1-key"}
  }
}
EOF

a6 consumer create -f - <<'EOF'
{
  "username": "jack2",
  "plugins": {
    "key-auth": {"key": "jack2-key"}
  }
}
EOF

# Create route with restriction
a6 route create -f - <<'EOF'
{
  "id": "restricted",
  "uri": "/api/*",
  "plugins": {
    "key-auth": {},
    "consumer-restriction": {
      "whitelist": ["jack1"]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

- `curl -H 'apikey: jack1-key' /api/data` → **200 OK**
- `curl -H 'apikey: jack2-key' /api/data` → **403** `{"message":"The consumer_name is forbidden."}`

### 2. Blacklist by Consumer Name

Block `bad-actor` while allowing everyone else:

```bash
a6 route create -f - <<'EOF'
{
  "id": "blacklisted",
  "uri": "/api/*",
  "plugins": {
    "key-auth": {},
    "consumer-restriction": {
      "blacklist": ["bad-actor"],
      "rejected_code": 403,
      "rejected_msg": "Access denied"
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 3. Restrict by Consumer Group

Only allow consumers in `enterprise` group:

```bash
# Create consumer group
a6 consumer-group create -f - <<'EOF'
{
  "id": "enterprise",
  "plugins": {
    "limit-count": {
      "count": 10000,
      "time_window": 60,
      "group": "enterprise"
    }
  }
}
EOF

# Create consumer in the group
a6 consumer create -f - <<'EOF'
{
  "username": "acme-corp",
  "plugins": {
    "key-auth": {"key": "acme-key"}
  },
  "group_id": "enterprise"
}
EOF

# Route restricted to enterprise group
a6 route create -f - <<'EOF'
{
  "id": "enterprise-only",
  "uri": "/premium/*",
  "plugins": {
    "key-auth": {},
    "consumer-restriction": {
      "type": "consumer_group_id",
      "whitelist": ["enterprise"]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 4. Method-Level Restrictions

Allow `jack1` only POST requests:

```bash
a6 route create -f - <<'EOF'
{
  "id": "method-restricted",
  "uri": "/api/*",
  "plugins": {
    "key-auth": {},
    "consumer-restriction": {
      "allowed_by_methods": [
        {
          "user": "jack1",
          "methods": ["POST"]
        },
        {
          "user": "admin",
          "methods": ["GET", "POST", "PUT", "DELETE"]
        }
      ]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 5. Restrict Consumer to Specific Services (Consumer-Level Config)

Consumer `api-user` can only access service 1:

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "api-user",
  "plugins": {
    "key-auth": {"key": "api-user-key"},
    "consumer-restriction": {
      "type": "service_id",
      "whitelist": ["1"],
      "rejected_code": 403
    }
  }
}
EOF
```

### 6. Restrict Consumer to Specific Routes (Consumer-Level Config)

Consumer `limited-user` can only access route 1:

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "limited-user",
  "plugins": {
    "key-auth": {"key": "limited-key"},
    "consumer-restriction": {
      "type": "route_id",
      "whitelist": ["1"],
      "rejected_code": 401
    }
  }
}
EOF
```

## Config Sync Example

```yaml
version: "1"
consumers:
  - username: admin
    plugins:
      key-auth:
        key: admin-key
  - username: readonly
    plugins:
      key-auth:
        key: readonly-key

routes:
  - id: admin-api
    uri: /admin/*
    plugins:
      key-auth: {}
      consumer-restriction:
        whitelist:
          - admin
        rejected_code: 403
        rejected_msg: "Admin access required"
    upstream_id: admin-backend

  - id: public-api
    uri: /api/*
    plugins:
      key-auth: {}
      consumer-restriction:
        allowed_by_methods:
          - user: readonly
            methods: ["GET"]
          - user: admin
            methods: ["GET", "POST", "PUT", "DELETE"]
    upstream_id: api-backend
```

## Common Patterns

### Tiered Access Control

```json
{
  "plugins": {
    "key-auth": {},
    "consumer-restriction": {
      "type": "consumer_group_id",
      "whitelist": ["enterprise", "pro"],
      "rejected_code": 402,
      "rejected_msg": "Upgrade required for this endpoint"
    }
  }
}
```

### Hide Endpoint Existence

```json
{
  "plugins": {
    "key-auth": {},
    "consumer-restriction": {
      "whitelist": ["admin"],
      "rejected_code": 404,
      "rejected_msg": "Resource not found"
    }
  }
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 "please check the consumer_name" | No auth plugin or consumer not authenticated | Add `key-auth`/`jwt-auth` to the route |
| 403 but consumer should be allowed | Consumer not in whitelist or is in blacklist | Verify consumer username matches whitelist entry exactly |
| `allowed_by_methods` ignored | Whitelist also set (higher priority) | Remove whitelist or use only one mode |
| `service_id` restriction not working | Configured on route instead of consumer | Move `consumer-restriction` config to consumer plugins |
| `route_id` restriction not working | Configured on route instead of consumer | Move `consumer-restriction` config to consumer plugins |
