---
title: "ip-restriction plugin"
description: "Skill for configuring the Apache APISIX ip-restriction plugin via the a6 CLI. Covers IP whitelist/blacklist setup on routes, CIDR range support, IPv4/IPv6, real client IP extraction behind proxies, custom error messages, and common operational patterns."
metadata:
  category: plugin
  plugin_name: ip-restriction
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-ip-restriction/SKILL.md
---
# ip-restriction plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `ip-restriction` plugin controls access to routes based on client IP address.
Configure a whitelist (only listed IPs allowed) or a blacklist (listed IPs
blocked). Supports individual IPs and CIDR ranges for both IPv4 and IPv6.

## When to Use

- Restrict API access to known IP ranges (office, VPN, partners)
- Block malicious IPs or IP ranges
- Limit admin endpoints to internal networks
- Implement geo-based access control at the IP level

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `whitelist` | array[string] | Conditional* | — | IPs/CIDR ranges allowed access |
| `blacklist` | array[string] | Conditional* | — | IPs/CIDR ranges denied access |
| `message` | string | No | `"Your IP address is not allowed"` | Error message (1–1024 chars) |
| `response_code` | integer | No | `403` | HTTP status on denial (403 or 404) |

**\*Constraint**: Exactly one of `whitelist` or `blacklist` is required. Cannot
use both simultaneously.

## How IP Matching Works

- **Whitelist**: Request allowed only if client IP matches an entry. All others
  blocked.
- **Blacklist**: Request blocked if client IP matches an entry. All others
  allowed.
- **CIDR support**: Full support for CIDR notation (e.g., `192.168.1.0/24`,
  `10.0.0.0/8`, `2001:db8::/32`).
- **IPv4 and IPv6**: Both address families supported.
- **Default IP source**: Uses `$remote_addr` (direct client IP from the TCP
  connection).

## Step-by-Step: Whitelist an IP Range

### 1. Create a route with ip-restriction

```bash
a6 route create -f - <<'EOF'
{
  "id": "internal-api",
  "uri": "/admin/*",
  "plugins": {
    "ip-restriction": {
      "whitelist": [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16"
      ]
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

### 2. Verify access

```bash
# From allowed IP (e.g., 10.0.1.5) → 200 OK
curl -i http://127.0.0.1:9080/admin/dashboard

# From blocked IP → 403 Forbidden
# {"message": "Your IP address is not allowed"}
```

## Step-by-Step: Blacklist Specific IPs

```bash
a6 route create -f - <<'EOF'
{
  "id": "public-api",
  "uri": "/api/*",
  "plugins": {
    "ip-restriction": {
      "blacklist": [
        "203.0.113.0/24",
        "198.51.100.42"
      ],
      "message": "Access denied from your network",
      "response_code": 403
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

### Real client IP behind a proxy (X-Forwarded-For)

By default, `ip-restriction` uses `$remote_addr` which is the direct client
(often a load balancer). To use the real client IP, combine with the `real-ip`
plugin:

```json
{
  "plugins": {
    "real-ip": {
      "source": "http_x_forwarded_for",
      "trusted_addresses": ["10.0.0.0/8"]
    },
    "ip-restriction": {
      "whitelist": ["203.0.113.0/24"]
    }
  }
}
```

**Critical**: Always set `trusted_addresses` in `real-ip` to prevent IP
spoofing. Only accept `X-Forwarded-For` from known proxy IPs.

### Custom 404 response (hide endpoint existence)

```json
{
  "plugins": {
    "ip-restriction": {
      "blacklist": ["0.0.0.0/0"],
      "whitelist": ["10.0.0.0/8"],
      "response_code": 404,
      "message": "Not found"
    }
  }
}
```

> Note: You cannot actually use both whitelist and blacklist. Use whitelist
> alone to achieve the same effect — all IPs not in the whitelist are blocked.

### IPv6 CIDR ranges

```json
{
  "plugins": {
    "ip-restriction": {
      "whitelist": [
        "2001:db8::/32",
        "::1"
      ]
    }
  }
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Legitimate users blocked | Using `$remote_addr` behind proxy | Add `real-ip` plugin with `trusted_addresses` |
| All users blocked on whitelist | Client IPs not in whitelist CIDR | Verify IP ranges with `curl ifconfig.me` from client |
| Cannot use both whitelist and blacklist | Schema enforces `oneOf` | Use whitelist only (blocks all non-listed) |
| IP restriction not working after change | IP matchers are LRU-cached | Update the route config to bust cache |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: internal-api
    uri: /admin/*
    plugins:
      ip-restriction:
        whitelist:
          - "10.0.0.0/8"
          - "172.16.0.0/12"
    upstream_id: admin-upstream
upstreams:
  - id: admin-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```
