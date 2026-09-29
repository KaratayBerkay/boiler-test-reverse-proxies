---
title: "jwt-auth plugin"
description: "Skill for configuring the Apache APISIX jwt-auth plugin via the a6 CLI. Covers JWT token authentication, HS256/RS256 algorithm selection, consumer credential binding, token lookup from header/query/cookie, claims handling, clock skew, secret management, and common operational patterns."
metadata:
  category: plugin
  plugin_name: jwt-auth
  apisix_version: ">=3.11.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 consumer create
    - a6 consumer update
    - a6 credential create
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-jwt-auth/SKILL.md
---
# jwt-auth plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `jwt-auth` plugin authenticates requests using JSON Web Tokens. Consumers
register a key and secret (or public key for asymmetric algorithms). Clients
include a signed JWT in the request header, query parameter, or cookie. APISIX
validates the signature and claims, then forwards the request with consumer
identity headers.

## When to Use

- Token-based stateless authentication
- Asymmetric key verification (RS256, ES256, EdDSA) where APISIX only needs the public key
- Custom claims-based consumer identification
- Integration with external token issuers (your own auth server, Auth0, etc.)

## Consumer Credential Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `key` | string | **Yes** | — | Unique identifier in JWT payload to match consumer |
| `secret` | string | Conditional | — | Shared secret for HMAC algorithms (HS256/HS384/HS512). Encrypted in etcd. |
| `public_key` | string | Conditional | — | PEM public key for RSA/ECDSA/EdDSA algorithms |
| `algorithm` | string | No | `"HS256"` | Signing algorithm (see supported list below) |
| `exp` | integer | No | `86400` | Token lifetime in **seconds** (not UNIX timestamp) |
| `base64_secret` | boolean | No | `false` | Set true if secret is base64-encoded |
| `lifetime_grace_period` | integer | No | `0` | Clock skew tolerance in seconds |
| `key_claim_name` | string | No | `"key"` | JWT claim containing the consumer key |

### Supported Algorithms

| Family | Algorithms |
|--------|-----------|
| HMAC | HS256, HS384, HS512 |
| RSA | RS256, RS384, RS512 |
| RSA-PSS | PS256, PS384, PS512 |
| ECDSA | ES256, ES384, ES512 |
| EdDSA | EdDSA |

## Route/Service Configuration Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `header` | string | No | `"authorization"` | Header to extract JWT from |
| `query` | string | No | `"jwt"` | Query parameter to extract JWT from |
| `cookie` | string | No | `"jwt"` | Cookie to extract JWT from |
| `hide_credentials` | boolean | No | `false` | Remove JWT before forwarding upstream |
| `key_claim_name` | string | No | `"key"` | JWT claim containing consumer key (must match credential config) |
| `anonymous_consumer` | string | No | — | Consumer for unauthenticated requests |
| `claims_to_verify` | array | No | `["exp","nbf"]` | Claims to verify (`exp`, `nbf`) |

## Token Lookup Priority

1. **Header** (default: `authorization`) — supports `Bearer <token>` prefix
2. **Query parameter** (default: `jwt`)
3. **Cookie** (default: `jwt`)

## Step-by-Step: Enable jwt-auth with HS256

### 1. Create a consumer

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "alice"
}
EOF
```

### 2. Add jwt-auth credential

Save the credential as `credential.yaml`, then create it:

```yaml
id: cred-alice-jwt
plugins:
  jwt-auth:
    key: alice-key
    secret: alice-secret-minimum-32-chars-long
    algorithm: HS256
    exp: 86400
```

```bash
a6 credential create --consumer alice -f credential.yaml
```

### 3. Create a route with jwt-auth

```bash
a6 route create -f - <<'EOF'
{
  "id": "jwt-protected",
  "uri": "/api/*",
  "plugins": {
    "jwt-auth": {}
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

### 4. Generate a JWT and test

Create a JWT with payload `{"key": "alice-key", "exp": <future_timestamp>}`
signed with `alice-secret-minimum-32-chars-long` using HS256.

```bash
curl -i http://127.0.0.1:9080/api/test \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..."
```

## Step-by-Step: Enable jwt-auth with RS256

### 1. Generate RSA key pair

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

### 2. Create a consumer

```bash
a6 consumer create -f - <<'EOF'
{
  "username": "bob"
}
EOF
```

### 3. Create a credential with the public key

Save the following as `bob-rs256-credential.yaml`, replacing the placeholder
with the base64 body between the PEM delimiters in `public.pem`:

```yaml
id: cred-bob-jwt
plugins:
  jwt-auth:
    key: bob-key
    algorithm: RS256
    public_key: |
      -----BEGIN PUBLIC KEY-----
      replace-with-the-base64-body-from-public.pem
      -----END PUBLIC KEY-----
```

```bash
a6 credential create --consumer bob -f bob-rs256-credential.yaml
```

Sign tokens with `private.pem` externally; APISIX only needs the public key.

## Common Patterns

### Custom claim name (use `iss` instead of `key`)

```bash
# Credential config:
{
  "jwt-auth": {
    "key": "my-issuer-id",
    "secret": "my-secret",
    "key_claim_name": "iss"
  }
}

# Route config:
{
  "jwt-auth": {
    "key_claim_name": "iss"
  }
}

# JWT payload:
{
  "iss": "my-issuer-id",
  "exp": 1879318541
}
```

### Clock skew tolerance

```json
{
  "jwt-auth": {
    "key": "consumer-key",
    "secret": "my-secret",
    "lifetime_grace_period": 30
  }
}
```

Allows 30 seconds clock drift between token issuer and APISIX.

### Token in query parameter

```json
{
  "plugins": {
    "jwt-auth": {
      "query": "token"
    }
  }
}
```

Client sends: `curl "http://127.0.0.1:9080/api/test?token=eyJ..."`

### Secret management with environment variables

```json
{
  "jwt-auth": {
    "key": "consumer-key",
    "secret": "$env://JWT_SECRET"
  }
}
```

### Secret management with HashiCorp Vault

```json
{
  "jwt-auth": {
    "key": "consumer-key",
    "secret": "$secret://vault/jwt/consumer-name/jwt-secret"
  }
}
```

## Headers Added to Upstream

| Header | Value |
|--------|-------|
| `X-Consumer-Username` | Consumer's username |
| `X-Credential-Identifier` | Credential ID |
| `X-Consumer-Custom-Id` | Consumer's `labels.custom_id` (if set) |

## Error Responses

| HTTP Code | Message | Cause |
|-----------|---------|-------|
| 401 | `"Missing JWT token in request"` | No token in header/query/cookie |
| 401 | `"JWT token invalid"` | Malformed token |
| 401 | `"failed to verify jwt"` | Bad signature, expired, or invalid claims |
| 401 | `"Invalid user key in JWT token"` | Consumer key not found |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 "failed to verify jwt"` | Token expired | Generate new token with future `exp` |
| `401 "failed to verify jwt"` | Algorithm mismatch | Ensure credential `algorithm` matches token |
| `401 "Invalid user key"` | Wrong claim name | Set `key_claim_name` on both credential and route |
| Public key rejected | Missing newlines in PEM | Include `\n` after header/before footer lines |
| Clock skew errors | Time drift | Set `lifetime_grace_period` on credential |

## Config Sync Example

```yaml
version: "1"
consumers:
  - username: alice
routes:
  - id: jwt-protected
    uri: /api/*
    plugins:
      jwt-auth: {}
    upstream_id: my-upstream
upstreams:
  - id: my-upstream
    type: roundrobin
    nodes:
      "backend:8080": 1
```

> **Note**: Consumer credentials (including JWT keys/secrets) must be created
> separately via the Admin API; `a6 config sync` manages the consumer resource
> but credentials are sub-resources.
