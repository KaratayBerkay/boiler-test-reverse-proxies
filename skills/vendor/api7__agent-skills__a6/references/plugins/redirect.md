---
title: "redirect plugin"
description: "Skill for configuring the Apache APISIX redirect plugin via the a6 CLI. Covers URI redirects, HTTP-to-HTTPS redirection, regex-based URI rewriting, query string handling, and common operational patterns."
metadata:
  category: plugin
  plugin_name: redirect
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 route get
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-redirect/SKILL.md
---
# redirect plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `redirect` plugin sends HTTP redirect responses (301, 302, etc.) to
clients. It can redirect to a new URI, enforce HTTPS, or use regex patterns
for complex path transformations. Unlike `proxy-rewrite` (which rewrites
before forwarding to upstream), this plugin returns a redirect response
directly to the client.

## When to Use

- Enforce HTTPS by redirecting all HTTP requests
- Redirect old URLs to new locations (301 permanent redirect)
- Pattern-based URI rewrites using regex capture groups
- Redirect to external domains
- Append or preserve query strings during redirects

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `http_to_https` | boolean | No | `false` | Redirect HTTP to HTTPS. Preserves URI and query string. Uses 301 status. |
| `uri` | string | No | — | Target redirect URI. Supports Nginx variables (`$uri`, `$host`, etc.). Can be absolute URL. |
| `regex_uri` | array[string] | No | — | Two-element array: `["regex_pattern", "replacement"]`. PCRE regex with capture groups. |
| `ret_code` | integer | No | `302` | HTTP status code for the redirect response. |
| `encode_uri` | boolean | No | `false` | Encode the URI in the Location header per RFC 3986. |
| `append_query_string` | boolean | No | `false` | Append the original request query string to the redirect Location. |

**Mutual exclusion**: Only ONE of `http_to_https`, `uri`, or `regex_uri` can be configured at a time.

**Note**: `http_to_https` and `append_query_string` cannot be used together (`http_to_https` already preserves query strings).

## HTTPS Port Selection (for http_to_https)

When `http_to_https` is true, the HTTPS port is determined by priority:

1. `plugin_attr.redirect.https_port` in `conf/config.yaml`
2. Random port from `apisix.ssl.listen` (if SSL configured)
3. Default: `443`

## Step-by-Step: Enable redirect on a Route

### 1. HTTP to HTTPS redirect

```bash
a6 route create -f - <<'EOF'
{
  "id": "force-https",
  "uri": "/*",
  "plugins": {
    "redirect": {
      "http_to_https": true
    }
  }
}
EOF
```

Result: `http://example.com/path?q=1` → `https://example.com/path?q=1` (301)

### 2. Simple URI redirect (moved permanently)

```bash
a6 route create -f - <<'EOF'
{
  "id": "old-to-new",
  "uri": "/old-page",
  "plugins": {
    "redirect": {
      "uri": "/new-page",
      "ret_code": 301
    }
  }
}
EOF
```

### 3. Regex-based redirect with capture groups

```bash
a6 route create -f - <<'EOF'
{
  "id": "regex-redirect",
  "uri": "/blog/*",
  "plugins": {
    "redirect": {
      "regex_uri": ["^/blog/(\\d{4})/(\\d{2})/(.*)$", "/articles/$1-$2-$3"],
      "ret_code": 301
    }
  }
}
EOF
```

Result: `/blog/2024/03/my-post` → `/articles/2024-03-my-post`

## Common Patterns

### Redirect to external domain

```json
{
  "plugins": {
    "redirect": {
      "uri": "https://new-domain.com/api/v2",
      "ret_code": 301
    }
  }
}
```

### Redirect with Nginx variables

```json
{
  "plugins": {
    "redirect": {
      "uri": "https://new-domain.com$request_uri",
      "ret_code": 301
    }
  }
}
```

Preserves the full original path and query string.

### Append trailing slash

```json
{
  "plugins": {
    "redirect": {
      "uri": "$uri/",
      "ret_code": 301
    }
  }
}
```

### Redirect with query string preservation

```json
{
  "plugins": {
    "redirect": {
      "uri": "/new-path",
      "append_query_string": true,
      "ret_code": 302
    }
  }
}
```

Request: `/old-path?foo=bar&baz=1` → Location: `/new-path?foo=bar&baz=1`

### Encode special characters in URI

```json
{
  "plugins": {
    "redirect": {
      "uri": "/path with spaces/resource",
      "encode_uri": true,
      "ret_code": 302
    }
  }
}
```

Location header: `/path%20with%20spaces/resource`

### Temporary redirect (302) for maintenance

```json
{
  "plugins": {
    "redirect": {
      "uri": "/maintenance.html",
      "ret_code": 302
    }
  }
}
```

Use 302 (temporary) so browsers don't cache the redirect.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Redirect loop | Route matches the redirect target | Ensure the target URI doesn't match the same route |
| Wrong HTTPS port | Default port selection | Set `plugin_attr.redirect.https_port` in config.yaml |
| Query string lost | Using `uri` without `append_query_string` | Add `"append_query_string": true` or use `$request_uri` |
| Duplicate query string | `append_query_string` with `$request_uri` | Don't combine both — `$request_uri` already includes query string |
| Nginx variable empty | Variable doesn't exist | Non-existent variables resolve to empty string (no error) |
| Regex not matching | Escaping or pattern issue | Escape backslashes in JSON: `\\d+`. Test regex with PCRE syntax. |
| Multiple redirect options set | `http_to_https`, `uri`, `regex_uri` are mutually exclusive | Use only ONE of the three options |

## Config Sync Example

```yaml
version: "1"
routes:
  - id: force-https
    uri: /*
    plugins:
      redirect:
        http_to_https: true
  - id: old-blog-redirect
    uri: /blog/*
    plugins:
      redirect:
        regex_uri:
          - "^/blog/(\\d{4})/(\\d{2})/(.*)"
          - "/articles/$1-$2-$3"
        ret_code: 301
```
