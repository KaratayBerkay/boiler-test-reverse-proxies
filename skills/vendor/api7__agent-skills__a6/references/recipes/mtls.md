---
title: "mtls recipe"
description: "Recipe skill for configuring mutual TLS (mTLS) using the a6 CLI. Covers SSL certificate management, upstream mTLS to backend services, client certificate verification, and end-to-end mTLS setup from client through APISIX to upstream."
metadata:
  category: recipe
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 ssl create
    - a6 ssl update
    - a6 ssl list
    - a6 ssl get
    - a6 ssl delete
    - a6 upstream create
    - a6 upstream update
    - a6 route create
  source: https://github.com/api7/a6/blob/main/skills/a6-recipe-mtls/SKILL.md
---
# mtls recipe

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

Mutual TLS (mTLS) ensures both the client and server verify each other's
identity via TLS certificates. Standard TLS only verifies the server; mTLS
adds client certificate verification.

With APISIX and the a6 CLI, you can configure:
1. **Client → APISIX mTLS**: Require clients to present valid certificates
2. **APISIX → Upstream mTLS**: Present client certificates when connecting to backends
3. **End-to-end mTLS**: Both directions simultaneously

## When to Use

- Zero-trust networking between services
- Secure service-to-service communication in microservices
- Compliance requirements mandating mutual authentication
- Replace or supplement API key authentication with certificate-based auth
- Internal APIs that should only be accessible by authorized services

## Concepts

| Term | Description |
|------|-------------|
| **CA certificate** | Certificate Authority cert used to verify client/server certs |
| **Server certificate** | Presented by APISIX to clients (standard TLS) |
| **Client certificate** | Presented by clients to APISIX (mTLS verification) |
| **Upstream TLS** | APISIX presents a client cert to the upstream backend |

## Part 1: Client → APISIX mTLS

Require clients to present a valid TLS certificate when connecting to APISIX.

### 1. Create SSL resource with CA for client verification

```bash
a6 ssl create -f - <<'EOF'
{
  "id": "mtls-domain",
  "cert": "<SERVER_CERTIFICATE_PEM>",
  "key": "<SERVER_PRIVATE_KEY_PEM>",
  "snis": ["api.example.com"],
  "client": {
    "ca": "<CA_CERTIFICATE_PEM>"
  }
}
EOF
```

**Fields**:
- `cert` / `key`: Server certificate and private key (presented to clients)
- `snis`: Server Name Indications — domain names this certificate covers
- `client.ca`: CA certificate used to verify client certificates
- `client.depth`: (optional) Maximum certificate chain depth for verification

### 2. Create a route on the protected domain

```bash
a6 route create -f - <<'EOF'
{
  "id": "secure-api",
  "uri": "/api/*",
  "host": "api.example.com",
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "backend:8080": 1
    }
  }
}
EOF
```

### 3. Test with client certificate

```bash
# With valid client cert — succeeds
curl --cert client.crt --key client.key --cacert ca.crt \
  https://api.example.com:9443/api/health

# Without client cert — fails with SSL handshake error
curl --cacert ca.crt https://api.example.com:9443/api/health
```

## Part 2: APISIX → Upstream mTLS

Configure APISIX to present a client certificate when connecting to backends.

### 1. Create upstream with TLS client certificate

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "mtls-backend",
  "type": "roundrobin",
  "scheme": "https",
  "nodes": {
    "secure-backend:443": 1
  },
  "tls": {
    "client_cert": "<CLIENT_CERTIFICATE_PEM>",
    "client_key": "<CLIENT_PRIVATE_KEY_PEM>"
  }
}
EOF
```

**Fields**:
- `scheme`: Must be `"https"` for TLS connections to upstream
- `tls.client_cert`: Client certificate APISIX presents to the upstream
- `tls.client_key`: Private key for the client certificate
- `pass_host`: Set to `"pass"` (default) or `"rewrite"` if upstream expects a specific Host header

### 2. Create route using this upstream

```bash
a6 route create -f - <<'EOF'
{
  "id": "api",
  "uri": "/api/*",
  "upstream_id": "mtls-backend"
}
EOF
```

## Part 3: End-to-End mTLS

Combine both: clients verify themselves to APISIX, and APISIX verifies
itself to the upstream.

### 1. SSL for client → APISIX mTLS

```bash
a6 ssl create -f - <<'EOF'
{
  "id": "frontend-mtls",
  "cert": "<APISIX_SERVER_CERT>",
  "key": "<APISIX_SERVER_KEY>",
  "snis": ["api.example.com"],
  "client": {
    "ca": "<CLIENT_CA_CERT>"
  }
}
EOF
```

### 2. Upstream for APISIX → backend mTLS

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "secure-backend",
  "type": "roundrobin",
  "scheme": "https",
  "nodes": {
    "internal-service:443": 1
  },
  "tls": {
    "client_cert": "<APISIX_CLIENT_CERT>",
    "client_key": "<APISIX_CLIENT_KEY>"
  }
}
EOF
```

### 3. Route connecting both

```bash
a6 route create -f - <<'EOF'
{
  "id": "e2e-mtls-api",
  "uri": "/api/*",
  "host": "api.example.com",
  "upstream_id": "secure-backend"
}
EOF
```

## Common Patterns

### Multiple domains with different CAs

```bash
# Domain A: internal services
a6 ssl create -f - <<'EOF'
{
  "id": "internal-mtls",
  "cert": "<INTERNAL_CERT>",
  "key": "<INTERNAL_KEY>",
  "snis": ["internal.example.com"],
  "client": {
    "ca": "<INTERNAL_CA>"
  }
}
EOF

# Domain B: partner services
a6 ssl create -f - <<'EOF'
{
  "id": "partner-mtls",
  "cert": "<PARTNER_CERT>",
  "key": "<PARTNER_KEY>",
  "snis": ["partner.example.com"],
  "client": {
    "ca": "<PARTNER_CA>"
  }
}
EOF
```

### Using APISIX Secret for certificate management

Configure APISIX to read certificate material from a supported external secret
manager. This example registers a Vault KV v1 manager; store the certificate
values separately in Vault and reference them from the SSL resource with
`$secret://vault/mtls-certs/<secret-name>/<key>`.

```bash
# Configure a Vault secret manager
a6 secret create vault/mtls-certs -f - <<'EOF'
{
  "uri": "https://vault.example.com",
  "prefix": "apisix",
  "token": "<VAULT_TOKEN>"
}
EOF
```

### Certificate rotation

Update certificates without downtime:

```bash
a6 ssl update mtls-domain -f - <<'EOF'
{
  "cert": "<NEW_CERT>",
  "key": "<NEW_KEY>",
  "client": {
    "ca": "<NEW_OR_SAME_CA>"
  }
}
EOF
```

APISIX picks up the new certificate immediately — no restart needed.

## Config Sync Example

```yaml
version: "1"
ssls:
  - id: api-mtls
    cert: |
      -----BEGIN CERTIFICATE-----
      <server certificate>
      -----END CERTIFICATE-----
    key: |
      -----BEGIN RSA PRIVATE KEY-----
      <server private key>
      -----END RSA PRIVATE KEY-----
    snis:
      - api.example.com
    client:
      ca: |
        -----BEGIN CERTIFICATE-----
        <CA certificate for client verification>
        -----END CERTIFICATE-----
upstreams:
  - id: secure-backend
    type: roundrobin
    scheme: https
    nodes:
      "backend:443": 1
    tls:
      client_cert: |
        -----BEGIN CERTIFICATE-----
        <client certificate for upstream>
        -----END CERTIFICATE-----
      client_key: |
        -----BEGIN RSA PRIVATE KEY-----
        <client private key for upstream>
        -----END RSA PRIVATE KEY-----
routes:
  - id: mtls-api
    uri: /api/*
    host: api.example.com
    upstream_id: secure-backend
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| SSL handshake failure (client side) | Client cert not signed by the CA in `client.ca` | Verify CA chain; check that client cert is signed by the correct CA |
| "no required SSL certificate" | Client didn't send a certificate | Configure client to present cert (`--cert` in curl) |
| 502 to upstream | Upstream rejects APISIX's client cert | Verify `tls.client_cert` is signed by the upstream's trusted CA |
| Certificate expired | TLS cert past validity date | Rotate certificate with `a6 ssl update` |
| SNI mismatch | Domain doesn't match `snis` list | Add the domain to the `snis` array |
| "unable to verify" | Self-signed cert without proper CA trust | Use `--cacert` in curl or add CA to system trust store |
| Mixed HTTP/HTTPS | Route accessible on both ports | Configure APISIX `listen` to only expose HTTPS port for mTLS domains |
