# Skills

Two groups of Agent Skills (the open `SKILL.md` format: YAML frontmatter with `name` + `description`, optional
`references/` and `scripts/`). Install into Claude Code by copying or symlinking a skill directory into
`~/.claude/skills/` (user-wide) or `.claude/skills/` (project).

## First-party skills (written from this lab's verified results)
| skill | use it for | extras |
|---|---|---|
| `reverse-proxy-capability-mapping` | "how do I do X in proxy Y" for 69 capabilities x 12 proxies, porting configs, honest "not in OSS - do this instead", choosing a proxy | `references/{routing,load-balancing,protocols,tls,caching-compression,headers-security,operations}.md` |
| `docker-compose-reverse-proxies` | verified images, entrypoints, mounts, healthchecks without curl, unprivileged :80, writable state, generated configs, sidecars, CPU pinning, reload commands | `references/stack-index.md` |
| `reverse-proxy-load-testing` | benchmarking proxies comparably: pinning, in-network load, closed vs open loop, cgroup CPU/memory, 14 scenarios, tool quirks, the lab's numbers | `references/methodology.md`, `references/measured.md`, `scripts/proxy-bench.sh` |
| `reverse-proxy-tls-termination` | termination, TLS 1.2/1.3, h2/h3, SNI certificates, mTLS with identity forwarding, TLS re-encryption, SNI passthrough, ACME with public and private CAs | - |
| `reverse-proxy-load-balancing-resilience` | algorithms, active vs passive health, retries and the "no live upstreams" cascade, timeouts, canary/mirroring, keep-alive pools, measured failover and reload behaviour | - |
| `reverse-proxy-security-hardening` | trust boundaries for client IP, rate/concurrency/body limits, basic/JWT/forward auth done safely, headers, CORS, error pages, protocol exposure, verification commands | - |
| `reverse-proxy-observability` | JSON access logs with the right fields, Prometheus natively or via exporters, OTel with parent-based sampling, request ids, admin surfaces, debugging 502/504 | - |
| `reverse-proxy-caching-compression` | Cache-Control semantics, keys/Vary, purge, stale-on-error, coalescing, HIT headers, gzip/brotli/zstd availability and the SSE exception | - |

## Vendored third-party skills (`vendor/`)
Each directory carries a `VENDORED.txt` (source URL, upstream path, commit, license, date) and the upstream `LICENSE`.
Only permissive licenses (Apache-2.0 / MIT). Skills whose upstream repo had no license file were **not** vendored.

| directory | topic | license | why |
|---|---|---|---|
| `api7__agent-skills__a6` | Apache APISIX through the `a6` CLI: 29 plugin references, 8 recipes (canary, blue-green, mTLS, health checks…), operator/developer personas | Apache-2.0 | vendor-authored (API7 / APISIX contributors); the most complete gateway skill found |
| `kong__kongctl__kongctl-declarative` | Kong declarative configuration with kongctl + decK (plan/diff/apply/sync, OpenAPI -> gateway config, CI/CD) | Apache-2.0 | Kong-authored; complements the lab's DB-less stack |
| `netdata__skills__troubleshoot-nginx` / `-haproxy` / `-envoy` / `-traefik` / `-varnish` / `-apache-httpd` | diagnostic trees for connection exhaustion, backend collapse, TLS CPU saturation, buffer starvation, reload storms (Netdata MCP queries optional) | Apache-2.0 | Netdata-authored operations playbooks for six of the lab's proxies |
| `magnus919__agent-skills__traefik` | Traefik v3: providers, routing, middlewares, TLS/ACME, production templates, healthcheck script | MIT | broadest Traefik skill found (evals directory dropped) |
| `ddnetters__homelab-agent-skills__caddy-reverse-proxy` | Caddyfile patterns, automatic HTTPS, Docker integration | MIT | concise Caddy reference |

Surveyed and **not** vendored: repos without a LICENSE (`nejclovrencic/nginx-agent-skills`, `membranedev/application-skills`,
`SecureSkills-io/nginx-skill`, `cloudthinker-ai/CloudSkills`, …), aggregator/mirror catalogs of unclear provenance
(`TerminalSkills/skills`, `agentskillexchange/skills`, `majiayu000/claude-skill-registry`, `sickn33/agentic-awesome-skills`,
`G1Joshi/Agent-Skills`, `bytesagain/ai-skills`), Kubernetes-Gateway-API-only skills (`missBerg/envoy-skills`), and repo-internal
skills in the vendors' own repositories (nginx, traefik, envoyproxy). See `../docs/research-sources.md` for the survey.

Gaps the first-party skills fill: no existing skill covered the cross-proxy capability mapping with verified "unsupported"
reasons, comparable proxy benchmarking, or HAProxy / Envoy Proxy / Varnish / Pingora / ATS configuration in SKILL.md form.
