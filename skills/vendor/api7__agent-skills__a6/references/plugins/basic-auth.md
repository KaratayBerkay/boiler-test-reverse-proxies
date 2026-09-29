---
title: "basic-auth plugin"
description: "Skill for configuring the Apache APISIX basic-auth plugin via the a6 CLI. Covers HTTP Basic Authentication setup on routes, consumer credential binding with username/password, hide_credentials, anonymous consumer fallback, and common operational patterns."
metadata:
  category: plugin
  plugin_name: basic-auth
  apisix_version: ">=3.11.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 consumer create
    - a6 consumer update
    - a6 credential create
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-basic-auth/SKILL.md
---
# basic-auth plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `basic-auth` plugin authenticates requests using HTTP Basic Authentication
(RFC 7617). Consumers register a username and password. Clients send credentials
in the `Authorization: Basic <base64>` header. APISIX decodes and validates
against consumer credentials, then forwards the request with consumer identity
headers.

## When to Use

- Simple username/password authentication for APIs
- Quick protection for internal or development APIs
- Integration with tools that natively support HTTP Basic Auth (browsers, curl, Postman)

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `hide_credentials` | boolean | No | `false` | Remove `Authorization` header before forwarding upstream |
| `anonymous_consumer` | string | No | — | Consumer username for unauthenticated requests |
| `realm` | string | No | `"basic"` | Realm in `WWW-Authenticate` response header on 401 |

## Consumer Credential Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | **Yes** | Unique username for the consumer |
| `password` | string | **Yes** | Password for the consumer. Auto-encrypted in etcd. |

## Step-by-Step: Enable basic-auth on a Route

### 1. Create a consumer

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "alice"
}
EOF
```

### 2. Add basic-auth credential

Save the credential as `credential.yaml`, then create it:

```yaml
id: cred-alice-basic-auth
plugins:
  basic-auth:
    username: alice
    password: alice-password-123
```

```bash
a6 credential create --consumer alice -f credential.yaml
```

### 3. Create a route with basic-auth enabled

```bash
a6 route create -f - <<'EOF'
{
  "id": "basic-protected",
  "uri": "/api/*",
  "plugins": {
    "basic-auth": {}
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
# Using curl -u flag (sends Authorization: Basic header)
curl -i http://127.0.0.1:9080/api/users -u alice:alice-password-123

# Using explicit header (base64 of "alice:alice-password-123")
curl -i http://127.0.0.1:9080/api/users \
  -H "Authorization: Basic YWxpY2U6YWxpY2UtcGFzc3dvcmQtMTIz"

# Should fail (401)
curl -i http://127.0.0.1:9080/api/users
```

## Common Patterns

### Hide credentials from upstream

```json
{
  "plugins": {
    "basic-auth": {
      "hide_credentials": true
    }
  }
}
```

The `Authorization` header is stripped before reaching the backend. Always
enable this in production to prevent credential leakage.

### Anonymous consumer with rate limiting

```bash
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
    "basic-auth": {
      "anonymous_consumer": "anonymous"
    }
  }
}
```

Requests with valid credentials → authenticated consumer. Requests without
credentials → anonymous consumer with rate limits.

## Headers Added to Upstream

| Header | Value |
|--------|-------|
| `X-Consumer-Username` | Consumer's username |
| `X-Credential-Identifier` | Credential ID |
| `X-Consumer-Custom-Id` | Consumer's `labels.custom_id` (if set) |
| `Authorization` | Original header (unless `hide_credentials: true`) |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 Unauthorized` | Missing or wrong credentials | Check username/password; ensure base64 encoding is correct |
| Credentials visible in upstream logs | `hide_credentials` is false | Set `hide_credentials: true` |
| Browser not prompting login dialog | Missing `WWW-Authenticate` header | Verify plugin is enabled; check `realm` setting |
| Anonymous users not working | `anonymous_consumer` not set | Create consumer and set the field on the route plugin |

## Config Sync Example

```yaml
version: "1"
consumers:
  - username: alice
routes:
  - id: basic-protected
    uri: /api/*
    plugins:
      basic-auth: {}
    upstream_id: my-upstream
upstreams:
  - id: my-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```

> **Note**: Consumer credentials (username/password) must be created separately
> via the Admin API; `a6 config sync` manages the consumer resource but
> credentials are sub-resources.
