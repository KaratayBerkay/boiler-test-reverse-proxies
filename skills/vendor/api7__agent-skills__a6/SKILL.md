---
name: a6
description: >-
  Configure and operate the open-source Apache APISIX gateway through the a6 CLI. Use whenever the
  user wants to create, inspect, change, or delete APISIX routes, services, upstreams, consumers,
  credentials, SSL certificates, global rules, or plugins (ai-content-moderation,
  ai-prompt-decorator, ai-prompt-template, ai-proxy, basic-auth, consumer-restriction, cors,
  datadog, ext-plugin, fault-injection, grpc-transcode, hmac-auth, http-logger, ip-restriction,
  jwt-auth, kafka-logger, key-auth, limit-count, limit-req, openid-connect, prometheus,
  proxy-rewrite, redirect, response-rewrite, serverless, skywalking, traffic-split, wolf-rbac,
  zipkin), or run a workflow such as api-versioning, blue-green, canary, circuit-breaker,
  graphql-proxy, health-check, mtls, multi-tenant. Includes developer and platform-operator
  personas and the a6 command conventions.
version: "2.0.0"
license: Apache-2.0
metadata:
  author: Apache APISIX Contributors
  cli: a6
  cli_repo: https://github.com/api7/a6
  product: Apache APISIX
  apisix_version: ">=3.0.0"
  references: 40
---

# a6 — Apache APISIX agent skill

`a6` is the command-line tool for Apache APISIX. It wraps the APISIX Admin API.
This skill is a router: it tells you which reference file to read for the task at hand. Read only what the task needs.

## 1. Always start here

Read [references/shared.md](references/shared.md) once per session before running any `a6` command. It covers the noun-verb command pattern, output formats, context/authentication handling, resource types, and the declarative `a6 config sync` workflow. Every other reference assumes it.

## 2. Pick the reference for the task

Match the user's request against the tables below and read the linked file. The tables are generated from `references/index.json`; edit that file, not the tables. Load one plugin or recipe file at a time; add a second only when the task clearly spans both (for example key-auth + limit-count).

<!-- routing-tables:start (generated from references/index.json by scripts/sync-router.mjs; do not edit by hand) -->

### Plugins (29)

| Plugin | Reference | Covers |
|---|---|---|
| `ai-aws-content-moderation` | [plugins/ai-content-moderation.md](references/plugins/ai-content-moderation.md) | AWS and Aliyun AI content moderation. Covers request and response checks, streaming, deny_code, and ai-proxy. |
| `ai-prompt-decorator` | [plugins/ai-prompt-decorator.md](references/plugins/ai-prompt-decorator.md) | Covers prepending and appending system/user/assistant messages to LLM requests, setting conversation… |
| `ai-prompt-template` | [plugins/ai-prompt-template.md](references/plugins/ai-prompt-template.md) | Covers defining reusable prompt templates with variable placeholders, enforcing prompt structure, accepting… |
| `ai-proxy` | [plugins/ai-proxy.md](references/plugins/ai-proxy.md) | Covers proxying requests to LLM providers (OpenAI, Azure OpenAI, DeepSeek, Anthropic, Gemini, Vertex AI,… |
| `basic-auth` | [plugins/basic-auth.md](references/plugins/basic-auth.md) | Covers HTTP Basic Authentication setup on routes, consumer credential binding with username/password,… |
| `consumer-restriction` | [plugins/consumer-restriction.md](references/plugins/consumer-restriction.md) | Covers restricting access by consumer name, consumer group ID, service ID, or route ID using… |
| `cors` | [plugins/cors.md](references/plugins/cors.md) | Covers Cross-Origin Resource Sharing setup on routes, allow_origins, allow_methods, allow_headers,… |
| `datadog` | [plugins/datadog.md](references/plugins/datadog.md) | Covers pushing custom metrics to Datadog via DogStatsD, metric tags, batching, plugin metadata for global… |
| `ext-plugin-pre-req` | [plugins/ext-plugin.md](references/plugins/ext-plugin.md) | External plugin system (ext-plugin-pre-req, ext-plugin-post-req, ext-plugin-post-resp). Covers Plugin Runner… |
| `fault-injection` | [plugins/fault-injection.md](references/plugins/fault-injection.md) | Covers injecting delays and HTTP aborts for chaos engineering, percentage-based sampling, conditional… |
| `grpc-transcode` | [plugins/grpc-transcode.md](references/plugins/grpc-transcode.md) | Covers converting RESTful HTTP requests to gRPC, proto file management, pb_option settings for data type… |
| `hmac-auth` | [plugins/hmac-auth.md](references/plugins/hmac-auth.md) | Covers HMAC signature authentication, consumer credential binding with key_id/secret_key, allowed… |
| `http-logger` | [plugins/http-logger.md](references/plugins/http-logger.md) | Covers pushing access logs to HTTP/HTTPS endpoints in batches, custom log formats with NGINX variables,… |
| `ip-restriction` | [plugins/ip-restriction.md](references/plugins/ip-restriction.md) | Covers IP whitelist/blacklist setup on routes, CIDR range support, IPv4/IPv6, real client IP extraction… |
| `jwt-auth` | [plugins/jwt-auth.md](references/plugins/jwt-auth.md) | Covers JWT token authentication, HS256/RS256 algorithm selection, consumer credential binding, token lookup… |
| `kafka-logger` | [plugins/kafka-logger.md](references/plugins/kafka-logger.md) | Covers pushing access logs to Apache Kafka topics, broker configuration, SASL authentication (PLAIN,… |
| `key-auth` | [plugins/key-auth.md](references/plugins/key-auth.md) | Covers API key authentication setup on routes, consumer credential binding, key lookup from… |
| `limit-count` | [plugins/limit-count.md](references/plugins/limit-count.md) | Covers fixed and sliding windows, Redis Sentinel, delayed sync, and shared quotas. |
| `limit-req` | [plugins/limit-req.md](references/plugins/limit-req.md) | Covers leaky-bucket rate limiting, rate/burst configuration, nodelay behavior, key types, Redis policies for… |
| `openid-connect` | [plugins/openid-connect.md](references/plugins/openid-connect.md) | Covers authorization-code and bearer flows, PAR, DPoP, and session validation. |
| `prometheus` | [plugins/prometheus.md](references/plugins/prometheus.md) | Prometheus. Covers HTTP, LLM, and AI cache metrics, latency type labels, and Grafana dashboards. |
| `proxy-rewrite` | [plugins/proxy-rewrite.md](references/plugins/proxy-rewrite.md) | Covers rewriting request URI, host, method, headers, and scheme before forwarding to upstream. Includes… |
| `redirect` | [plugins/redirect.md](references/plugins/redirect.md) | Covers URI redirects, HTTP-to-HTTPS redirection, regex-based URI rewriting, query string handling, and… |
| `response-rewrite` | [plugins/response-rewrite.md](references/plugins/response-rewrite.md) | Covers rewriting response status codes, headers, and body before returning to clients. Includes conditional… |
| `serverless-pre-function` | [plugins/serverless.md](references/plugins/serverless.md) | Serverless-pre-function and serverless-post-function plugins. Covers inline Lua function execution in… |
| `skywalking` | [plugins/skywalking.md](references/plugins/skywalking.md) | Covers distributed tracing with Apache SkyWalking OAP, sampling configuration, service topology, and… |
| `traffic-split` | [plugins/traffic-split.md](references/plugins/traffic-split.md) | Covers weighted traffic splitting between upstreams with conditional match rules. Includes canary release,… |
| `wolf-rbac` | [plugins/wolf-rbac.md](references/plugins/wolf-rbac.md) | Covers integration with the Wolf RBAC server for role-based access control, token management,… |
| `zipkin` | [plugins/zipkin.md](references/plugins/zipkin.md) | Covers distributed tracing with Zipkin, Jaeger, or any Zipkin-compatible collector, B3 propagation headers,… |

### Recipes — multi-step workflows (8)

| Workflow | Reference | Covers |
|---|---|---|
| `api-versioning` | [recipes/api-versioning.md](references/recipes/api-versioning.md) | Covers URI path versioning with proxy-rewrite, header-based versioning with traffic-split, query parameter… |
| `blue-green` | [recipes/blue-green.md](references/recipes/blue-green.md) | Blue-green deployments. Covers creating two upstream environments, switching traffic instantly via route… |
| `canary` | [recipes/canary.md](references/recipes/canary.md) | Covers gradual traffic shifting with the traffic-split plugin, header-based canary routing, weight… |
| `circuit-breaker` | [recipes/circuit-breaker.md](references/recipes/circuit-breaker.md) | Covers the api-breaker plugin for automatic upstream circuit breaking, configuring unhealthy thresholds,… |
| `graphql-proxy` | [recipes/graphql-proxy.md](references/recipes/graphql-proxy.md) | Covers operation-based routing with built-in GraphQL variables, per-operation rate limiting, REST-to-GraphQL… |
| `health-check` | [recipes/health-check.md](references/recipes/health-check.md) | Upstream health checks. Covers active health checks (HTTP probing), passive health checks (response… |
| `mtls` | [recipes/mtls.md](references/recipes/mtls.md) | Mutual TLS (mTLS). Covers SSL certificate management, upstream mTLS to backend services, client certificate… |
| `multi-tenant` | [recipes/multi-tenant.md](references/recipes/multi-tenant.md) | Tenant-aware policies on a shared APISIX gateway. Covers shared policies through Consumer Groups,… |

### Personas — role-based guidance (2)

| Role | Reference | Covers |
|---|---|---|
| `developer` | [personas/developer.md](references/personas/developer.md) | API developers building and testing APIs. Provides decision frameworks for API design, route configuration,… |
| `operator` | [personas/operator.md](references/personas/operator.md) | Platform operators and DevOps engineers managing APISIX instances. Provides decision frameworks for… |

<!-- routing-tables:end -->

If nothing matches, the request is probably plain resource CRUD (routes, services, upstreams, consumers, SSL, global rules): [references/shared.md](references/shared.md) is sufficient. Machine-readable metadata for every reference is in [references/index.json](references/index.json).

## 3. Operating rules

1. **Inspect before you change.** List or get the current resource (`a6 route get <id>`, `a6 route list`) and show the user what exists.
2. **Propose an exact change and wait for approval** before applying anything to a gateway. Prefer file-based commands (`-f route.yaml` / `-f -`) so the full payload is visible.
3. **Apply only the approved change**, scoped as narrowly as possible.
4. **Verify** with a follow-up `get` and, where possible, a test request through the gateway.
5. **Keep a rollback path**: note the previous configuration before updating, and use `a6 config dump` / `a6 config diff` for larger changes.
6. **Never put an access token or Admin API key in a prompt, file, or commit.** Use `a6 context` for credentials.
7. **Use a non-production instance for a first run** of any new workflow.

## 4. Example — combine two references

User: *"Add key-auth to my `/orders` route and rate-limit it to 100 requests per minute."*

1. Read `references/shared.md`, then `references/plugins/key-auth.md` and `references/plugins/limit-count.md`.
2. Inspect: `a6 route get orders`.
3. Propose the merged plugin block, get approval, apply with `a6 route update orders -f route.yaml`, then verify with `a6 route get orders`.
