---
title: "api versioning recipe"
description: "Recipe skill for implementing API versioning strategies using the a6 CLI. Covers URI path versioning with proxy-rewrite, header-based versioning with traffic-split, query parameter versioning, gradual version migration with weighted traffic splitting, and version deprecation with redirect."
metadata:
  category: recipe
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
    - a6 config diff
  source: https://github.com/api7/a6/blob/main/skills/a6-recipe-api-versioning/SKILL.md
---
# api versioning recipe

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

API versioning allows you to evolve your API without breaking existing clients.
APISIX supports multiple versioning strategies through routing rules, header
matching, and traffic splitting — all configurable via the a6 CLI.

Strategies covered:
1. **URI path versioning** — `/v1/users`, `/v2/users`
2. **Header-based versioning** — `Accept: application/vnd.api.v2+json`
3. **Query parameter versioning** — `?version=2`
4. **Gradual migration** — weighted traffic split between versions
5. **Version deprecation** — redirect old versions to new

## When to Use

- Introducing breaking changes to an existing API
- Running multiple API versions simultaneously
- Gradually migrating clients from v1 to v2
- Deprecating old API versions with user-friendly redirects

## Approach A: URI Path Versioning

The most common pattern. Each version has its own URI prefix, and
`proxy-rewrite` strips the version prefix before forwarding to the backend.

### 1. Create versioned upstreams

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "api-v1",
  "type": "roundrobin",
  "nodes": { "api-v1-backend:8080": 1 }
}
EOF

a6 upstream create -f - <<'EOF'
{
  "id": "api-v2",
  "type": "roundrobin",
  "nodes": { "api-v2-backend:8080": 1 }
}
EOF
```

### 2. Create versioned routes with URI rewriting

```bash
# v1: /v1/users/123 → /users/123 on api-v1 backend
a6 route create -f - <<'EOF'
{
  "id": "route-v1",
  "uri": "/v1/*",
  "upstream_id": "api-v1",
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/v1/(.*)", "/$1"]
    }
  }
}
EOF

# v2: /v2/users/123 → /users/123 on api-v2 backend
a6 route create -f - <<'EOF'
{
  "id": "route-v2",
  "uri": "/v2/*",
  "upstream_id": "api-v2",
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/v2/(.*)", "/$1"]
    }
  }
}
EOF
```

Clients call `/v1/users` or `/v2/users`, and the backend always sees `/users`.

## Approach B: Header-Based Versioning

Route based on the `Accept` header using `traffic-split` with `vars` matching.
A single URI serves multiple versions.

```bash
a6 route create -f - <<'EOF'
{
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [
            { "vars": [["http_accept", "~~", "application/vnd\\.api\\.v2\\+json"]] }
          ],
          "weighted_upstreams": [
            {
              "upstream": {
                "type": "roundrobin",
                "nodes": { "api-v2-backend:8080": 1 }
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
    "nodes": { "api-v1-backend:8080": 1 }
  }
}
EOF
```

- `Accept: application/vnd.api.v2+json` → v2 backend
- Any other `Accept` value → v1 backend (default upstream)
- `~~` is the regex match operator in APISIX vars expressions

## Approach C: Query Parameter Versioning

Route based on `?version=2` query parameter.

```bash
a6 route create -f - <<'EOF'
{
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [
            { "vars": [["arg_version", "==", "2"]] }
          ],
          "weighted_upstreams": [
            {
              "upstream": {
                "type": "roundrobin",
                "nodes": { "api-v2-backend:8080": 1 }
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
    "nodes": { "api-v1-backend:8080": 1 }
  }
}
EOF
```

- `/api/users?version=2` → v2 backend
- `/api/users` or `/api/users?version=1` → v1 backend

## Gradual Version Migration

Use weighted traffic splitting to gradually shift traffic from v1 to v2.

### Start: 90% v1, 10% v2

```bash
a6 route create -f - <<'EOF'
{
  "id": "api-migration",
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream": {
                "type": "roundrobin",
                "nodes": { "api-v2-backend:8080": 1 }
              },
              "weight": 1
            },
            { "weight": 9 }
          ]
        }
      ]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": { "api-v1-backend:8080": 1 }
  }
}
EOF
```

### Shift to 50/50

```bash
a6 route update api-migration -f - <<'EOF'
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream": {
                "type": "roundrobin",
                "nodes": { "api-v2-backend:8080": 1 }
              },
              "weight": 1
            },
            { "weight": 1 }
          ]
        }
      ]
    }
  }
}
EOF
```

### Complete: 100% v2

```bash
a6 route update api-migration -f - <<'EOF'
{
  "upstream": {
    "type": "roundrobin",
    "nodes": { "api-v2-backend:8080": 1 }
  },
  "plugins": {}
}
EOF
```

## Version Deprecation with Redirect

When sunsetting v1, redirect clients to v2 with a `301 Moved Permanently`.

```bash
a6 route update route-v1 -f - <<'EOF'
{
  "uri": "/v1/*",
  "plugins": {
    "redirect": {
      "regex_uri": ["^/v1/(.*)", "/v2/$1"],
      "ret_code": 301
    }
  }
}
EOF
```

Clients calling `/v1/users` receive:
```
HTTP/1.1 301 Moved Permanently
Location: /v2/users
```

## Declarative Versioning Config

```yaml
# apisix-versioning.yaml
upstreams:
  - id: api-v1
    type: roundrobin
    nodes:
      "api-v1-backend:8080": 1
  - id: api-v2
    type: roundrobin
    nodes:
      "api-v2-backend:8080": 1

routes:
  - id: route-v1
    uri: "/v1/*"
    upstream_id: api-v1
    plugins:
      proxy-rewrite:
        regex_uri: ["^/v1/(.*)", "/$1"]
  - id: route-v2
    uri: "/v2/*"
    upstream_id: api-v2
    plugins:
      proxy-rewrite:
        regex_uri: ["^/v2/(.*)", "/$1"]
```

```bash
a6 config diff -f apisix-versioning.yaml
a6 config sync -f apisix-versioning.yaml
```

## Gotchas

- **`regex_uri` is an array of two strings** — `["pattern", "replacement"]`, not
  an object. The pattern is a Lua regex (PCRE-compatible).
- **traffic-split weight semantics** — a `weighted_upstreams` entry without an
  `upstream` field means "use the route's default upstream". Weight `9` + weight
  `1` = 90%/10%.
- **`~~` operator** — regex match in vars expressions. Must double-escape backslashes
  in JSON: `"application/vnd\\\\.api\\\\.v2\\\\+json"`.
- **Order matters** — traffic-split rules are evaluated top-down. First matching
  rule wins.
- **URI rewrite happens before upstream** — `proxy-rewrite` changes the URI that
  the backend sees, not the URI used for route matching.
- **redirect plugin is terminal** — when redirect is active, the request never
  reaches an upstream. Remove the upstream_id to avoid confusion.

## Verification

```bash
# Test URI path versioning
curl http://localhost:9080/v1/users   # → v1 backend
curl http://localhost:9080/v2/users   # → v2 backend

# Test header-based versioning
curl -H "Accept: application/vnd.api.v2+json" http://localhost:9080/api/users  # → v2
curl http://localhost:9080/api/users  # → v1 (default)

# Test query parameter versioning
curl "http://localhost:9080/api/users?version=2"  # → v2
curl http://localhost:9080/api/users               # → v1

# Test redirect (deprecation)
curl -v http://localhost:9080/v1/users  # → 301 to /v2/users
```
