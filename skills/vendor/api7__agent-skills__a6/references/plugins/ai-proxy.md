---
title: "ai-proxy plugin"
description: "Skill for configuring the Apache APISIX ai-proxy plugin via the a6 CLI. Covers proxying requests to LLM providers (OpenAI, Azure OpenAI, DeepSeek, Anthropic, Gemini, Vertex AI, Amazon Bedrock, and more), authentication per provider, model configuration, streaming, logging, and load balancing with ai-proxy-multi."
metadata:
  category: plugin
  plugin_name: ai-proxy
  apisix_version: ">=3.9.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-ai-proxy/SKILL.md
---
# ai-proxy plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `ai-proxy` plugin turns APISIX into an AI gateway. Clients can send
requests in supported protocols to APISIX instead of handling provider
authentication and endpoint selection themselves. The plugin detects the
client protocol, selects a compatible provider endpoint, forwards the native
format or converts it when an adapter is available, and handles response
streaming.

## When to Use

- Proxy Chat Completions, Responses API, Embeddings, Anthropic Messages, or
  Bedrock Converse requests to a compatible provider
- Centralize API keys at the gateway instead of distributing to clients
- Add observability (token counts, latency) to LLM calls
- Combine with `ai-prompt-template`, `ai-prompt-decorator`, or content
  moderation plugins for a full AI gateway pipeline

## Protocol Detection

APISIX uses the request URI as part of protocol detection. Anthropic Messages
requests must use a URI ending in `/v1/messages`, and Bedrock Converse requests
must use a URI ending in `/converse`. Without these suffixes, a request body can
match another protocol, such as OpenAI Chat.

OpenAI Responses requests with an `input` field must use a URI ending in
`/v1/responses`. Otherwise, APISIX detects the body as OpenAI Embeddings; use a
URI ending in `/v1/embeddings` for embedding routes.

For Bedrock streaming, keep the client-facing URI ending in `/converse` and set
`stream: true` in the request body. APISIX then selects the upstream
`/model/{modelId}/converse-stream` endpoint.

## Supported Providers

| Provider | Value | Endpoint Behavior |
|----------|-------|-------------------|
| OpenAI | `openai` | Automatically selects `/v1/chat/completions`, `/v1/responses`, or `/v1/embeddings` on `https://api.openai.com` |
| DeepSeek | `deepseek` | `https://api.deepseek.com/chat/completions` |
| Azure OpenAI | `azure-openai` | Custom via `override.endpoint` |
| Anthropic | `anthropic` | Automatically selects `/v1/chat/completions` or `/v1/messages` on `https://api.anthropic.com` |
| AIMLAPI | `aimlapi` | `https://api.aimlapi.com/v1/chat/completions` |
| OpenRouter | `openrouter` | `https://openrouter.ai/api/v1/chat/completions` |
| Gemini | `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` |
| Vertex AI | `vertex-ai` | `https://aiplatform.googleapis.com` |
| Amazon Bedrock | `bedrock` | Region- and model-specific Bedrock Runtime endpoint; available from APISIX 3.17.0 |
| OpenAI-Compatible | `openai-compatible` | Custom via `override.endpoint` |

## Plugin Configuration Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | string | **Yes** | — | One of the 10 supported providers |
| `auth` | object | **Yes** | — | Authentication config (see below) |
| `options` | object | No | — | Model and generation parameters |
| `options.model` | string | No | — | Model name (provider-specific) |
| `options.temperature` | number | No | — | Sampling temperature |
| `options.top_p` | number | No | — | Nucleus sampling |
| `options.max_tokens` | integer | No | — | Maximum tokens to generate |
| `options.stream` | boolean | No | — | Override the outgoing `stream` field. For Bedrock Converse, `stream: true` on a `/converse` request selects `/model/{modelId}/converse-stream` and returns unmodified AWS EventStream binary frames with `Content-Type: application/vnd.amazon.eventstream`, not SSE; clients must parse EventStream responses. |
| `override` | object | No | — | Provider endpoint and request-body override settings |
| `override.endpoint` | string | No | — | Provider scheme and host, or a full URL including the path and query |
| `provider_conf` | object | No | — | Provider-specific config for Vertex AI or Amazon Bedrock |
| `provider_conf.project_id` | string | No | — | GCP project ID for Vertex AI; required with `region` unless `override.endpoint` is configured |
| `provider_conf.region` | string | No | — | GCP region for Vertex AI; required AWS region for Amazon Bedrock |
| `logging` | object | No | — | Logging options |
| `logging.summaries` | boolean | No | `false` | Log model, duration, tokens |
| `logging.payloads` | boolean | No | `false` | Log request/response bodies |
| `timeout` | integer | No | `30000` | Request timeout (ms) |
| `keepalive` | boolean | No | `true` | Keep connection alive |
| `keepalive_timeout` | integer | No | `60000` | Keepalive timeout (ms) |
| `keepalive_pool` | integer | No | `30` | Keepalive pool size |
| `ssl_verify` | boolean | No | `true` | Verify SSL certificate |

## Authentication by Provider

### OpenAI / DeepSeek / AIMLAPI / OpenRouter

```json
{
  "auth": {
    "header": {
      "Authorization": "Bearer sk-your-api-key"
    }
  }
}
```

### Anthropic

```json
{
  "auth": {
    "header": {
      "x-api-key": "your-anthropic-api-key",
      "anthropic-version": "2023-06-01"
    }
  }
}
```

Native Anthropic Messages requests require an `anthropic-version` header.
Configure it in `auth.header`, as shown, or require clients to send it.

### Azure OpenAI

```json
{
  "auth": {
    "header": {
      "api-key": "your-azure-key"
    }
  },
  "override": {
    "endpoint": "https://YOUR-RESOURCE.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-02-15-preview"
  }
}
```

### Gemini

```json
{
  "auth": {
    "header": {
      "Authorization": "Bearer your-gemini-key"
    }
  }
}
```

### Vertex AI (GCP Service Account)

```json
{
  "auth": {
    "gcp": {
      "service_account_json": "{ ... }",
      "max_ttl": 3600,
      "expire_early_secs": 60
    }
  },
  "provider_conf": {
    "project_id": "your-project-id",
    "region": "us-central1"
  }
}
```

The `service_account_json` can also be set via the `GCP_SERVICE_ACCOUNT`
environment variable.

### Amazon Bedrock

```json
{
  "auth": {
    "aws": {
      "access_key_id": "your-access-key-id",
      "secret_access_key": "your-secret-access-key",
      "session_token": "your-session-token"
    }
  },
  "provider_conf": {
    "region": "us-east-1"
  },
  "options": {
    "model": "your-model-id"
  }
}
```

The session token is required when you use temporary AWS credentials.

### Custom OpenAI-Compatible API

```json
{
  "auth": {
    "header": {
      "Authorization": "Bearer your-token"
    }
  },
  "override": {
    "endpoint": "https://your-custom-llm.com/v1/chat/completions"
  }
}
```

## Step-by-Step: Route to OpenAI

### 1. Create a route with ai-proxy

```bash
a6 route create -f - <<'EOF'
{
  "id": "openai-chat",
  "uri": "/v1/chat/completions",
  "methods": ["POST"],
  "plugins": {
    "ai-proxy": {
      "provider": "openai",
      "auth": {
        "header": {
          "Authorization": "Bearer sk-your-openai-key"
        }
      },
      "options": {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1024
      }
    }
  }
}
EOF
```

### 2. Send a request

```bash
curl http://127.0.0.1:9080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is 1+1?"}
    ]
  }'
```

The gateway adds authentication and forwards to OpenAI. The client never
sees the API key.

## Common Patterns

### Streaming responses

```json
{
  "plugins": {
    "ai-proxy": {
      "provider": "openai",
      "auth": {
        "header": {
          "Authorization": "Bearer sk-your-key"
        }
      },
      "options": {
        "model": "gpt-4",
        "stream": true
      }
    }
  }
}
```

The client receives Server-Sent Events (SSE). To get token counts in
streaming mode, the client should include `stream_options.include_usage: true`
in the request body.

### Azure OpenAI

```json
{
  "plugins": {
    "ai-proxy": {
      "provider": "azure-openai",
      "auth": {
        "header": {
          "api-key": "your-azure-key"
        }
      },
      "options": {
        "model": "gpt-4"
      },
      "override": {
        "endpoint": "https://myresource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2024-02-15-preview"
      },
      "timeout": 60000
    }
  }
}
```

### Embeddings endpoint

```bash
a6 route create -f - <<'EOF'
{
  "id": "embeddings",
  "uri": "/v1/embeddings",
  "methods": ["POST"],
  "plugins": {
    "ai-proxy": {
      "provider": "openai",
      "auth": {
        "header": {
          "Authorization": "Bearer sk-your-key"
        }
      },
      "options": {
        "model": "text-embedding-3-small"
      },
      "override": {
        "endpoint": "https://api.openai.com/v1/embeddings"
      }
    }
  }
}
EOF
```

### Enable logging

```json
{
  "plugins": {
    "ai-proxy": {
      "provider": "openai",
      "auth": {
        "header": {
          "Authorization": "Bearer sk-your-key"
        }
      },
      "options": {
        "model": "gpt-4"
      },
      "logging": {
        "summaries": true,
        "payloads": false
      }
    }
  }
}
```

## Model Routing with Multiple Routes

The plugin does not natively route by model. Use separate routes with `vars`
matching on request body fields:

```bash
# Route requests for gpt-4 to OpenAI
a6 route create -f - <<'EOF'
{
  "id": "openai-gpt4",
  "uri": "/v1/chat/completions",
  "methods": ["POST"],
  "vars": [["post_arg.model", "==", "gpt-4"]],
  "plugins": {
    "ai-proxy": {
      "provider": "openai",
      "auth": { "header": { "Authorization": "Bearer sk-openai-key" } },
      "options": { "model": "gpt-4" }
    }
  }
}
EOF

# Route requests for deepseek-chat to DeepSeek
a6 route create -f - <<'EOF'
{
  "id": "deepseek-chat",
  "uri": "/v1/chat/completions",
  "methods": ["POST"],
  "vars": [["post_arg.model", "==", "deepseek-chat"]],
  "plugins": {
    "ai-proxy": {
      "provider": "deepseek",
      "auth": { "header": { "Authorization": "Bearer sk-deepseek-key" } },
      "options": { "model": "deepseek-chat" }
    }
  }
}
EOF
```

## Load Balancing with ai-proxy-multi

For load balancing, failover, and priority-based routing across providers,
use `ai-proxy-multi` instead:

```json
{
  "plugins": {
    "ai-proxy-multi": {
      "balancer": {
        "algorithm": "roundrobin"
      },
      "fallback_strategy": ["rate_limiting", "http_429", "http_5xx"],
      "instances": [
        {
          "name": "openai-primary",
          "provider": "openai",
          "priority": 1,
          "weight": 8,
          "auth": {
            "header": { "Authorization": "Bearer sk-openai-key" }
          },
          "options": { "model": "gpt-4" }
        },
        {
          "name": "deepseek-backup",
          "provider": "deepseek",
          "priority": 0,
          "weight": 2,
          "auth": {
            "header": { "Authorization": "Bearer sk-deepseek-key" }
          },
          "options": { "model": "deepseek-chat" }
        }
      ]
    }
  }
}
```

## Access Log Variables

Configure APISIX to log LLM metrics:

| Variable | Description |
|----------|-------------|
| `$request_type` | `traditional_http`, `ai_chat`, or `ai_stream` |
| `$llm_time_to_first_token` | Time to first token (ms) |
| `$llm_model` | Actual model used by provider |
| `$request_llm_model` | Model requested by client |
| `$llm_prompt_tokens` | Prompt token count |
| `$llm_completion_tokens` | Completion token count |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: openai-chat
    uri: /v1/chat/completions
    methods:
      - POST
    plugins:
      ai-proxy:
        provider: openai
        auth:
          header:
            Authorization: Bearer sk-your-openai-key
        options:
          model: gpt-4
          max_tokens: 1024
          temperature: 0.7
        logging:
          summaries: true
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 502 Bad Gateway | Wrong endpoint or provider value | Verify `provider` matches your API; check `override.endpoint` for Azure/custom |
| 401 from upstream | Invalid API key | Check `auth.header` value; ensure key is active with the provider |
| Timeout errors | Slow LLM response | Increase `timeout` (default 30000ms); use streaming for long completions |
| No token counts in streaming | Missing stream_options | Client should send `stream_options.include_usage: true` |
| Azure 404 | Missing api-version in URL | Include `?api-version=YYYY-MM-DD-preview` in `override.endpoint` |
| Vertex AI auth failure | Bad service account JSON | Set via `auth.gcp.service_account_json` or `GCP_SERVICE_ACCOUNT` env var |
