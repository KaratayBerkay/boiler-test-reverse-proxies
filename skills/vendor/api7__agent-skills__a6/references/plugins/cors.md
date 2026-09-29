---
title: "cors plugin"
description: "Skill for configuring the Apache APISIX cors plugin via the a6 CLI. Covers Cross-Origin Resource Sharing setup on routes, allow_origins, allow_methods, allow_headers, credentials handling, regex origin matching, preflight caching, and common operational patterns."
metadata:
  category: plugin
  plugin_name: cors
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-cors/SKILL.md
---
# cors plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `cors` plugin manages Cross-Origin Resource Sharing headers on APISIX
routes. It automatically handles preflight OPTIONS requests, sets
`Access-Control-*` response headers, and supports wildcard, exact, and
regex-based origin matching.

## When to Use

- Enable browser-based JavaScript access to your API from different origins
- Configure credentialed cross-origin requests (cookies, auth headers)
- Allow specific subdomains via regex patterns
- Control preflight cache duration for performance

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `allow_origins` | string | No | `"*"` | Allowed origins. Comma-separated `scheme://host:port`. Use `*` for all (no credentials). Use `**` to force-allow all (security risk). |
| `allow_methods` | string | No | `"*"` | Allowed HTTP methods. Comma-separated. Use `*` or `**` same as origins. |
| `allow_headers` | string | No | `"*"` | Allowed request headers. Comma-separated. When `**`, echoes the request's `Access-Control-Request-Headers`. |
| `expose_headers` | string | No | — | Response headers exposed to browser. Comma-separated. Not set by default. |
| `max_age` | integer | No | `5` | Preflight cache duration in seconds. `-1` disables caching. |
| `allow_credential` | boolean | No | `false` | Allow credentials (cookies, auth headers). If `true`, cannot use `*` for other fields. |
| `allow_origins_by_regex` | array[string] | No | — | Regex patterns to match origins dynamically |
| `allow_origins_by_metadata` | array[string] | No | — | Reference origins from plugin metadata |
| `timing_allow_origins` | string | No | — | Origins for Resource Timing API access |
| `timing_allow_origins_by_regex` | array[string] | No | — | Regex patterns for timing origins |

## Wildcard Rules

| Value | Meaning | With `allow_credential: true`? |
|-------|---------|-------------------------------|
| `*` | Allow all | ❌ Not allowed (CORS spec) |
| `**` | Force allow all | ✅ Allowed but **dangerous** (CSRF risk) |
| Specific | Exact match | ✅ Allowed |

## Step-by-Step: Enable CORS on a Route

### 1. Basic CORS (public API, no credentials)

```bash
a6 route create -f - <<'EOF'
{
  "id": "public-api",
  "uri": "/api/*",
  "plugins": {
    "cors": {}
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

Response headers on all requests:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
Access-Control-Max-Age: 5
```

### 2. CORS with credentials (specific origins)

```bash
a6 route create -f - <<'EOF'
{
  "id": "credentialed-api",
  "uri": "/api/*",
  "plugins": {
    "cors": {
      "allow_origins": "https://app.example.com,https://admin.example.com",
      "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
      "allow_headers": "Content-Type,Authorization,X-Custom-Header",
      "expose_headers": "X-Request-Id,X-Response-Time",
      "max_age": 3600,
      "allow_credential": true
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

## Common Patterns

### Regex-based origin matching (all subdomains)

```json
{
  "plugins": {
    "cors": {
      "allow_origins_by_regex": [
        ".*\\.example\\.com$"
      ],
      "allow_methods": "GET,POST,PUT,DELETE",
      "allow_credential": true,
      "max_age": 86400
    }
  }
}
```

Matches: `https://app.example.com`, `https://staging.example.com`
Does not match: `https://example.com`, `https://evil.com`

### Multiple domain groups with regex

```json
{
  "plugins": {
    "cors": {
      "allow_origins_by_regex": [
        ".*\\.example\\.com$",
        ".*\\.partner\\.net$",
        "^https://localhost:[0-9]+$"
      ],
      "allow_methods": "GET,POST",
      "allow_credential": true
    }
  }
}
```

### Long preflight cache

```json
{
  "plugins": {
    "cors": {
      "allow_origins": "https://app.example.com",
      "max_age": 86400,
      "allow_credential": true
    }
  }
}
```

Browser caches the preflight response for 24 hours, reducing OPTIONS requests.

### Expose custom response headers

```json
{
  "plugins": {
    "cors": {
      "allow_origins": "*",
      "expose_headers": "X-Request-Id,X-RateLimit-Limit,X-RateLimit-Remaining"
    }
  }
}
```

Without `expose_headers`, browsers only expose [CORS-safelisted headers](https://developer.mozilla.org/en-US/docs/Glossary/CORS-safelisted_response_header).

## Response Headers Set by Plugin

| Header | When Set |
|--------|----------|
| `Access-Control-Allow-Origin` | Always (matching origin or `*`) |
| `Access-Control-Allow-Methods` | Always |
| `Access-Control-Allow-Headers` | Always |
| `Access-Control-Expose-Headers` | Only if `expose_headers` configured |
| `Access-Control-Max-Age` | Always (preflight responses) |
| `Access-Control-Allow-Credentials` | Only if `allow_credential: true` |
| `Timing-Allow-Origin` | Only if `timing_allow_origins` configured |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Browser CORS error despite plugin | `allow_credential: true` with `allow_origins: "*"` | Use specific origins or `**` (risky) |
| Preflight fails but GET works | `allow_methods` missing the method | Add method to `allow_methods` |
| Custom header blocked | Header not in `allow_headers` | Add header to `allow_headers` |
| Can't read response header in JS | Header not in `expose_headers` | Add header to `expose_headers` |
| Regex not matching | Missing anchors or escaping | Use `$` anchor and escape dots: `\\.` |
| Cookies not sent cross-origin | `allow_credential` is false | Set `allow_credential: true` with specific origins |
| Origin format rejected | Missing scheme | Use `https://example.com` not `example.com` |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: cors-api
    uri: /api/*
    plugins:
      cors:
        allow_origins: "https://app.example.com"
        allow_methods: "GET,POST,PUT,DELETE,OPTIONS"
        allow_headers: "Content-Type,Authorization"
        expose_headers: "X-Request-Id"
        max_age: 3600
        allow_credential: true
    upstream_id: api-upstream
upstreams:
  - id: api-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```
