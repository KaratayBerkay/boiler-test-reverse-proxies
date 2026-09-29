---
title: "ext-plugin plugin"
description: "Skill for configuring the Apache APISIX external plugin system (ext-plugin-pre-req, ext-plugin-post-req, ext-plugin-post-resp) via the a6 CLI. Covers Plugin Runner architecture, configuration for Go/Java/Python runners, RPC protocol, graceful degradation, and performance considerations."
metadata:
  category: plugin
  plugin_name: ext-plugin-pre-req
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-ext-plugin/SKILL.md
---
# ext-plugin plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The APISIX external plugin system lets you run plugins written in **Go, Java,
Python, or JavaScript** via a Plugin Runner process. APISIX communicates with
the runner over a Unix socket using FlatBuffers serialization.

Three plugins control when external plugins execute:

| Plugin | Phase | Priority | Description |
|--------|-------|----------|-------------|
| `ext-plugin-pre-req` | rewrite | 12000 | Before built-in Lua plugins |
| `ext-plugin-post-req` | access | −3000 | After Lua plugins, before upstream |
| `ext-plugin-post-resp` | before_proxy | −4000 | After upstream response received |

## When to Use

- Implement custom logic in Go, Java, or Python instead of Lua
- Reuse existing business logic from non-Lua codebases
- Apply pre-processing (auth, validation) or post-processing (response transform)
- Teams that prefer statically-typed languages over Lua

## Plugin Configuration Reference

All three plugins share the same schema:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `conf` | array | No | — | List of external plugins to execute |
| `conf[].name` | string | **Yes** | — | Plugin identifier (1–128 chars) |
| `conf[].value` | string | **Yes** | — | JSON string configuration passed to the plugin |
| `allow_degradation` | boolean | No | `false` | When `true`, requests continue if runner is unavailable |

## Plugin Runner Architecture

```
┌──────────┐    Unix Socket    ┌───────────────┐
│  APISIX  │ ◄──────────────► │ Plugin Runner  │
│  (Nginx) │   FlatBuffers    │ (Go/Java/Py)   │
└──────────┘                   └───────────────┘
```

1. APISIX starts the runner as a **subprocess** (managed lifecycle)
2. On `ext-plugin-*` trigger, APISIX sends an RPC over Unix socket
3. Runner executes external plugins and returns the result
4. APISIX applies modifications (headers, body, status) to the request/response

### RPC Protocol

- **PrepareConf**: Syncs plugin configuration → returns a conf token (cached)
- **HTTPReqCall**: Per-request execution with serialized HTTP data + conf token
- **ExtraInfo**: Runner can request additional data (variables, body, response)

## Supported Plugin Runners

| Language | Repository | Status |
|----------|------------|--------|
| Go | `apache/apisix-go-plugin-runner` | GA |
| Java | `apache/apisix-java-plugin-runner` | GA |
| Python | `apache/apisix-python-plugin-runner` | Experimental |
| JavaScript | `zenozeng/apisix-javascript-plugin-runner` | Community |

## APISIX Configuration (config.yaml)

### Production Setup

APISIX manages the runner as a subprocess:

```yaml
ext-plugin:
  cmd: ["/path/to/runner-executable", "run"]
```

### Runner-Specific Commands

```yaml
# Go runner
ext-plugin:
  cmd: ["/opt/apisix-go-runner", "run"]

# Java runner
ext-plugin:
  cmd: ["java", "-jar", "-Xmx1g", "-Xms1g", "/opt/apisix-runner.jar"]

# Python runner
ext-plugin:
  cmd: ["python3", "/opt/apisix-python-runner/apisix/main.py", "start"]
```

### Development Setup (Standalone Runner)

For local development, run the runner separately:

```yaml
# APISIX config.yaml — do NOT set cmd
ext-plugin:
  path_for_test: "/tmp/runner.sock"
```

```bash
# Start runner manually
APISIX_LISTEN_ADDRESS=unix:/tmp/runner.sock ./runner run
```

### Environment Variables

Pass environment variables to the runner:

```yaml
nginx_config:
  envs:
    - MY_ENV_VAR
    - DATABASE_URL
```

## Step-by-Step Examples

### 1. Single External Plugin

```bash
a6 route create -f - <<'EOF'
{
  "id": "ext-auth",
  "uri": "/api/*",
  "plugins": {
    "ext-plugin-pre-req": {
      "conf": [
        {"name": "AuthFilter", "value": "{\"token_required\":true}"}
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

### 2. Multiple External Plugins with Degradation

```bash
a6 route create -f - <<'EOF'
{
  "id": "ext-chain",
  "uri": "/api/*",
  "plugins": {
    "ext-plugin-pre-req": {
      "conf": [
        {"name": "AuthFilter", "value": "{\"token_required\":true}"},
        {"name": "RateLimiter", "value": "{\"requests_per_second\":100}"}
      ],
      "allow_degradation": true
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

### 3. All Three Plugin Types (Full Request Lifecycle)

```bash
a6 route create -f - <<'EOF'
{
  "id": "full-ext",
  "uri": "/api/*",
  "plugins": {
    "ext-plugin-pre-req": {
      "conf": [{"name": "auth-check", "value": "{}"}]
    },
    "ext-plugin-post-req": {
      "conf": [{"name": "request-transform", "value": "{}"}]
    },
    "ext-plugin-post-resp": {
      "conf": [{"name": "response-logger", "value": "{}"}]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {"backend:8080": 1}
  }
}
EOF
```

**Execution order:** pre-req → (Lua plugins) → post-req → (upstream) → post-resp

## Config Sync Example

```yaml
version: "1"
routes:
  - id: ext-plugin-demo
    uri: /api/*
    plugins:
      ext-plugin-pre-req:
        conf:
          - name: AuthFilter
            value: '{"token_required":true}'
        allow_degradation: true
    upstream_id: my-upstream
```

## Compatibility Matrix

| Feature | ext-plugin-pre-req | ext-plugin-post-req | ext-plugin-post-resp |
|---------|-------------------|---------------------|---------------------|
| Phase | rewrite | access | before_proxy |
| Runs | Before Lua plugins | After Lua plugins | After upstream response |
| proxy-mirror | ✅ | ✅ | ❌ |
| proxy-cache | ✅ | ✅ | ❌ |
| proxy-control | ✅ | ✅ | ❌ |
| mTLS to upstream | ✅ | ✅ | ❌ |

**`ext-plugin-post-resp` limitation:** Uses `lua-resty-http` internally,
which makes it incompatible with `proxy-mirror`, `proxy-cache`,
`proxy-control`, and mTLS to upstream.

## Performance Considerations

- **Unix socket + FlatBuffers**: Low-latency IPC, no TCP overhead
- **Conf token caching**: PrepareConf called once per config change, not per request
- **Process management**: APISIX sends SIGTERM then SIGKILL (1s grace) on reload
- **Degradation mode**: Enable `allow_degradation: true` for non-critical plugins
- **Connection reuse**: Runner should reuse socket connections

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `failed to receive RPC_PREPARE_CONF` | Runner not listening or socket path mismatch | Verify `path_for_test` matches `APISIX_LISTEN_ADDRESS` |
| 503 Service Unavailable | Runner crashed or not started | Check runner logs; verify `cmd` path is correct |
| Runner not receiving env vars | Nginx hides env vars by default | Add vars to `nginx_config.envs` in config.yaml |
| Slow response times | External plugin doing heavy work | Profile runner; consider async processing |
| `ext-plugin-post-resp` conflicts | Incompatible with proxy-* plugins | Use `ext-plugin-post-req` instead, or remove proxy-mirror/cache |
