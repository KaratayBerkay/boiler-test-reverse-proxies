---
title: "hmac-auth plugin"
description: "Skill for configuring the Apache APISIX hmac-auth plugin via the a6 CLI. Covers HMAC signature authentication, consumer credential binding with key_id/secret_key, allowed algorithms, clock skew handling, request body validation, signed headers, and common operational patterns."
metadata:
  category: plugin
  plugin_name: hmac-auth
  apisix_version: ">=3.11.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 consumer create
    - a6 consumer update
    - a6 credential create
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-hmac-auth/SKILL.md
---
# hmac-auth plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `hmac-auth` plugin authenticates requests using HMAC (Hash-based Message
Authentication Code) signatures. Clients compute an HMAC signature over the
request method, path, date, and optional headers/body, then include it in the
`Authorization` header. APISIX recomputes the signature server-side and verifies
it matches. This provides request integrity verification without transmitting
secrets over the wire.

## When to Use

- Request integrity verification (tamper-proof API calls)
- Server-to-server authentication where both sides share a secret
- APIs requiring body integrity validation
- Environments where tokens or passwords should never appear in requests

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `allowed_algorithms` | array | No | `["hmac-sha1","hmac-sha256","hmac-sha512"]` | HMAC algorithms allowed |
| `clock_skew` | integer | No | `300` | Max allowed time difference in seconds between client and server |
| `signed_headers` | array | No | — | Additional headers required in the HMAC signature |
| `validate_request_body` | boolean | No | `false` | Validate request body integrity via SHA-256 digest |
| `hide_credentials` | boolean | No | `false` | Remove Authorization header before forwarding upstream |
| `anonymous_consumer` | string | No | — | Consumer username for unauthenticated requests |
| `realm` | string | No | `"hmac"` | Realm in `WWW-Authenticate` response header |

## Consumer Credential Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key_id` | string | **Yes** | Unique identifier for the consumer |
| `secret_key` | string | **Yes** | Secret key for HMAC computation. Auto-encrypted in etcd. |

## Step-by-Step: Enable hmac-auth on a Route

### 1. Create a consumer

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "alice"
}
EOF
```

### 2. Add hmac-auth credential

Save the credential as `credential.yaml`, then create it:

```yaml
id: cred-alice-hmac
plugins:
  hmac-auth:
    key_id: alice-key
    secret_key: alice-secret-key-value
```

```bash
a6 credential create --consumer alice -f credential.yaml
```

### 3. Create a route with hmac-auth enabled

```bash
a6 route create -f - <<'EOF'
{
  "id": "hmac-protected",
  "uri": "/api/*",
  "plugins": {
    "hmac-auth": {}
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

### 4. Generate signature and test

The HMAC signature follows the [HTTP Signatures draft](https://www.ietf.org/archive/id/draft-cavage-http-signatures-12.txt).

**Python example:**

```python
import hmac, hashlib, base64
from datetime import datetime, timezone

key_id = "alice-key"
secret_key = b"alice-secret-key-value"
method = "GET"
path = "/api/users"
algorithm = "hmac-sha256"

gmt_time = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

signing_string = f"{key_id}\n{method} {path}\ndate: {gmt_time}\n"

signature = base64.b64encode(
    hmac.new(secret_key, signing_string.encode(), hashlib.sha256).digest()
).decode()

# Use these headers in request:
# Date: {gmt_time}
# Authorization: Signature keyId="{key_id}",algorithm="{algorithm}",
#   headers="@request-target date",signature="{signature}"
```

**curl example:**

```bash
curl -i http://127.0.0.1:9080/api/users \
  -H "Date: $(date -u +'%a, %d %b %Y %H:%M:%S GMT')" \
  -H 'Authorization: Signature keyId="alice-key",algorithm="hmac-sha256",headers="@request-target date",signature="<computed_signature>"'
```

## Authorization Header Format

```
Signature keyId="{key_id}",algorithm="{algorithm}",headers="{signed_headers}",signature="{signature}"
```

| Component | Description |
|-----------|-------------|
| `keyId` | Consumer's `key_id` value |
| `algorithm` | One of: `hmac-sha1`, `hmac-sha256`, `hmac-sha512` |
| `headers` | Space-separated list: `@request-target date [additional...]` |
| `signature` | Base64-encoded HMAC signature |

## Signing String Construction

The signing string is newline-separated:

```
{key_id}\n
{METHOD} {path}\n
date: {Date header value}\n
{additional-header}: {value}\n
```

- First line: the `key_id`
- Second line: HTTP method + space + request path
- Subsequent lines: lowercase header names with values
- Each line terminated with `\n`

## Common Patterns

### Restrict to specific algorithms

```json
{
  "plugins": {
    "hmac-auth": {
      "allowed_algorithms": ["hmac-sha256", "hmac-sha512"]
    }
  }
}
```

### Increase clock skew tolerance

```json
{
  "plugins": {
    "hmac-auth": {
      "clock_skew": 600
    }
  }
}
```

Allows up to 10 minutes time difference.

### Validate request body

```json
{
  "plugins": {
    "hmac-auth": {
      "validate_request_body": true
    }
  }
}
```

Client must include `Digest: SHA-256={base64_sha256_of_body}` header. APISIX
recomputes the body digest and rejects the request if it does not match.

### Require custom headers in signature

```json
{
  "plugins": {
    "hmac-auth": {
      "signed_headers": ["x-custom-header-a", "x-custom-header-b"]
    }
  }
}
```

## Headers Added to Upstream

| Header | Value |
|--------|-------|
| `X-Consumer-Username` | Consumer's username |
| `X-Credential-Identifier` | Credential ID |
| `X-Consumer-Custom-Id` | Consumer's `labels.custom_id` (if set) |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401` signature mismatch | Signing string differs from server expectation | Verify newline format, header lowercase, key_id first line |
| `401` clock skew | `Date` header too far from server time | Sync clocks or increase `clock_skew` |
| `401` algorithm not allowed | Client used algorithm not in `allowed_algorithms` | Add algorithm to allow list or change client |
| `401` body digest mismatch | Body changed after digest computed | Recompute `Digest` header from actual body |
| Signature hard to debug | Complex signing string | Log the exact signing string client-side and compare |

## Config Sync Example

```yaml
version: "1"
consumers:
  - username: alice
routes:
  - id: hmac-protected
    uri: /api/*
    plugins:
      hmac-auth: {}
    upstream_id: my-upstream
upstreams:
  - id: my-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```

> **Note**: Consumer credentials (key_id/secret_key) must be created separately
> via the Admin API; `a6 config sync` manages the consumer resource but
> credentials are sub-resources.
