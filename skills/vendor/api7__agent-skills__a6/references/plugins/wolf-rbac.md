---
title: "wolf-rbac plugin"
description: "Skill for configuring the Apache APISIX wolf-rbac plugin via the a6 CLI. Covers integration with the Wolf RBAC server for role-based access control, token management, login/user-info/change-password API endpoints, permission checking flow, and multi-application setup."
metadata:
  category: plugin
  plugin_name: wolf-rbac
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 consumer create
    - a6 consumer update
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-wolf-rbac/SKILL.md
---
# wolf-rbac plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `wolf-rbac` plugin provides Role-Based Access Control (RBAC) by integrating
with the [Wolf RBAC server](https://github.com/iGeeky/wolf). It enables
centralized authentication and fine-grained URL+method permission checking
across multiple applications without modifying backend services.

**Priority:** 2555 (authentication plugin, runs in `rewrite` phase).

## When to Use

- Centralized RBAC across multiple HTTP applications
- URL + HTTP method level permission control
- Unified user management for microservices
- Need login, user-info, and password-change API endpoints

## Prerequisites

1. **Wolf RBAC server** running (default `http://127.0.0.1:12180`)
2. In Wolf console, configure: Application → Users → Roles → Permissions → Resources
3. Install Wolf via Docker: `https://github.com/iGeeky/wolf/blob/master/quick-start-with-docker/README.md`

## Plugin Configuration Reference (Consumer)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `server` | string | No | `http://127.0.0.1:12180` | Wolf RBAC server URL |
| `appid` | string | No | `unset` | Application ID registered in Wolf console |
| `header_prefix` | string | No | `X-` | Prefix for injected headers (UserId, Username, Nickname) |

**Note:** Configure on the **Consumer**, not the Route. Route config is empty `{}`.

## Token Format

```
V1#<appid>#<wolf_jwt_token>
```

Example: `V1#restful#eyJhbGciOiJIUzI1NiIs...`

### Token Extraction Priority

1. Query parameter: `?rbac_token=V1%23app%23token` (URL-encoded)
2. Authorization header: `Authorization: V1#app#token`
3. Custom header: `x-rbac-token: V1#app#token`
4. Cookie: `x-rbac-token=V1#app#token`

## API Endpoints

The plugin registers three endpoints (must be exposed via `public-api` plugin):

### POST /apisix/plugin/wolf-rbac/login

Authenticate and obtain `rbac_token`.

**Request:**
```json
{
  "appid": "restful",
  "username": "test",
  "password": "user-password",
  "authType": 1
}
```

- `authType`: `1` = password (default), `2` = LDAP (Wolf v0.5.0+)

**Response (200):**
```json
{
  "rbac_token": "V1#restful#eyJhbGci...",
  "user_info": {"id": "749", "username": "test", "nickname": "test"}
}
```

### GET /apisix/plugin/wolf-rbac/user_info

Get authenticated user details. Requires valid `rbac_token`.

**Response (200):**
```json
{
  "user_info": {
    "id": 749,
    "username": "test",
    "nickname": "test",
    "permissions": {"USER_LIST": true},
    "roles": {}
  }
}
```

### PUT /apisix/plugin/wolf-rbac/change_pwd

Change password. Requires valid `rbac_token`.

**Request:**
```json
{"oldPassword": "old", "newPassword": "new"}
```

## Authorization Flow

```
1. Client sends request with rbac_token
2. APISIX parses token → extracts appid + wolf_token
3. Matches appid to Consumer configuration
4. Calls Wolf server: GET /wolf/rbac/access_check
   - appID, resName (URL), action (HTTP method), clientIP
5. Wolf checks user roles/permissions for the resource
6. Success → inject X-UserId, X-Username, X-Nickname headers
7. Failure → return 401 (invalid token) or 403 (no permission)
```

**Retry behavior:** Up to 3 retries for 5xx Wolf server errors, 100ms between retries.

## Step-by-Step Setup

### 1. Create Consumer

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "wolf_rbac",
  "plugins": {
    "wolf-rbac": {
      "server": "http://127.0.0.1:12180",
      "appid": "restful"
    }
  }
}
EOF
```

### 2. Create Protected Route

```bash
a6 route create -f - <<'EOF'
{
  "id": "protected-api",
  "uri": "/api/*",
  "plugins": {
    "wolf-rbac": {}
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 3. Expose Login Endpoint

```bash
a6 route create -f - <<'EOF'
{
  "id": "wolf-login",
  "uri": "/apisix/plugin/wolf-rbac/login",
  "plugins": {
    "public-api": {}
  }
}
EOF
```

### 4. Expose User Info Endpoint

```bash
a6 route create -f - <<'EOF'
{
  "id": "wolf-userinfo",
  "uri": "/apisix/plugin/wolf-rbac/user_info",
  "plugins": {
    "public-api": {}
  }
}
EOF
```

### 5. Expose Change Password Endpoint

```bash
a6 route create -f - <<'EOF'
{
  "id": "wolf-changepwd",
  "uri": "/apisix/plugin/wolf-rbac/change_pwd",
  "plugins": {
    "public-api": {}
  }
}
EOF
```

### 6. Test Login

```bash
curl -X POST http://127.0.0.1:9080/apisix/plugin/wolf-rbac/login \
  -H "Content-Type: application/json" \
  -d '{"appid":"restful","username":"test","password":"user-password"}'
```

### 7. Access Protected Resource

```bash
curl http://127.0.0.1:9080/api/users \
  -H "Authorization: V1#restful#<token_from_step_6>"
```

## Multi-Application Setup

```bash
# App 1 consumer
a6 consumer create -f - <<'EOF'
{
  "username": "wolf_app1",
  "plugins": {
    "wolf-rbac": {
      "server": "http://127.0.0.1:12180",
      "appid": "app1"
    }
  }
}
EOF

# App 2 consumer
a6 consumer create -f - <<'EOF'
{
  "username": "wolf_app2",
  "plugins": {
    "wolf-rbac": {
      "server": "http://127.0.0.1:12180",
      "appid": "app2"
    }
  }
}
EOF
```

Each `appid` in the token determines which Consumer (and which Wolf application)
is used for permission checking.

## Custom Header Prefix

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "wolf_custom",
  "plugins": {
    "wolf-rbac": {
      "server": "http://127.0.0.1:12180",
      "appid": "myapp",
      "header_prefix": "Wolf-"
    }
  }
}
EOF
```

Injected headers become: `Wolf-UserId`, `Wolf-Username`, `Wolf-Nickname`.

## Config Sync Example

```yaml
version: "1"
consumers:
  - username: wolf_rbac
    plugins:
      wolf-rbac:
        server: "http://127.0.0.1:12180"
        appid: restful

routes:
  - id: protected-api
    uri: /api/*
    plugins:
      wolf-rbac: {}
    upstream_id: api-backend

  - id: wolf-login
    uri: /apisix/plugin/wolf-rbac/login
    plugins:
      public-api: {}

  - id: wolf-userinfo
    uri: /apisix/plugin/wolf-rbac/user_info
    plugins:
      public-api: {}

  - id: wolf-changepwd
    uri: /apisix/plugin/wolf-rbac/change_pwd
    plugins:
      public-api: {}
```

## Injected Headers

After successful authentication, these headers are added to both request
(upstream) and response (client):

| Header | Example | Description |
|--------|---------|-------------|
| `{prefix}UserId` | `X-UserId: 749` | Wolf user ID |
| `{prefix}Username` | `X-Username: admin` | Wolf username |
| `{prefix}Nickname` | `X-Nickname: administrator` | URL-encoded nickname |

## Error Responses

| Status | Message | Cause |
|--------|---------|-------|
| 401 | Missing rbac token in request | No token in any supported location |
| 401 | invalid rbac token: parse failed | Token format not `V1#appid#jwt` |
| 401 | Invalid appid in rbac token | No Consumer with matching appid |
| 401 | ERR_TOKEN_INVALID | JWT expired or signature invalid |
| 403 | ERR_ACCESS_DENIED | User lacks permission for URL+method |
| 500 | request to wolf-server failed | Wolf server unreachable or error |

## Security Recommendations

- Use HTTPS for Wolf server URL in production
- Prefer `Authorization` header over query parameter (avoids logging tokens)
- Set `HttpOnly` and `Secure` flags when using cookies
- Combine with `limit-req` on login endpoint to prevent brute force
- Combine with `ip-restriction` for additional network-level security

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 400 "appid is missing" on login | Missing `appid` in login request body | Include `appid` field |
| 400 "appid not found" | No Consumer configured with that appid | Create Consumer with matching `appid` |
| 401 on every request | Token expired or not passed correctly | Re-login to get fresh token; check token location |
| 403 "ERR_ACCESS_DENIED" | User not authorized for URL+method in Wolf | Configure permissions in Wolf console |
| 500 "request to wolf-server failed" | Wolf server down or unreachable | Verify Wolf server URL and connectivity |
| Login endpoint returns 404 | Not exposed via `public-api` | Create route with `public-api` plugin for login URI |
