---
title: "graphql proxy recipe"
description: "Recipe skill for implementing GraphQL proxying patterns using the a6 CLI. Covers operation-based routing with built-in GraphQL variables, per-operation rate limiting, REST-to-GraphQL conversion with the degraphql plugin, and security patterns for GraphQL APIs."
metadata:
  category: recipe
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
    - a6 config diff
  source: https://github.com/api7/a6/blob/main/skills/a6-recipe-graphql-proxy/SKILL.md
---
# graphql proxy recipe

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

APISIX provides built-in GraphQL support through three variables that let you
route and apply policies based on GraphQL query content — without parsing
GraphQL yourself:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `graphql_name` | Operation name from the query | `"getUser"` |
| `graphql_operation` | Operation type | `"query"`, `"mutation"` |
| `graphql_root_fields` | Top-level fields requested | `["user", "orders"]` |

These variables are extracted automatically from POST requests with
`Content-Type: application/json` or `application/graphql`, and from GET
requests with a `query` parameter.

## When to Use

- Routing different GraphQL operations to different backends
- Applying rate limits per operation type (queries vs mutations)
- Restricting which operations specific consumers can execute
- Converting REST endpoints to GraphQL queries (degraphql)
- Adding security layers (auth, rate limiting) to a GraphQL API

## Approach A: Operation-Based Routing

Route GraphQL queries and mutations to different backends using the
`graphql_operation` variable.

### Route queries to read replicas, mutations to primary

```bash
# Queries → read replica
a6 route create -f - <<'EOF'
{
  "id": "graphql-queries",
  "uri": "/graphql",
  "vars": [["graphql_operation", "==", "query"]],
  "upstream": {
    "type": "roundrobin",
    "nodes": { "graphql-read-replica:4000": 1 }
  }
}
EOF

# Mutations → primary database
a6 route create -f - <<'EOF'
{
  "id": "graphql-mutations",
  "uri": "/graphql",
  "vars": [["graphql_operation", "==", "mutation"]],
  "upstream": {
    "type": "roundrobin",
    "nodes": { "graphql-primary:4000": 1 }
  }
}
EOF
```

### Route by operation name

```bash
# Route the expensive "analytics" query to a dedicated backend
a6 route create -f - <<'EOF'
{
  "id": "graphql-analytics",
  "uri": "/graphql",
  "vars": [["graphql_name", "==", "getAnalytics"]],
  "priority": 10,
  "upstream": {
    "type": "roundrobin",
    "nodes": { "analytics-backend:4000": 1 }
  }
}
EOF
```

The `priority` field ensures this route is matched before a generic `/graphql` route.

## Approach B: Per-Operation Rate Limiting

Apply different rate limits to queries vs mutations.

```bash
# Queries: 1000 req/min
a6 route create -f - <<'EOF'
{
  "id": "graphql-query-limited",
  "uri": "/graphql",
  "vars": [["graphql_operation", "==", "query"]],
  "plugins": {
    "key-auth": {},
    "limit-count": {
      "count": 1000,
      "time_window": 60,
      "key_type": "var",
      "key": "consumer_name",
      "rejected_code": 429
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": { "graphql-backend:4000": 1 }
  }
}
EOF

# Mutations: 100 req/min (more restrictive)
a6 route create -f - <<'EOF'
{
  "id": "graphql-mutation-limited",
  "uri": "/graphql",
  "vars": [["graphql_operation", "==", "mutation"]],
  "plugins": {
    "key-auth": {},
    "limit-count": {
      "count": 100,
      "time_window": 60,
      "key_type": "var",
      "key": "consumer_name",
      "rejected_code": 429,
      "rejected_msg": "Mutation rate limit exceeded"
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": { "graphql-backend:4000": 1 }
  }
}
EOF
```

## Approach C: Restrict Operations by Consumer

Use `consumer-restriction` to allow only specific consumers to execute
mutations.

```bash
a6 route create -f - <<'EOF'
{
  "id": "graphql-mutations-restricted",
  "uri": "/graphql",
  "vars": [["graphql_operation", "==", "mutation"]],
  "plugins": {
    "key-auth": {},
    "consumer-restriction": {
      "whitelist": ["admin-user", "service-account"],
      "rejected_code": 403,
      "rejected_msg": "Mutations not allowed for your account"
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": { "graphql-backend:4000": 1 }
  }
}
EOF
```

## Approach D: REST-to-GraphQL with degraphql

The `degraphql` plugin converts RESTful endpoints into GraphQL queries,
allowing REST clients to consume a GraphQL backend.

### 1. Enable degraphql on a route

```bash
a6 route create -f - <<'EOF'
{
  "id": "rest-to-graphql-users",
  "uri": "/users/:id",
  "methods": ["GET"],
  "plugins": {
    "degraphql": {
      "query": "query getUser($id: ID!) { user(id: $id) { id name email } }",
      "variables": ["id"]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": { "graphql-backend:4000": 1 }
  }
}
EOF
```

REST clients call `GET /users/123` and receive the GraphQL response
for `user(id: "123")`.

### 2. Static query (no variables)

```bash
a6 route create -f - <<'EOF'
{
  "id": "rest-to-graphql-stats",
  "uri": "/stats",
  "methods": ["GET"],
  "plugins": {
    "degraphql": {
      "query": "{ systemStats { cpu memory uptime } }"
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": { "graphql-backend:4000": 1 }
  }
}
EOF
```

## Declarative GraphQL Config

```yaml
# apisix-graphql.yaml
routes:
  - id: graphql-queries
    uri: "/graphql"
    vars: [["graphql_operation", "==", "query"]]
    plugins:
      key-auth: {}
      limit-count:
        count: 1000
        time_window: 60
        key_type: var
        key: consumer_name
    upstream:
      type: roundrobin
      nodes:
        "graphql-read-replica:4000": 1

  - id: graphql-mutations
    uri: "/graphql"
    vars: [["graphql_operation", "==", "mutation"]]
    plugins:
      key-auth: {}
      limit-count:
        count: 100
        time_window: 60
        key_type: var
        key: consumer_name
      consumer-restriction:
        whitelist: ["admin-user", "service-account"]
    upstream:
      type: roundrobin
      nodes:
        "graphql-primary:4000": 1
```

```bash
a6 config diff -f apisix-graphql.yaml
a6 config sync -f apisix-graphql.yaml
```

## Gotchas

- **Body size limit** — APISIX parses GraphQL from the request body. Default max
  body size is 1 MiB (configurable via `client_max_body_size` in APISIX config).
  Large queries may be rejected.
- **Single operation only** — APISIX extracts variables from the **first** operation
  in the request. Batched GraphQL queries (multiple operations) are not supported
  for routing purposes.
- **No WebSocket subscriptions** — GraphQL subscriptions over WebSocket are not
  supported by the built-in GraphQL parsing. You can still proxy WebSocket
  connections, but without operation-based routing.
- **POST content types** — GraphQL parsing works with `application/json` (standard)
  and `application/graphql` (query in body as text). Other content types are not
  parsed.
- **GET requests** — GraphQL variables are read from the `query` URL parameter
  (URL-encoded GraphQL query string).
- **`vars` matching** — the `vars` field on a route accepts an array of conditions.
  Each condition is `["variable", "operator", "value"]`. Multiple conditions are
  AND-ed together.
- **degraphql limitations** — the plugin sends a POST with `application/json` to
  the upstream, regardless of the original request method. The `variables` field
  maps URI path parameters to GraphQL variables by name.
- **Priority for overlapping routes** — when multiple routes match `/graphql` with
  different `vars`, use the `priority` field to control matching order. Higher
  priority = matched first.

## Verification

```bash
# Test query routing
curl -X POST http://localhost:9080/graphql \
  -H "Content-Type: application/json" \
  -H "apikey: my-key" \
  -d '{"query": "query getUser { user(id: 1) { name } }"}'

# Test mutation routing
curl -X POST http://localhost:9080/graphql \
  -H "Content-Type: application/json" \
  -H "apikey: my-key" \
  -d '{"query": "mutation createUser { createUser(name: \"test\") { id } }"}'

# Test rate limiting (should 429 after exceeding limit)
for i in $(seq 1 1001); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:9080/graphql \
    -H "Content-Type: application/json" \
    -H "apikey: my-key" \
    -d '{"query": "{ users { id } }"}'
done

# Test REST-to-GraphQL
curl http://localhost:9080/users/123
# Returns GraphQL response for user(id: "123")
```
