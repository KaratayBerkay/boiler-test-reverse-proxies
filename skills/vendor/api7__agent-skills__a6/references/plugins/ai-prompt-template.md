---
title: "ai-prompt-template plugin"
description: "Skill for configuring the Apache APISIX ai-prompt-template plugin via the a6 CLI. Covers defining reusable prompt templates with variable placeholders, enforcing prompt structure, accepting user inputs for specific fields only, and combining with ai-proxy for a complete AI gateway pipeline."
metadata:
  category: plugin
  plugin_name: ai-prompt-template
  apisix_version: ">=3.9.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-ai-prompt-template/SKILL.md
---
# ai-prompt-template plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `ai-prompt-template` plugin pre-configures prompt templates with
`{{variable}}` placeholders. Clients submit only the template name and
variable values; the plugin fills the template and produces a complete
chat-completion request. This enforces prompt structure and prevents
clients from sending arbitrary system prompts.

**Priority**: 1071 (runs before `ai-prompt-decorator` at 1070 and
`ai-proxy` at 1040).

## When to Use

- Enforce a fixed prompt structure across all clients
- Accept user inputs only for specific fields (fill-in-the-blank)
- Prevent prompt injection by controlling the system message
- Build prompt libraries that clients select by name

## Plugin Configuration Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `templates` | array | **Yes** | Array of template objects (min 1) |
| `templates[].name` | string | **Yes** | Template identifier (min length 1) |
| `templates[].template` | object | **Yes** | Template specification |
| `templates[].template.model` | string | **Yes** | AI model name |
| `templates[].template.messages` | array | **Yes** | Array of message objects (min 1) |
| `templates[].template.messages[].role` | string | **Yes** | `system`, `user`, or `assistant` |
| `templates[].template.messages[].content` | string | **Yes** | Prompt content with `{{variable}}` placeholders |

## Template Variable Syntax

Use double curly braces: `{{variable_name}}`

Variables are replaced by matching keys in the client request body. The
plugin uses the `body-transformer` plugin internally for substitution.

## Client Request Format

Instead of sending a standard `messages` array, clients send:

```json
{
  "template_name": "my-template",
  "variable1": "value1",
  "variable2": "value2"
}
```

The plugin looks up the template by name, fills in the variables, and
produces a complete chat-completion request body.

## Step-by-Step: Create a Templated Route

### 1. Create a route with ai-prompt-template and ai-proxy

```bash
a6 route create -f - <<'EOF'
{
  "id": "templated-chat",
  "uri": "/v1/chat/completions",
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
        "model": "gpt-4"
      }
    },
    "ai-prompt-template": {
      "templates": [
        {
          "name": "code-review",
          "template": {
            "model": "gpt-4",
            "messages": [
              {
                "role": "system",
                "content": "You are an expert {{language}} code reviewer. Review the code for bugs, performance issues, and style."
              },
              {
                "role": "user",
                "content": "Review this code:\n\n{{code}}"
              }
            ]
          }
        }
      ]
    }
  }
}
EOF
```

### 2. Send a request with template variables

```bash
curl http://127.0.0.1:9080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "code-review",
    "language": "Python",
    "code": "def add(a, b): return a + b"
  }'
```

### 3. What the plugin sends to OpenAI

```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Python code reviewer. Review the code for bugs, performance issues, and style."
    },
    {
      "role": "user",
      "content": "Review this code:\n\ndef add(a, b): return a + b"
    }
  ]
}
```

## Common Patterns

### Multiple templates on one route

```json
{
  "plugins": {
    "ai-prompt-template": {
      "templates": [
        {
          "name": "translate",
          "template": {
            "model": "gpt-4",
            "messages": [
              {
                "role": "system",
                "content": "Translate the following text from {{source_lang}} to {{target_lang}}. Return only the translation."
              },
              {
                "role": "user",
                "content": "{{text}}"
              }
            ]
          }
        },
        {
          "name": "summarize",
          "template": {
            "model": "gpt-4",
            "messages": [
              {
                "role": "system",
                "content": "Summarize the following text in {{style}} style, using at most {{max_sentences}} sentences."
              },
              {
                "role": "user",
                "content": "{{text}}"
              }
            ]
          }
        }
      ]
    }
  }
}
```

Clients select the template by name:

```bash
# Translation
curl http://127.0.0.1:9080/v1/chat/completions \
  -d '{"template_name":"translate","source_lang":"English","target_lang":"Chinese","text":"Hello world"}'

# Summarization
curl http://127.0.0.1:9080/v1/chat/completions \
  -d '{"template_name":"summarize","style":"concise","max_sentences":"3","text":"Long article..."}'
```

### Combining with ai-prompt-decorator

The pipeline executes in priority order:

1. `ai-prompt-template` (1071) — fills variables
2. `ai-prompt-decorator` (1070) — prepends/appends messages
3. `ai-proxy` (1040) — sends to LLM

```json
{
  "plugins": {
    "ai-prompt-template": {
      "templates": [
        {
          "name": "qa",
          "template": {
            "model": "gpt-4",
            "messages": [
              {"role": "user", "content": "{{question}}"}
            ]
          }
        }
      ]
    },
    "ai-prompt-decorator": {
      "prepend": [
        {"role": "system", "content": "Be concise and factual."}
      ],
      "append": [
        {"role": "system", "content": "Cite sources if possible."}
      ]
    },
    "ai-proxy": {
      "provider": "openai",
      "auth": {
        "header": {"Authorization": "Bearer sk-your-key"}
      }
    }
  }
}
```

## Config Sync Example

```yaml
version: "1"
routes:
  - id: templated-chat
    uri: /v1/chat/completions
    methods:
      - POST
    plugins:
      ai-proxy:
        provider: openai
        auth:
          header:
            Authorization: Bearer sk-your-key
        options:
          model: gpt-4
      ai-prompt-template:
        templates:
          - name: code-review
            template:
              model: gpt-4
              messages:
                - role: system
                  content: "You are an expert {{language}} code reviewer."
                - role: user
                  content: "Review this code:\n\n{{code}}"
          - name: explain
            template:
              model: gpt-4
              messages:
                - role: system
                  content: "Explain {{topic}} at a {{level}} level."
                - role: user
                  content: "{{question}}"
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 400 "template not found" | `template_name` doesn't match any configured template | Check spelling; names are case-sensitive |
| Unfilled `{{variable}}` in output | Variable key missing from request body | Include all template variables in the request JSON |
| Plugin not transforming | Wrong plugin name or misconfigured | Verify plugin name is `ai-prompt-template` (not `prompt-template`) |
| Conflict with direct messages | Client sends both `template_name` and `messages` | Use only `template_name` + variables; the plugin replaces the entire body |
