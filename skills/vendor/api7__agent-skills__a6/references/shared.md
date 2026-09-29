---
title: "a6 CLI conventions"
description: "Core skill for working with the a6 CLI — the Apache APISIX command-line tool. Provides project conventions, command patterns, architecture overview, and development workflow. Load this skill when working on a6 source code, adding new commands, writing tests, or modifying any a6 component."
metadata:
  category: shared
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route
    - a6 upstream
    - a6 service
    - a6 consumer
    - a6 ssl
    - a6 plugin
    - a6 config
    - a6 context
  source: https://github.com/api7/a6/blob/main/skills/a6-shared/SKILL.md
---
# a6 CLI conventions

## What is a6

a6 is a Go CLI wrapping the Apache APISIX Admin API. It provides imperative CRUD
for all 14 APISIX resources, declarative config sync, context management for
multiple APISIX instances, and debug tooling.

- **Binary**: `a6`
- **Module**: `github.com/api7/a6`
- **Go**: 1.22+
- **Pattern**: noun-verb (`a6 <resource> <action> [flags]`)

## Project Layout

```
a6/
├── cmd/a6/main.go                  # Entry point
├── pkg/cmd/                        # Command implementations
│   ├── root/root.go                # Root command, registers all subcommands
│   ├── factory.go                  # DI: IOStreams, HttpClient, Config
│   ├── route/                      # a6 route list|get|create|update|delete
│   ├── upstream/                   # a6 upstream list|get|create|update|delete|health
│   ├── service/                    # a6 service ...
│   ├── consumer/                   # a6 consumer ...
│   ├── ssl/                        # a6 ssl ...
│   ├── plugin/                     # a6 plugin list|get
│   ├── config/                     # a6 config sync|diff|dump|validate
│   └── context/                    # a6 context create|use|list|delete|current
├── pkg/api/                        # Admin API HTTP client + types
│   ├── client.go                   # Thin net/http wrapper with auth
│   └── types_*.go                  # Go structs per resource (Route, Upstream, etc.)
├── pkg/iostreams/                  # I/O abstraction (TTY detection)
├── pkg/cmdutil/                    # Shared utilities (errors, exporter, flags)
├── pkg/tableprinter/               # Table rendering
├── pkg/httpmock/                   # HTTP mock for unit tests
├── internal/config/                # Context/config file management
├── test/fixtures/                  # JSON fixtures for unit tests
├── test/e2e/                       # E2E tests (build tag: e2e)
└── docs/                           # Project documentation
```

## Architecture Patterns

### Factory Pattern (Dependency Injection)

Every command receives a `*cmd.Factory` containing `IOStreams`, `HttpClient()`,
and `Config()`. No global state. This enables full test isolation.

```go
type Factory struct {
    IOStreams   *iostreams.IOStreams
    HttpClient func() (*http.Client, error)
    Config     func() (config.Config, error)
}
```

### Command Pattern (Options + NewCmd + Run)

Every command follows the same structure:

```go
type Options struct {
    IO     *iostreams.IOStreams
    Client func() (*http.Client, error)
    Config func() (config.Config, error)
    // command-specific fields
}

func NewCmdXxx(f *cmd.Factory) *cobra.Command { ... }
func xxxRun(opts *Options) error { ... }
```

### Output Pattern

- TTY → table output (human-friendly)
- Non-TTY → JSON (machine-readable)
- `--output json|yaml|table` overrides detection

### Testing Pattern

- Unit tests: `httpmock` stubs + test IOStreams. Zero real network calls.
- E2E tests: `//go:build e2e`, real APISIX in Docker, binary invocation.
- Fixtures: `test/fixtures/*.json` for realistic mock responses.

## Adding a New Command

1. Read the API spec: `docs/admin-api-spec.md`
2. Create types: `pkg/api/types_<resource>.go` with both `json:` and `yaml:` tags
3. Create parent command: `pkg/cmd/<resource>/<resource>.go`
4. Create action: `pkg/cmd/<resource>/<action>/<action>.go` (follow `docs/golden-example.md`)
5. Add tests: `*_test.go` in same package (TTY, non-TTY, filter, error cases)
6. Add fixture: `test/fixtures/<resource>_<action>.json`
7. Register: add to `pkg/cmd/root/root.go`
8. Update docs: `docs/user-guide/<resource>.md`

## Common Commands

```bash
make build          # Build to ./bin/a6
make test           # Unit tests (excludes e2e)
make test-e2e       # E2E tests (requires running APISIX)
make lint           # golangci-lint
make fmt            # gofmt
make check          # fmt + vet + lint + test
make docker-up      # Start local APISIX stack
make docker-down    # Stop local APISIX stack
```

## Code Conventions

- `gofmt` + `goimports` formatting
- Error messages: lowercase, no trailing punctuation
- camelCase locals, PascalCase exports
- No `any` or `interface{}` — use concrete types or generics
- All struct fields need both `json:` and `yaml:` tags
- Never suppress errors; always handle and propagate

## Resource Types Covered

| Resource | Key Field | API Path |
|----------|-----------|----------|
| Route | `id` | `/apisix/admin/routes` |
| Service | `id` | `/apisix/admin/services` |
| Upstream | `id` | `/apisix/admin/upstreams` |
| Consumer | `username` | `/apisix/admin/consumers` |
| SSL | `id` | `/apisix/admin/ssl` |
| Global Rule | `id` | `/apisix/admin/global_rules` |
| Plugin Config | `id` | `/apisix/admin/plugin_configs` |
| Consumer Group | `id` | `/apisix/admin/consumer_groups` |
| Stream Route | `id` | `/apisix/admin/stream_routes` |
| Proto | `id` | `/apisix/admin/protos` |
| Secret | `id` | `/apisix/admin/secrets/{manager}/{id}` |
| Plugin Metadata | `plugin_name` | `/apisix/admin/plugin_metadata/{name}` |
| Plugin (read-only) | `name` | `/apisix/admin/plugins` |
| Credential | `id` | `/apisix/admin/consumers/{username}/credentials` |

## Config Sync Workflow

The declarative config system (`a6 config sync/diff/dump/validate`) manages
resources via YAML files:

```yaml
version: "1"
routes:
  - id: my-route
    uri: /api/*
    upstream_id: my-upstream
upstreams:
  - id: my-upstream
    type: roundrobin
    nodes:
      "httpbin:8080": 1
```

Sync processes resources in dependency order: upstreams/services first,
routes/stream_routes last. Deletes happen in reverse order. Transient
"still referenced" errors during delete are retried with exponential backoff.
