---
title: "openid-connect plugin"
description: "Skill for configuring the APISIX openid-connect plugin via the a6 CLI. Covers authorization-code and bearer flows, PAR, DPoP, and session validation."
metadata:
  category: plugin
  plugin_name: openid-connect
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-openid-connect/SKILL.md
---
# openid-connect plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `openid-connect` plugin integrates APISIX with external OpenID Connect
identity providers (Keycloak, Auth0, Okta, etc.). It supports the full
authorization code flow for browser-based applications, bearer token validation
for API clients, and token introspection or local JWKS verification.

From APISIX 3.18.0 the plugin also supports nested PAR and DPoP configuration,
forwards the raw ID token when `set_raw_id_token_header` is enabled, fails closed
when the trusted issuer cannot be determined, treats
`claim_validator.audience.match_with_client_id` as requiring an audience claim,
and enforces `required_scopes` on authorization-code sessions. For bearer JWT
validation, configure `claim_validator.issuer.valid_issuers` when discovery can
be unavailable.

Field tables and a Keycloak PAR/DPoP walkthrough:
https://docs.api7.ai/hub/openid-connect
https://docs.api7.ai/apisix/how-to-guide/authentication/secure-oidc-with-par-and-dpop

## When to Use

- Integrate with enterprise identity providers (Keycloak, Auth0, Okta, Azure AD)
- Browser-based SSO with authorization code flow
- API protection with bearer access tokens
- Centralized authentication across multiple routes

## Plugin Configuration Reference (Route/Service)

### Required Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `client_id` | string | **Yes** | — | OAuth 2.0 client ID |
| `client_secret` | string | Conditional | — | OAuth 2.0 client secret (encrypted in etcd). Optional for local JWT verification, `private_key_jwt`, or a public-client PKCE flow |
| `discovery` | string | **Yes** | — | OIDC well-known discovery URL |

### Authentication & Scopes

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `scope` | string | No | `"openid"` | Space-delimited OIDC scopes |
| `bearer_only` | boolean | No | `false` | Require bearer access token only (no redirect) |
| `required_scopes` | array | No | — | Scopes required in access token |
| `realm` | string | No | `"apisix"` | Realm in WWW-Authenticate header |

### URIs & Redirects

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `redirect_uri` | string | No | `{route_uri}/.apisix/redirect` | Redirect URI after auth |
| `logout_path` | string | No | `"/logout"` | Path to trigger logout |
| `post_logout_redirect_uri` | string | No | — | URL to redirect after logout |
| `unauth_action` | string | No | `"auth"` | Action on unauth: `"auth"` (redirect), `"deny"` (401), `"pass"` (allow) |

### Token Verification

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `introspection_endpoint` | string | No | — | Token introspection endpoint URL |
| `public_key` | string | No | — | PEM public key for local JWT verification |
| `use_jwks` | boolean | No | `false` | Use JWKS from discovery for local JWT verification |
| `token_signing_alg_values_expected` | string | No | — | Expected JWT signing algorithm |

### Session Management

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `session.secret` | string | Yes* | — | 16+ char key for session encryption (*required for auth code flow) |
| `session.absolute_timeout` | integer | No | — | Absolute session lifetime in seconds |
| `session.cookie.lifetime` | integer | No | — | Deprecated alias for `session.absolute_timeout` |
| `session.storage` | string | No | `"cookie"` | `"cookie"` or `"redis"` |

### Headers to Upstream

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `set_access_token_header` | boolean | No | `true` | Set `X-Access-Token` header |
| `access_token_in_authorization_header` | boolean | No | `false` | Set token in `Authorization` header |
| `set_id_token_header` | boolean | No | `true` | Set `X-ID-Token` header |
| `set_raw_id_token_header` | boolean | No | `false` | Set `X-Raw-ID-Token` with the unmodified ID token |
| `set_userinfo_header` | boolean | No | `true` | Set `X-Userinfo` header |
| `hide_credentials` | boolean | No | `false` | Remove auth headers before upstream |

### PAR and DPoP (APISIX 3.18.0+)

Configure these as nested objects. Flat keys such as `use_par` or `use_dpop` are
rejected.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `par.enabled` | boolean | No | `false` | Send the authorization request through PAR |
| `dpop.enabled` | boolean | No | `false` | Bind token requests with a DPoP proof JWT |

See the Plugin Hub page for endpoint auth, key material, and validation rules.

### Advanced

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ssl_verify` | boolean | No | `true` | Verify IdP SSL certificates |
| `timeout` | integer | No | `3` | Request timeout to IdP in seconds |
| `use_pkce` | boolean | No | `false` | Enable PKCE (RFC 7636) |
| `renew_access_token_on_expiry` | boolean | No | `true` | Auto-refresh expiring tokens |

## Token Verification Modes

### 1. Token Introspection (default for bearer_only)

APISIX calls the IdP's introspection endpoint for every request.

- **Pros**: Real-time validation, handles token revocation
- **Cons**: Added latency (network call to IdP)

```json
{
  "openid-connect": {
    "client_id": "my-app",
    "client_secret": "secret",
    "discovery": "https://keycloak.example.com/realms/my/.well-known/openid-configuration",
    "bearer_only": true,
    "introspection_endpoint": "https://keycloak.example.com/realms/my/protocol/openid-connect/token/introspect"
  }
}
```

### 2. Local JWKS Verification

APISIX fetches JWKS from the discovery document and validates JWT locally.

- **Pros**: Fast (no per-request IdP call), scalable
- **Cons**: Cannot detect revoked tokens until JWKS cache refreshes

```json
{
  "openid-connect": {
    "client_id": "my-app",
    "client_secret": "secret",
    "discovery": "https://keycloak.example.com/realms/my/.well-known/openid-configuration",
    "bearer_only": true,
    "use_jwks": true
  }
}
```

### 3. Static Public Key Verification

Provide the public key directly. No discovery or introspection calls.

```json
{
  "openid-connect": {
    "client_id": "my-app",
    "client_secret": "secret",
    "discovery": "https://keycloak.example.com/realms/my/.well-known/openid-configuration",
    "bearer_only": true,
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjAN...\n-----END PUBLIC KEY-----"
  }
}
```

## Step-by-Step: Authorization Code Flow (Keycloak)

### 1. Create a route with openid-connect

```bash
a6 route create -f - <<'EOF'
{
  "id": "oidc-webapp",
  "uri": "/app/*",
  "plugins": {
    "openid-connect": {
      "client_id": "apisix-client",
      "client_secret": "your-client-secret",
      "discovery": "https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration",
      "scope": "openid email profile",
      "redirect_uri": "http://127.0.0.1:9080/app/redirect",
      "session": {
        "secret": "my-16-char-secret"
      }
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "webapp:3000": 1
    }
  }
}
EOF
```

### 2. Flow

1. User visits `http://127.0.0.1:9080/app/dashboard` → no session
2. APISIX redirects to Keycloak login page
3. User authenticates → Keycloak redirects to `http://127.0.0.1:9080/app/redirect?code=...`
4. APISIX exchanges code for tokens, stores in session cookie
5. Subsequent requests use the session cookie automatically

## Step-by-Step: Bearer Token API Protection

### 1. Create a route for API protection

```bash
a6 route create -f - <<'EOF'
{
  "id": "oidc-api",
  "uri": "/api/*",
  "plugins": {
    "openid-connect": {
      "client_id": "apisix-client",
      "client_secret": "your-client-secret",
      "discovery": "https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration",
      "bearer_only": true,
      "use_jwks": true
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

### 2. Obtain and use token

```bash
# Get token from IdP
TOKEN=$(curl -s -X POST \
  "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token" \
  -d "client_id=apisix-client" \
  -d "client_secret=your-client-secret" \
  -d "grant_type=client_credentials" \
  | jq -r '.access_token')

# Call the API
curl -i http://127.0.0.1:9080/api/resource \
  -H "Authorization: Bearer ${TOKEN}"
```

## Provider Discovery URLs

| Provider | Discovery URL Pattern |
|----------|----------------------|
| **Keycloak** | `https://{host}/realms/{realm}/.well-known/openid-configuration` |
| **Auth0** | `https://{tenant}.auth0.com/.well-known/openid-configuration` |
| **Okta** | `https://{org}.okta.com/.well-known/openid-configuration` |
| **Azure AD** | `https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration` |
| **Google** | `https://accounts.google.com/.well-known/openid-configuration` |

## Common Patterns

### Redis session storage (distributed APISIX)

```json
{
  "openid-connect": {
    "client_id": "my-app",
    "client_secret": "secret",
    "discovery": "https://idp.example.com/.well-known/openid-configuration",
    "session": {
      "secret": "my-16-char-secret",
      "storage": "redis",
      "redis": {
        "host": "redis.example.com",
        "port": 6379,
        "password": "redis-pass",
        "database": 0
      }
    }
  }
}
```

### Allow unauthenticated access (optional auth)

```json
{
  "openid-connect": {
    "client_id": "my-app",
    "client_secret": "secret",
    "discovery": "https://idp.example.com/.well-known/openid-configuration",
    "bearer_only": true,
    "unauth_action": "pass"
  }
}
```

Authenticated requests get identity headers; unauthenticated requests pass
through without identity.

### PKCE for public clients

```json
{
  "openid-connect": {
    "client_id": "spa-client",
    "client_secret": "secret",
    "discovery": "https://idp.example.com/.well-known/openid-configuration",
    "use_pkce": true,
    "session": {
      "secret": "my-16-char-secret"
    }
  }
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Redirect loop after login | `redirect_uri` same as route URI | Set `redirect_uri` to a sub-path (e.g., `/app/redirect`) |
| `"no session state found"` | Session cookie not saved | Check `session.secret` length (16+ chars), check SameSite cookie policy |
| `401` on valid bearer token | Introspection failing | Verify `introspection_endpoint` URL, check client credentials |
| SSL errors to IdP | `ssl_verify: true` but certs invalid | Fix certs or set `ssl_verify: false` for testing |
| Large cookie errors | Session too big for cookie | Switch to `session.storage: "redis"` |
| Token not refreshing | `renew_access_token_on_expiry: false` | Set to `true` (default) |
| `403` with `required_scopes` after login | Session scopes missing or unreadable (3.18.0+) | Confirm granted scopes on the access or ID token; `required_scopes` applies to authorization-code sessions |
| Bearer JWT rejected while discovery is down | Issuer fail-closed (3.18.0+) | Set `claim_validator.issuer.valid_issuers` |
| NGINX buffer errors | Session cookie too large | Increase `proxy_buffers` / `proxy_buffer_size` in NGINX config |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: oidc-webapp
    uri: /app/*
    plugins:
      openid-connect:
        client_id: apisix-client
        client_secret: your-client-secret
        discovery: https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration
        scope: openid email profile
        redirect_uri: http://127.0.0.1:9080/app/redirect
        session:
          secret: my-16-char-secret
    upstream_id: webapp-upstream
upstreams:
  - id: webapp-upstream
    type: roundrobin
    nodes:
      "webapp:3000": 1
```
