---
title: "blue green recipe"
description: "Recipe skill for implementing blue-green deployments using the a6 CLI. Covers creating two upstream environments, switching traffic instantly via route updates or traffic-split plugin, rollback procedures, and config sync workflows for declarative blue-green management."
metadata:
  category: recipe
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 upstream create
    - a6 upstream update
    - a6 route create
    - a6 route update
    - a6 config sync
    - a6 config diff
  source: https://github.com/api7/a6/blob/main/skills/a6-recipe-blue-green/SKILL.md
---
# blue green recipe

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

Blue-green deployment runs two identical production environments (blue and
green). At any time, only one serves live traffic. Deploy the new version to
the idle environment, test it, then switch traffic instantly. If anything
goes wrong, switch back.

This recipe implements blue-green deployment using APISIX routes and upstreams
managed by the a6 CLI.

## When to Use

- Zero-downtime deployments with instant rollback
- You have two identical environments that can be swapped
- You want to test the new version with internal traffic before switching
- You need an auditable, scriptable deployment process

## Approach A: Upstream Swap (Simplest)

Switch traffic by updating the route's `upstream_id` to point at the other
environment.

### 1. Create both upstreams

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "blue",
  "type": "roundrobin",
  "nodes": {
    "blue-backend-1:8080": 1,
    "blue-backend-2:8080": 1
  }
}
EOF

a6 upstream create -f - <<'EOF'
{
  "id": "green",
  "type": "roundrobin",
  "nodes": {
    "green-backend-1:8080": 1,
    "green-backend-2:8080": 1
  }
}
EOF
```

### 2. Create route pointing to blue

```bash
a6 route create -f - <<'EOF'
{
  "id": "api",
  "uri": "/api/*",
  "upstream_id": "blue"
}
EOF
```

### 3. Deploy new version to green, test it

Deploy your new version to the green environment. Test internally.

### 4. Switch to green

```bash
a6 route update api -f - <<'EOF'
{
  "upstream_id": "green"
}
EOF
```

Traffic switches instantly. No downtime.

### 5. Rollback to blue (if needed)

```bash
a6 route update api -f - <<'EOF'
{
  "upstream_id": "blue"
}
EOF
```

## Approach B: Traffic-Split Plugin (Header-Based Testing)

Use the `traffic-split` plugin to test the green environment with specific
headers before full switch.

### 1. Create route with traffic-split

```bash
a6 route create -f - <<'EOF'
{
  "id": "api",
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [
            {
              "vars": [["http_x-env", "==", "green"]]
            }
          ],
          "weighted_upstreams": [
            {
              "upstream_id": "green",
              "weight": 1
            }
          ]
        }
      ]
    }
  },
  "upstream_id": "blue"
}
EOF
```

### 2. Test green internally

```bash
curl -H "x-env: green" http://gateway:9080/api/health
```

### 3. Full switch — remove traffic-split, swap upstream

```bash
a6 route update api -f - <<'EOF'
{
  "plugins": {},
  "upstream_id": "green"
}
EOF
```

## Approach C: Config Sync (Declarative)

### config.yaml — Blue active

```yaml
version: "1"
upstreams:
  - id: blue
    type: roundrobin
    nodes:
      "blue-backend-1:8080": 1
      "blue-backend-2:8080": 1
  - id: green
    type: roundrobin
    nodes:
      "green-backend-1:8080": 1
      "green-backend-2:8080": 1
routes:
  - id: api
    uri: /api/*
    upstream_id: blue  # ← change to "green" to switch
```

### Preview changes before switching

```bash
# Edit config.yaml: change upstream_id to "green"
a6 config diff -f config.yaml
```

### Apply the switch

```bash
a6 config sync -f config.yaml
```

## Deployment Script Example

```bash
#!/bin/bash
set -euo pipefail

CURRENT=$(a6 route get api -o json | jq -r '.upstream_id')
TARGET=$([ "$CURRENT" = "blue" ] && echo "green" || echo "blue")

echo "Current: $CURRENT → Switching to: $TARGET"

# Switch
a6 route update api -f - <<EOF
{"upstream_id": "$TARGET"}
EOF

echo "Switched to $TARGET. Verifying..."

# Health check
if curl -sf http://gateway:9080/api/health > /dev/null; then
  echo "✅ $TARGET is healthy"
else
  echo "❌ $TARGET unhealthy, rolling back to $CURRENT"
  a6 route update api -f - <<EOF
{"upstream_id": "$CURRENT"}
EOF
  exit 1
fi
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 502 after switch | New environment not ready | Test health endpoint before switching; rollback if needed |
| Traffic still going to old env | Route cache or DNS | APISIX routes update instantly via etcd — verify with `a6 route get` |
| Can't rollback | Lost track of previous upstream | Always record current state before switching |
| Connections drop during switch | Long-running requests on old upstream | APISIX handles in-flight requests gracefully; existing connections complete |
