---
title: "response-rewrite plugin"
description: "Skill for configuring the Apache APISIX response-rewrite plugin via the a6 CLI. Covers rewriting response status codes, headers, and body before returning to clients. Includes conditional execution with vars, regex body filters, base64 body decoding, and common operational patterns."
metadata:
  category: plugin
  plugin_name: response-rewrite
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 route get
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-response-rewrite/SKILL.md
---
# response-rewrite plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `response-rewrite` plugin rewrites response attributes before APISIX
returns the response to the client. You can change the HTTP status code,
response headers, and response body — either unconditionally or based on
matching conditions. It runs in the `header_filter` and `body_filter`
phases, so it executes even if earlier plugins (like auth) call `ngx.exit`.

## When to Use

- Override the HTTP status code returned to clients
- Add, set, or remove response headers (e.g., security headers, CORS)
- Replace the entire response body (static content, error messages)
- Use regex filters to modify parts of the response body
- Apply response changes conditionally (e.g., only for certain status codes)
- Serve base64-decoded binary content (images, protobuf)

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `status_code` | integer | No | — | New HTTP status code (200–598). If unset, original status is used. |
| `body` | string | No | — | New response body. `Content-Length` is automatically reset. **Cannot be used with `filters`**. |
| `body_base64` | boolean | No | `false` | Decode `body` from base64 before sending. Only decodes plugin-configured body, not upstream response. |
| `headers` | object | No | — | Header manipulation with `set`, `add`, and `remove` fields. |
| `headers.set` | object | No | — | Set (overwrite) response headers. Key-value pairs. Supports Nginx variables. |
| `headers.add` | array[string] | No | — | Append response headers. Format: `["Name: value", ...]`. Adds even if header exists. |
| `headers.remove` | array[string] | No | — | Remove response headers. List of header names to strip. |
| `vars` | array[array] | No | — | Conditional matching using [lua-resty-expr](https://github.com/api7/lua-resty-expr) syntax. Plugin only executes when conditions match. |
| `filters` | array[object] | No | — | Regex filters to modify response body. **Cannot be used with `body`**. |
| `filters[].regex` | string | Yes | — | Regex pattern to match in response body. |
| `filters[].replace` | string | Yes | — | Replacement content. |
| `filters[].scope` | string | No | `"once"` | `"once"` = first match only. `"global"` = all matches. |
| `filters[].options` | string | No | `"jo"` | Regex options. See [ngx.re.match](https://github.com/openresty/lua-nginx-module#ngxrematch). |

**Mutual exclusion**: `body` and `filters` cannot be used together.

## Step-by-Step: Enable response-rewrite on a Route

### 1. Add security response headers

```bash
a6 route create -f - <<'EOF'
{
  "id": "security-headers",
  "uri": "/api/*",
  "plugins": {
    "response-rewrite": {
      "headers": {
        "set": {
          "X-Content-Type-Options": "nosniff",
          "X-Frame-Options": "DENY",
          "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        },
        "remove": ["Server", "X-Powered-By"]
      }
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

### 2. Custom error response body

```bash
a6 route create -f - <<'EOF'
{
  "id": "custom-error",
  "uri": "/maintenance/*",
  "plugins": {
    "response-rewrite": {
      "status_code": 503,
      "body": "{\"error\": \"Service under maintenance\", \"retry_after\": 300}",
      "headers": {
        "set": {
          "Content-Type": "application/json",
          "Retry-After": "300"
        }
      }
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

### 3. Conditional rewrite (only for 200 responses)

```bash
a6 route create -f - <<'EOF'
{
  "id": "conditional-rewrite",
  "uri": "/api/*",
  "plugins": {
    "response-rewrite": {
      "headers": {
        "set": {
          "Cache-Control": "public, max-age=3600"
        }
      },
      "vars": [["status", "==", 200]]
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

### Regex body filter (replace text globally)

Replace internal hostnames in response body with public URLs:

```json
{
  "plugins": {
    "response-rewrite": {
      "filters": [
        {
          "regex": "http://internal\\.service\\.local",
          "scope": "global",
          "replace": "https://api.example.com"
        }
      ]
    }
  }
}
```

### Multiple regex filters

```json
{
  "plugins": {
    "response-rewrite": {
      "filters": [
        {
          "regex": "X-Amzn-Trace-Id",
          "scope": "global",
          "replace": "X-Trace-Id"
        },
        {
          "regex": "\"debug\":\\s*true",
          "scope": "global",
          "replace": "\"debug\": false"
        }
      ]
    }
  }
}
```

### Base64 body (serve binary content)

```json
{
  "plugins": {
    "response-rewrite": {
      "status_code": 200,
      "body": "SGVsbG8gV29ybGQ=",
      "body_base64": true,
      "headers": {
        "set": {
          "Content-Type": "text/plain"
        }
      }
    }
  }
}
```

Returns decoded body: `Hello World`

### Add dynamic server info headers

```json
{
  "plugins": {
    "response-rewrite": {
      "headers": {
        "set": {
          "X-Served-By": "$balancer_ip:$balancer_port",
          "X-Request-Id": "$request_id"
        }
      }
    }
  }
}
```

### Conditional: only rewrite 5xx errors

```json
{
  "plugins": {
    "response-rewrite": {
      "body": "{\"error\": \"internal server error\", \"code\": 500}",
      "headers": {
        "set": {
          "Content-Type": "application/json"
        }
      },
      "vars": [["status", ">=", 500]]
    }
  }
}
```

## Important Notes

- **Execution phase**: Runs in `header_filter` and `body_filter` phases, which means it executes **even if earlier plugins** (auth, rate-limiting) reject the request via `ngx.exit`.
- **Header manipulation order**: `add` → `remove` → `set` (same as proxy-rewrite).
- **Body and filters are mutually exclusive**: Cannot set both `body` and `filters`.
- **base64 decoding**: Only applies to the plugin-configured `body` field, NOT to the upstream response body.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Body not changed | `body` and `filters` both set | Use only one: `body` for full replacement, `filters` for partial |
| Status code unchanged | `status_code` not in valid range | Must be 200–598 |
| Regex filter not matching | Pattern syntax or escaping issue | Test regex; use `"jo"` options for UTF-8 support |
| Headers still present after remove | Header name case mismatch | Header names are case-insensitive; check exact spelling |
| Vars condition not working | Incorrect operator or type | Use `lua-resty-expr` syntax: `["status", "==", 200]` (integer, not string) |
| Rewrite runs on auth failures | Expected behavior | Plugin runs in filter phases regardless of earlier `ngx.exit` calls |
| Content-Length mismatch | Manual Content-Length header | Don't set Content-Length manually — plugin resets it automatically |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: response-transform
    uri: /api/*
    plugins:
      response-rewrite:
        headers:
          set:
            X-Content-Type-Options: "nosniff"
            X-Frame-Options: "DENY"
          remove:
            - Server
            - X-Powered-By
        vars:
          - ["status", "==", 200]
    upstream_id: api-backend
upstreams:
  - id: api-backend
    type: roundrobin
    nodes:
      "backend:8080": 1
```
