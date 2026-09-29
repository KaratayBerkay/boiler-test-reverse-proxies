---
title: "serverless plugin"
description: "Skill for configuring the Apache APISIX serverless-pre-function and serverless-post-function plugins via the a6 CLI. Covers inline Lua function execution in configurable request phases, function signature, closure patterns, available Lua APIs, and execution ordering."
metadata:
  category: plugin
  plugin_name: serverless-pre-function
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 global-rule create
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-serverless/SKILL.md
---
# serverless plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

APISIX provides two serverless plugins that execute inline Lua functions during
request processing:

- **`serverless-pre-function`** — runs at the **beginning** of the specified
  phase (priority 10000, executes early).
- **`serverless-post-function`** — runs at the **end** of the specified phase
  (priority −2000, executes late).

Both share identical configuration. Functions are defined as Lua strings in the
Admin API and compiled at load time.

## When to Use

- Inject custom request/response logic without writing a full plugin
- Quick prototyping of header injection, redirects, or logging
- Add lightweight pre-processing (rewrite) or post-processing (log)
- Dynamic routing decisions based on request attributes

## Plugin Configuration Reference

| Field | Type | Required | Default | Valid Values | Description |
|-------|------|----------|---------|--------------|-------------|
| `phase` | string | No | `"access"` | `rewrite`, `access`, `header_filter`, `body_filter`, `log`, `before_proxy` | Phase when functions execute |
| `functions` | array[string] | **Yes** | — | Lua function strings | Functions executed sequentially; each must return a function |

## Function Signature

Since APISIX v2.6+, functions receive two arguments:

```lua
return function(conf, ctx)
    -- conf: plugin configuration object
    -- ctx:  APISIX request context (shared across plugins)
    --
    -- Optional return:
    --   return code, body   -- exit immediately with HTTP status + body
    --   return              -- continue to next function / plugin
end
```

**Rules:**
- The string MUST return a function. Raw statements are rejected.
- Functions are cached via LRU cache; update the route to pick up changes.

## Phase Execution Order

```
1. rewrite         → modify request before routing
2. access          → authorization / authentication checks
3. before_proxy    → last chance before upstream call
4. header_filter   → modify response headers
5. body_filter     → modify response body (chunked via ngx.arg)
6. log             → logging after response sent (read-only)
```

### Phase Restrictions

| Phase | Can Read Request | Can Modify Request | Can Modify Response | Can Exit |
|-------|------------------|--------------------|---------------------|----------|
| rewrite | ✅ | ✅ | ❌ | ✅ |
| access | ✅ | ✅ | ❌ | ✅ |
| before_proxy | ✅ | ✅ | ❌ | ✅ |
| header_filter | ✅ | ❌ | ✅ (headers) | ❌ |
| body_filter | ✅ | ❌ | ✅ (body chunks) | ❌ |
| log | ✅ | ❌ | ❌ | ❌ |

## Step-by-Step Examples

### 1. Basic Logging

```bash
a6 route create -f - <<'EOF'
{
  "id": "serverless-log",
  "uri": "/api/*",
  "plugins": {
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": [
        "return function() ngx.log(ngx.WARN, 'incoming request: ', ngx.var.uri) end"
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

### 2. HTTP to HTTPS Redirect

```bash
a6 route create -f - <<'EOF'
{
  "id": "force-https",
  "uri": "/*",
  "plugins": {
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": [
        "return function() if ngx.var.scheme == 'http' then ngx.header['Location'] = 'https://' .. ngx.var.host .. ngx.var.request_uri; ngx.exit(301) end end"
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

### 3. Request Header Injection

```bash
a6 route create -f - <<'EOF'
{
  "id": "inject-headers",
  "uri": "/api/*",
  "plugins": {
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": [
        "return function(conf, ctx) ngx.req.set_header('X-Request-ID', ngx.var.request_id); ngx.req.set_header('X-Real-IP', ngx.var.remote_addr) end"
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

### 4. Modify Upstream URI

```bash
a6 route create -f - <<'EOF'
{
  "id": "rewrite-uri",
  "uri": "/legacy/*",
  "plugins": {
    "serverless-post-function": {
      "phase": "access",
      "functions": [
        "return function(conf, ctx) ctx.var.upstream_uri = '/v2' .. ngx.var.uri end"
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

### 5. Response Header Modification (header_filter phase)

```bash
a6 route create -f - <<'EOF'
{
  "id": "resp-headers",
  "uri": "/api/*",
  "plugins": {
    "serverless-post-function": {
      "phase": "header_filter",
      "functions": [
        "return function() ngx.header['X-Processed-By'] = 'APISIX'; ngx.header['X-Response-Time'] = ngx.now() - ngx.req.start_time() end"
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

### 6. Closure with Persistent State

```bash
a6 route create -f - <<'EOF'
{
  "id": "closure-counter",
  "uri": "/count",
  "plugins": {
    "serverless-pre-function": {
      "phase": "log",
      "functions": [
        "local count = 0; return function() count = count + 1; ngx.log(ngx.WARN, 'request count: ', count) end"
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

### 7. Multiple Sequential Functions

```bash
a6 route create -f - <<'EOF'
{
  "id": "multi-fn",
  "uri": "/api/*",
  "plugins": {
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": [
        "return function() ngx.log(ngx.WARN, 'step one') end",
        "return function() ngx.log(ngx.WARN, 'step two') end"
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

### 8. Custom Authentication Guard

```bash
a6 route create -f - <<'EOF'
{
  "id": "custom-auth",
  "uri": "/admin/*",
  "plugins": {
    "serverless-pre-function": {
      "phase": "access",
      "functions": [
        "return function() local token = ngx.var.http_authorization; if not token or token ~= 'Bearer secret123' then return 401, '{\"error\":\"unauthorized\"}' end end"
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

## Available Lua APIs

### Core ngx APIs

```lua
-- Request
ngx.var.uri, ngx.var.request_uri, ngx.var.scheme, ngx.var.host
ngx.var.remote_addr, ngx.var.request_method, ngx.var.request_id
ngx.req.get_headers(), ngx.req.get_uri_args(), ngx.req.get_method()
ngx.req.set_header(name, value), ngx.req.read_body(), ngx.req.get_body_data()

-- Response
ngx.header["Name"] = "value"
ngx.status = 200
ngx.say(data), ngx.print(data)
ngx.exit(status), ngx.redirect(uri, status)

-- Logging
ngx.log(ngx.ERR, msg), ngx.log(ngx.WARN, msg), ngx.log(ngx.INFO, msg)

-- Utilities
ngx.time(), ngx.now(), ngx.encode_base64(str), ngx.decode_base64(str)
```

### APISIX Context Variables

```lua
ctx.var.upstream_uri = "/new/path"   -- modify upstream request URI
ctx.curr_req_matched._path           -- matched route path
ctx.consumer_name                    -- authenticated consumer name
ctx.route_id                         -- current route ID
ctx.service_id                       -- current service ID
```

### Available Libraries

```lua
local json = require("cjson")
local core = require("apisix.core")
local http = require("resty.http")
local lrucache = require("resty.lrucache")
```

## Config Sync Example

```yaml
version: "1"
routes:
  - id: serverless-demo
    uri: /api/*
    plugins:
      serverless-pre-function:
        phase: rewrite
        functions:
          - "return function() ngx.req.set_header('X-Gateway', 'apisix') end"
      serverless-post-function:
        phase: log
        functions:
          - "return function() ngx.log(ngx.WARN, 'request completed') end"
    upstream_id: my-upstream
```

## Key Differences: Pre vs Post

| Feature | serverless-pre-function | serverless-post-function |
|---------|------------------------|--------------------------|
| Execution | Beginning of phase | End of phase |
| Priority | 10000 (high — runs early) | −2000 (low — runs late) |
| Typical Use | Pre-processing, auth guards | Post-processing, logging |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `only accept Lua function, the input code type is nil` | Function string doesn't return a function | Wrap code in `return function() ... end` |
| `failed to compile function` | Syntax error in Lua code | Test code in a Lua REPL first |
| Function changes not taking effect | LRU cache holds old compiled function | Update route to trigger recompilation |
| `ngx.say` not working in header_filter | Phase restriction — cannot write body in header_filter | Use header_filter only for `ngx.header` modifications |
| No output in log phase | Log phase is read-only | Use `ngx.log()` instead of `ngx.say()` |
| Blocking I/O causes timeout | Synchronous operations in request path | Use `ngx.timer.at()` for async work |
