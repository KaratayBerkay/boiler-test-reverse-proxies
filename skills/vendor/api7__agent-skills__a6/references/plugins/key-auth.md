---
title: "key-auth plugin"
description: "Skill for configuring the Apache APISIX key-auth plugin via the a6 CLI. Covers API key authentication setup on routes, consumer credential binding, key lookup from header/query/cookie, hide_credentials, anonymous consumer fallback, and common operational patterns."
metadata:
  category: plugin
  plugin_name: key-auth
  apisix_version: ">=3.11.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 consumer create
    - a6 consumer update
    - a6 credential create
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-key-auth/SKILL.md
---
# key-auth plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `key-auth` plugin authenticates requests using API keys. Clients include a
key in a header, query parameter, or cookie. APISIX looks up the key against
consumer credentials and, on match, forwards the request with consumer identity
headers. On failure it returns `401 Unauthorized`.

## When to Use

- Protect routes with simple API-key authentication
- Identify which consumer is calling an API
- Combine with rate-limiting for tiered access (authenticated vs anonymous)
- Hide credentials from upstream services

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `header` | string | No | `"apikey"` | Header name to extract API key from |
| `query` | string | No | `"apikey"` | Query parameter name (lower priority than header) |
| `hide_credentials` | boolean | No | `false` | Remove key from request before forwarding upstream |
| `anonymous_consumer` | string | No | — | Consumer username for unauthenticated requests |
| `realm` | string | No | `"key"` | Realm in `WWW-Authenticate` response header on 401 |

## Consumer Credential Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | **Yes** | Unique API key for the consumer. Auto-encrypted in etcd. |

## Key Lookup Priority

1. **Header** (default: `apikey`) — checked first
2. **Query parameter** (default: `apikey`) — checked if header absent
3. If both absent → `401 Unauthorized` with `"Missing API key in request"`

## Step-by-Step: Enable key-auth on a Route

### 1. Create a consumer

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "alice"
}
EOF
```

### 2. Add key-auth credential to the consumer

Save the credential as `credential.yaml`:

```yaml
id: cred-alice-key-auth
plugins:
  key-auth:
    key: alice-secret-key-001
```

```bash
a6 credential create --consumer alice -f credential.yaml
```

### 3. Create a route with key-auth enabled

```bash
a6 route create -f - <<'EOF'
{
  "id": "protected-api",
  "uri": "/api/*",
  "plugins": {
    "key-auth": {}
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

### 4. Verify authentication

```bash
# Should succeed (200)
curl -i http://127.0.0.1:9080/api/users -H "apikey: alice-secret-key-001"

# Should fail (401)
curl -i http://127.0.0.1:9080/api/users
```

## Common Patterns

### Custom header name

```json
{
  "plugins": {
    "key-auth": {
      "header": "X-API-Token"
    }
  }
}
```

Client sends: `curl -H "X-API-Token: alice-secret-key-001" ...`

### Query parameter authentication

```json
{
  "plugins": {
    "key-auth": {
      "query": "token"
    }
  }
}
```

Client sends: `curl "http://127.0.0.1:9080/api/users?token=alice-secret-key-001"`

### Hide credentials from upstream

```json
{
  "plugins": {
    "key-auth": {
      "hide_credentials": true
    }
  }
}
```

The `apikey` header or query param is stripped before reaching the backend.
Always enable this in production.

### Anonymous consumer with rate limiting

```bash
# Create anonymous consumer with strict limits
a6 consumer create -f - <<'EOF'
{
  "username": "anonymous",
  "plugins": {
    "limit-count": {
      "count": 10,
      "time_window": 60,
      "rejected_code": 429
    }
  }
}
EOF
```

```json
{
  "plugins": {
    "key-auth": {
      "anonymous_consumer": "anonymous"
    }
  }
}
```

Requests with valid keys → authenticated consumer. Requests without keys →
anonymous consumer with rate limits.

## Headers Added to Upstream

On successful authentication, APISIX adds:

| Header | Value |
|--------|-------|
| `X-Consumer-Username` | Consumer's username |
| `X-Credential-Identifier` | Credential ID |
| `X-Consumer-Custom-Id` | Consumer's `labels.custom_id` (if set) |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 "Missing API key in request"` | No key in header or query | Add `apikey` header or query param |
| `401 "Invalid API key in request"` | Key does not match any consumer | Verify the key value in consumer credentials |
| Key visible in upstream logs | `hide_credentials` is false | Set `hide_credentials: true` |
| Anonymous users not working | `anonymous_consumer` not set or consumer missing | Create the consumer and set the field |

## Config Sync Example

```yaml
version: "1"
consumers:
  - username: alice
routes:
  - id: protected-api
    uri: /api/*
    plugins:
      key-auth: {}
    upstream_id: my-upstream
upstreams:
  - id: my-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```

> **Note**: Consumer credentials must be created separately via the Admin API;
> `a6 config sync` manages the consumer resource but credentials are
> sub-resources.
