---
title: "canary recipe"
description: "Recipe skill for implementing canary releases using the a6 CLI. Covers gradual traffic shifting with the traffic-split plugin, header-based canary routing, weight adjustment progression, monitoring checkpoints, and full promotion or rollback workflows."
metadata:
  category: recipe
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 upstream create
    - a6 route create
    - a6 route update
    - a6 route get
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-recipe-canary/SKILL.md
---
# canary recipe

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

A canary release gradually shifts traffic from the stable version to a new
version. Start with a small percentage (e.g., 5%), monitor for errors, then
increase incrementally until the new version receives 100% of traffic. If
errors spike at any stage, roll back instantly.

This recipe uses the `traffic-split` plugin to manage weighted traffic
distribution between stable and canary upstreams.

## When to Use

- Deploy new versions with minimal blast radius
- Validate changes with real production traffic before full rollout
- You need gradual rollout with monitoring checkpoints
- You want automatic or scripted rollback on error detection

## Step-by-Step: Canary Release

### 1. Create stable and canary upstreams

```bash
a6 upstream create -f - <<'EOF'
{
  "id": "stable",
  "type": "roundrobin",
  "nodes": {
    "stable-v1:8080": 1
  }
}
EOF

a6 upstream create -f - <<'EOF'
{
  "id": "canary",
  "type": "roundrobin",
  "nodes": {
    "canary-v2:8080": 1
  }
}
EOF
```

### 2. Start canary at 5%

```bash
a6 route create -f - <<'EOF'
{
  "id": "api",
  "uri": "/api/*",
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream_id": "canary",
              "weight": 5
            },
            {
              "weight": 95
            }
          ]
        }
      ]
    }
  },
  "upstream_id": "stable"
}
EOF
```

### 3. Monitor and increase to 25%

Check error rates, latency, and logs. If healthy:

```bash
a6 route update api -f - <<'EOF'
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream_id": "canary",
              "weight": 25
            },
            {
              "weight": 75
            }
          ]
        }
      ]
    }
  }
}
EOF
```

### 4. Increase to 50%

```bash
a6 route update api -f - <<'EOF'
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "weighted_upstreams": [
            {
              "upstream_id": "canary",
              "weight": 50
            },
            {
              "weight": 50
            }
          ]
        }
      ]
    }
  }
}
EOF
```

### 5. Promote to 100% (complete the rollout)

Remove traffic-split and switch to canary as the new stable:

```bash
a6 route update api -f - <<'EOF'
{
  "plugins": {},
  "upstream_id": "canary"
}
EOF
```

Then update the "stable" upstream nodes to the new version for next time:

```bash
a6 upstream update stable -f - <<'EOF'
{
  "nodes": {
    "canary-v2:8080": 1
  }
}
EOF
```

## Rollback (at any stage)

Remove the traffic-split plugin to send all traffic back to stable:

```bash
a6 route update api -f - <<'EOF'
{
  "plugins": {},
  "upstream_id": "stable"
}
EOF
```

## Advanced: Header-Based Canary

Route specific users (e.g., internal testers) to the canary version:

```bash
a6 route update api -f - <<'EOF'
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [
            {
              "vars": [["http_x-canary", "==", "true"]]
            }
          ],
          "weighted_upstreams": [
            {
              "upstream_id": "canary",
              "weight": 1
            }
          ]
        }
      ]
    }
  },
  "upstream_id": "stable"
}
EOF
```

Only requests with header `x-canary: true` go to the canary. All others stay on stable.

## Advanced: Cookie-Based Canary

Route users who opted into beta:

```json
{
  "plugins": {
    "traffic-split": {
      "rules": [
        {
          "match": [
            {
              "vars": [["cookie_beta", "==", "1"]]
            }
          ],
          "weighted_upstreams": [
            {
              "upstream_id": "canary",
              "weight": 1
            }
          ]
        }
      ]
    }
  }
}
```

## Canary Progression Script

```bash
#!/bin/bash
set -euo pipefail

ROUTE_ID="api"
CANARY_UPSTREAM="canary"
WEIGHTS=(5 25 50 75 100)
HEALTH_URL="http://gateway:9080/api/health"
WAIT_SECONDS=300  # 5 minutes between stages

for w in "${WEIGHTS[@]}"; do
  if [ "$w" -eq 100 ]; then
    echo "Promoting canary to 100%..."
    a6 route update "$ROUTE_ID" -f - <<EOF
{"plugins": {}, "upstream_id": "$CANARY_UPSTREAM"}
EOF
  else
    stable_w=$((100 - w))
    echo "Setting canary to ${w}% (stable ${stable_w}%)..."
    a6 route update "$ROUTE_ID" -f - <<EOF
{
  "plugins": {
    "traffic-split": {
      "rules": [{
        "weighted_upstreams": [
          {"upstream_id": "$CANARY_UPSTREAM", "weight": $w},
          {"weight": $stable_w}
        ]
      }]
    }
  }
}
EOF
  fi

  echo "Waiting ${WAIT_SECONDS}s and checking health..."
  sleep "$WAIT_SECONDS"

  if ! curl -sf "$HEALTH_URL" > /dev/null; then
    echo "❌ Health check failed at ${w}%. Rolling back."
    a6 route update "$ROUTE_ID" -f - <<EOF
{"plugins": {}, "upstream_id": "stable"}
EOF
    exit 1
  fi
  echo "✅ Healthy at ${w}%"
done

echo "🎉 Canary release complete!"
```

## Config Sync Example

```yaml
version: "1"
upstreams:
  - id: stable
    type: roundrobin
    nodes:
      "stable-v1:8080": 1
  - id: canary
    type: roundrobin
    nodes:
      "canary-v2:8080": 1
routes:
  - id: api
    uri: /api/*
    plugins:
      traffic-split:
        rules:
          - weighted_upstreams:
              - upstream_id: canary
                weight: 10
              - weight: 90
    upstream_id: stable
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Traffic ratio not exact | Round-robin approximation | Expected; ratios converge over many requests |
| Canary not receiving traffic | Match condition never true | Check header/cookie name; use `a6 route get` to verify config |
| Rollback not instant | Plugin config cached | APISIX updates propagate via etcd in milliseconds — verify with `a6 route get` |
| 502 errors from canary | Canary upstream not healthy | Check canary service health before starting rollout |
| Weight changes have no effect | Editing wrong route | Verify route ID with `a6 route list` |
