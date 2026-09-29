---
title: "developer persona"
description: "Persona skill for API developers building and testing APIs on APISIX using the a6 CLI. Provides decision frameworks for API design, route configuration, plugin selection, testing workflows, local development setup, and CI/CD integration patterns."
metadata:
  category: persona
  apisix_version: ">=3.11.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 route get
    - a6 upstream create
    - a6 service create
    - a6 consumer create
    - a6 credential create
    - a6 plugin list
    - a6 plugin get
    - a6 config sync
    - a6 config dump
    - a6 config validate
    - a6 debug trace
  source: https://github.com/api7/a6/blob/main/skills/a6-persona-developer/SKILL.md
---
# developer persona

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Who This Is For

You are an **API developer** responsible for:
- Designing and configuring API routes on APISIX
- Choosing and configuring plugins for auth, rate limiting, transformation
- Testing APIs locally against a development APISIX instance
- Writing declarative configs for CI/CD pipelines
- Debugging request flow through the gateway

## Getting Started

### 1. Install and configure

```bash
# Install a6
go install github.com/api7/a6/cmd/a6@latest

# Connect to your dev APISIX instance
a6 context create dev --server http://localhost:9180 --api-key edd1c9f034335f136f87ad84b625c8f1

# Verify connection
a6 route list --output table
```

### 2. Explore available plugins

```bash
# List all available plugins
a6 plugin list

# Get the schema for a specific plugin
a6 plugin get key-auth --output json
a6 plugin get limit-count --output json
```

## Building Your First API

### Step 1: Create an upstream (your backend)

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "my-api-backend",
  "type": "roundrobin",
  "nodes": {
    "localhost:3000": 1
  }
}
EOF
```

### Step 2: Create a route

```bash
a6 route create -f - <<'EOF'
{
  "id": "my-api",
  "uri": "/api/*",
  "methods": ["GET", "POST", "PUT", "DELETE"],
  "upstream_id": "my-api-backend"
}
EOF
```

### Step 3: Test it

```bash
curl http://localhost:9080/api/hello
```

### Step 4: Add authentication

```bash
# Create a consumer with key-auth
a6 consumer create -f - <<'EOF'
{
  "username": "dev-user",
  "plugins": {
    "key-auth": { "key": "my-dev-key" }
  }
}
EOF

# Enable key-auth on the route
a6 route update my-api -f - <<'EOF'
{
  "plugins": {
    "key-auth": {}
  }
}
EOF

# Test with the key
curl -H "apikey: my-dev-key" http://localhost:9080/api/hello
```

## Plugin Selection Guide

Use this decision tree to choose the right plugins for your API.

### Authentication — "Who is calling?"

| Need | Plugin | Key Feature |
|------|--------|-------------|
| Simple API key | `key-auth` | Header/query param key lookup |
| JWT tokens | `jwt-auth` | RS256/HS256, token in header/query/cookie |
| Username/password | `basic-auth` | HTTP Basic authentication |
| HMAC signatures | `hmac-auth` | Request body signing, replay prevention |
| OAuth2/OIDC | `openid-connect` | Auth0, Okta, Keycloak integration |

### Rate Limiting — "How much can they call?"

| Need | Plugin | Key Feature |
|------|--------|-------------|
| Fixed window counter | `limit-count` | N requests per time window, Redis cluster support |
| Leaky bucket | `limit-req` | Smooth rate limiting, burst allowance |

### Transformation — "Change request/response"

| Need | Plugin | Key Feature |
|------|--------|-------------|
| Rewrite URI/headers | `proxy-rewrite` | Strip prefixes, add headers, change host |
| Modify response | `response-rewrite` | Change status code, body, headers |
| A/B testing, canary | `traffic-split` | Weighted routing, conditional matching |
| URL redirect | `redirect` | HTTP 301/302/307 redirects |

### Security — "Block bad traffic"

| Need | Plugin | Key Feature |
|------|--------|-------------|
| IP whitelist/blacklist | `ip-restriction` | CIDR support, allow/deny lists |
| CORS headers | `cors` | Cross-origin resource sharing |
| Access control | `consumer-restriction` | Restrict by consumer, group, or route |

### Observability — "What's happening?"

| Need | Plugin | Key Feature |
|------|--------|-------------|
| Metrics | `prometheus` | Latency, status codes, bandwidth |
| Distributed tracing | `zipkin` or `skywalking` | Request trace correlation |
| Access logs | `http-logger` or `kafka-logger` | Structured log export |

## Common Patterns

### API with auth + rate limiting

```bash
a6 route create -f - <<'EOF'
{
  "uri": "/api/*",
  "upstream_id": "my-api-backend",
  "plugins": {
    "key-auth": {},
    "limit-count": {
      "count": 1000,
      "time_window": 3600,
      "key_type": "var",
      "key": "consumer_name",
      "rejected_code": 429
    }
  }
}
EOF
```

### Strip version prefix

```bash
a6 route create -f - <<'EOF'
{
  "uri": "/v1/*",
  "upstream_id": "my-api-backend",
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/v1/(.*)", "/$1"]
    }
  }
}
EOF
```

### Add CORS for frontend apps

```bash
a6 route update my-api -f - <<'EOF'
{
  "plugins": {
    "cors": {
      "allow_origins": "http://localhost:3001",
      "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
      "allow_headers": "Authorization,Content-Type",
      "allow_credential": true,
      "max_age": 3600
    }
  }
}
EOF
```

### Use a Service for shared config

When multiple routes share the same upstream and plugins, use a Service:

```bash
# Create service with shared config
a6 service create -f - <<'EOF'
{
  "id": "my-api-service",
  "upstream_id": "my-api-backend",
  "plugins": {
    "key-auth": {},
    "cors": { "allow_origins": "*" }
  }
}
EOF

# Routes inherit service config
a6 route create -f - <<'EOF'
{ "uri": "/users/*", "service_id": "my-api-service" }
EOF

a6 route create -f - <<'EOF'
{ "uri": "/orders/*", "service_id": "my-api-service" }
EOF
```

## Local Development Setup

### Start APISIX locally with Docker

```bash
# If using the a6 repo's docker-compose
make docker-up

# Or manually
docker run -d --name etcd \
  -p 2379:2379 \
  -e ALLOW_NONE_AUTHENTICATION=yes \
  bitnami/etcd:3.5

docker run -d --name apisix \
  -p 9080:9080 -p 9180:9180 \
  -v $(pwd)/apisix-config.yaml:/usr/local/apisix/conf/config.yaml \
  apache/apisix:3.11.0-debian
```

### Seed development data

```bash
# Create your dev config file
cat > dev-config.yaml <<'EOF'
upstreams:
  - id: local-backend
    type: roundrobin
    nodes:
      "host.docker.internal:3000": 1

consumers:
  - username: dev

routes:
  - id: api
    uri: "/api/*"
    upstream_id: local-backend
    plugins:
      key-auth: {}
EOF

# Apply it
a6 config sync -f dev-config.yaml
```

Create authentication data as a separate credential resource. Save the
following as `dev-credential.yaml`:

```yaml
id: dev-key-auth
plugins:
  key-auth:
    key: dev-key
```

```bash
a6 credential create --consumer dev -f dev-credential.yaml
```

## Debugging

### Trace a request

```bash
# See how APISIX routes a specific request
a6 debug trace api --path /api/users --method GET --header "apikey: dev-key"
```

### Stream logs

```bash
# Watch APISIX container logs in real-time
a6 debug logs --follow
```

### Inspect a route's full config

```bash
# See the merged config (route + service + plugins)
a6 route get my-api --output json | jq .
```

## CI/CD Integration

### Validate in CI

```yaml
# .github/workflows/apisix.yml
- name: Validate APISIX config
  run: a6 config validate -f apisix-config.yaml
```

### Deploy with config sync

```yaml
- name: Deploy to staging
  run: |
    a6 context create staging --server ${{ secrets.STAGING_URL }} --api-key ${{ secrets.STAGING_KEY }}
    a6 context use staging
    a6 config diff -f apisix-config.yaml
    a6 config sync -f apisix-config.yaml
```

### Export the current configuration

`a6 config dump` does not export Consumer Credential subresources. Keep the
credential files in your secure deployment workflow and restore them separately.

```bash
a6 config dump --output yaml > apisix-backup.yaml
```

## Decision Framework

| Situation | Action |
|-----------|--------|
| New API endpoint | Create upstream → create route → add plugins → test |
| Add auth to existing API | Create consumer → update route with auth plugin → test |
| Multiple routes, same config | Create a Service → reference via `service_id` |
| Need rate limiting | Choose `limit-count` (fixed) or `limit-req` (smooth) → add to route |
| Backend URL changed | `a6 upstream update <id>` with new nodes |
| Debug 502 errors | `a6 debug trace <route-id>` → `a6 upstream health` → check backend |
| Prepare for production | `a6 config dump` → commit to git → `a6 config validate` in CI |
| Test a new plugin | `a6 plugin get <name>` for schema → add to a test route → verify |

## Best Practices

1. **Use declarative configs** — store `apisix-config.yaml` in your repo, use
   `a6 config sync` for deployments instead of imperative commands
2. **One service per API** — group related routes under a Service for shared config
3. **Auth on every route** — never expose unauthenticated routes in production
4. **Rate limit by consumer** — use `key_type: "var"` with `key: "consumer_name"`
   for per-user limits
5. **Test locally first** — always test against a dev APISIX instance before deploying
6. **Inspect plugin schemas** — run `a6 plugin get <name>` to see required/optional
   fields before configuring
7. **Use `--output json`** — pipe JSON output to `jq` for scripting and automation
8. **Keep routes focused** — one route per endpoint pattern; avoid overly broad URI
   matchers like `/*` in production
