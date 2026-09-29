---
title: "proxy-rewrite plugin"
description: "Skill for configuring the Apache APISIX proxy-rewrite plugin via the a6 CLI. Covers rewriting request URI, host, method, headers, and scheme before forwarding to upstream. Includes regex URI rewriting, header manipulation, and common operational patterns."
metadata:
  category: plugin
  plugin_name: proxy-rewrite
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 route get
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-proxy-rewrite/SKILL.md
---
# proxy-rewrite plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `proxy-rewrite` plugin rewrites request attributes before APISIX forwards
the request to the upstream. You can change the URI path, host header, HTTP
method, scheme, and add/set/remove request headers — all without modifying
your backend service.

## When to Use

- Rewrite the URI path before forwarding (e.g., strip a prefix like `/api/v1`)
- Rewrite the Host header for backend routing
- Change the HTTP method (e.g., convert POST to PUT)
- Add, set, or remove request headers before proxying
- Use regex-based URI rewriting for complex path transformations
- Switch the scheme from HTTP to HTTPS (or vice versa) when proxying

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `uri` | string | No | — | New upstream request URI. Supports Nginx variables (e.g., `$uri`, `$arg_name`). |
| `method` | string | No | — | Override the HTTP method. Must be uppercase: `GET`, `POST`, `PUT`, `DELETE`, etc. |
| `host` | string | No | — | New Host header value sent to upstream. |
| `scheme` | string | No | — | New scheme for upstream request: `http` or `https`. |
| `headers` | object | No | — | Header manipulation object with `set`, `add`, and `remove` fields. |
| `headers.set` | object | No | — | Set (overwrite) headers. Key-value pairs. Supports Nginx variables. |
| `headers.add` | object | No | — | Append headers. Key-value pairs. Adds even if the header already exists. |
| `headers.remove` | array[string] | No | — | Remove headers. List of header names to strip. |
| `regex_uri` | array[string] | No | — | Array of two strings: `[pattern, replacement]`. Uses PCRE regex to rewrite the URI. |
| `use_real_request_uri_unsafe` | boolean | No | `false` | Use the original unescaped URI. **Security risk** — only enable if you understand the implications. |

**Priority**: If both `uri` and `regex_uri` are set, `uri` takes precedence.

## Step-by-Step: Enable proxy-rewrite on a Route

### 1. Simple URI rewrite (strip prefix)

Strip `/api/v1` prefix so `/api/v1/users` becomes `/users`:

```bash
a6 route create -f - <<'EOF'
{
  "id": "strip-prefix",
  "uri": "/api/v1/*",
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/api/v1/(.*)", "/$1"]
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

### 2. Rewrite host header

Route to a different virtual host on the backend:

```bash
a6 route create -f - <<'EOF'
{
  "id": "rewrite-host",
  "uri": "/legacy/*",
  "plugins": {
    "proxy-rewrite": {
      "host": "legacy.internal.svc"
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

### 3. Add and remove headers

```bash
a6 route create -f - <<'EOF'
{
  "id": "header-manip",
  "uri": "/api/*",
  "plugins": {
    "proxy-rewrite": {
      "headers": {
        "set": {
          "X-Forwarded-Proto": "https",
          "X-Real-IP": "$remote_addr"
        },
        "add": {
          "X-Request-Start": "$msec"
        },
        "remove": ["X-Internal-Debug", "X-Secret-Token"]
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

## Common Patterns

### Regex URI rewrite with capture groups

Rewrite `/products/123/reviews` to `/api/products?id=123&section=reviews`:

```json
{
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/products/(\\d+)/(.*)$", "/api/products?id=$1&section=$2"]
    }
  }
}
```

### Change HTTP method

Convert GET to POST for a legacy backend:

```json
{
  "plugins": {
    "proxy-rewrite": {
      "method": "POST"
    }
  }
}
```

### Static URI replacement

Replace the entire URI path:

```json
{
  "plugins": {
    "proxy-rewrite": {
      "uri": "/internal/health"
    }
  }
}
```

### Use Nginx variables in URI

```json
{
  "plugins": {
    "proxy-rewrite": {
      "uri": "/api/$arg_version/resource"
    }
  }
}
```

### Combine URI rewrite with header manipulation

```json
{
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/v2/(.*)", "/v3/$1"],
      "headers": {
        "set": {
          "X-API-Version": "v3"
        }
      }
    }
  }
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| URI not rewritten | Both `uri` and `regex_uri` set — `uri` wins | Remove `uri` if you need regex |
| Regex not matching | Bad pattern or unescaped characters | Test regex with PCRE syntax; escape backslashes in JSON: `\\d+` |
| Nginx variable not resolved | Variable name typo or not available | Check [Nginx variable list](http://nginx.org/en/docs/varindex.html) |
| 404 after rewrite | Rewritten URI doesn't match upstream paths | Verify the rewritten path exists on the backend |
| Host header unchanged | `host` field not set or overridden by upstream | Explicitly set `host` in proxy-rewrite config |
| Header appears twice | Used `set` vs `add` confusion | Use `set` to overwrite, `add` to append |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: api-rewrite
    uri: /api/v1/*
    plugins:
      proxy-rewrite:
        regex_uri:
          - "^/api/v1/(.*)"
          - "/$1"
        headers:
          set:
            X-Forwarded-Prefix: "/api/v1"
          remove:
            - X-Debug
    upstream_id: backend
upstreams:
  - id: backend
    type: roundrobin
    nodes:
      "backend:8080": 1
```
