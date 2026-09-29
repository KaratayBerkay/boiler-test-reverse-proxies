---
title: "grpc-transcode plugin"
description: "Skill for configuring the Apache APISIX grpc-transcode plugin via the a6 CLI. Covers converting RESTful HTTP requests to gRPC, proto file management, pb_option settings for data type conversion, error detail decoding, and common operational patterns."
metadata:
  category: plugin
  plugin_name: grpc-transcode
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 proto create
    - a6 proto list
    - a6 proto get
    - a6 proto delete
    - a6 route create
    - a6 route update
    - a6 route get
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-grpc-transcode/SKILL.md
---
# grpc-transcode plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `grpc-transcode` plugin converts HTTP/JSON requests into gRPC calls and
returns gRPC responses as JSON. Clients send standard HTTP requests; APISIX
transcodes them to gRPC using a pre-uploaded protobuf definition, forwards to
the gRPC upstream, and returns the response as JSON. The gRPC service needs
no modification.

## When to Use

- Expose gRPC services via RESTful HTTP endpoints
- Allow browser/mobile clients to call gRPC services without gRPC client libraries
- Add HTTP API gateway features (auth, rate limiting, logging) to gRPC services
- Migrate from REST to gRPC incrementally
- Decode gRPC error details into human-readable JSON

## Plugin Configuration Reference (Route/Service)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `proto_id` | string/integer | **Yes** | — | ID of the proto resource (uploaded via `a6 proto create`). |
| `service` | string | **Yes** | — | Fully qualified gRPC service name (e.g., `helloworld.Greeter`). |
| `method` | string | **Yes** | — | gRPC method name (e.g., `SayHello`). |
| `deadline` | number | No | `0` | Deadline for the gRPC call in milliseconds. `0` = no deadline. |
| `pb_option` | array[string] | No | — | Protobuf serialization options (see table below). |
| `show_status_in_body` | boolean | No | `false` | Include parsed `grpc-status-details-bin` in the JSON response body on errors. |
| `status_detail_type` | string | No | — | Message type for the `details` field in gRPC error status. Required to decode error details. |

## pb_option Values

| Option | Description |
|--------|-------------|
| `enum_as_name` | Return enum fields as string names (e.g., `"PENDING"`) |
| `enum_as_value` | Return enum fields as integer values (e.g., `1`) |
| `int64_as_number` | Return int64 as JSON number (may lose precision in JavaScript) |
| `int64_as_string` | Return int64 as string (safe for JavaScript clients) |
| `int64_as_hexstring` | Return int64 as hexadecimal string |
| `auto_default_values` | Auto-populate default values for unset fields |
| `no_default_values` | Do not add default values for unset fields |
| `use_default_values` | Use proto-defined default values |
| `use_default_metatable` | Use metatable for default values |
| `enable_hooks` | Enable protobuf hooks |
| `disable_hooks` | Disable protobuf hooks |

Multiple options can be combined: `["int64_as_string", "enum_as_name"]`

## Step-by-Step: Set Up gRPC Transcoding

### 1. Upload the proto definition

Given a proto file:
```protobuf
syntax = "proto3";
package helloworld;

service Greeter {
    rpc SayHello (HelloRequest) returns (HelloReply) {}
}

message HelloRequest {
    string name = 1;
}

message HelloReply {
    string message = 1;
}
```

Upload it:

```bash
a6 proto create -f - <<'EOF'
{
  "id": "1",
  "content": "syntax = \"proto3\";\npackage helloworld;\nservice Greeter {\n    rpc SayHello (HelloRequest) returns (HelloReply) {}\n}\nmessage HelloRequest {\n    string name = 1;\n}\nmessage HelloReply {\n    string message = 1;\n}"
}
EOF
```

### 2. Create a route with grpc-transcode

```bash
a6 route create -f - <<'EOF'
{
  "id": "grpc-hello",
  "methods": ["GET", "POST"],
  "uri": "/grpc/hello",
  "plugins": {
    "grpc-transcode": {
      "proto_id": "1",
      "service": "helloworld.Greeter",
      "method": "SayHello"
    }
  },
  "upstream": {
    "scheme": "grpc",
    "type": "roundrobin",
    "nodes": {
      "grpc-server:50051": 1
    }
  }
}
EOF
```

**Critical**: The upstream `scheme` **must** be `"grpc"` (or `"grpcs"` for TLS).

### 3. Test the endpoint

```bash
# Pass parameters via query string
curl "http://localhost:9080/grpc/hello?name=world"
# Response: {"message":"Hello world"}

# Or via POST body
curl -X POST http://localhost:9080/grpc/hello \
  -H "Content-Type: application/json" \
  -d '{"name": "world"}'
# Response: {"message":"Hello world"}
```

## Common Patterns

### Proto with imports (use compiled .pb file)

When your proto has `import` statements, compile to a `.pb` file first:

```bash
protoc --include_imports --descriptor_set_out=service.pb proto/service.proto
```

Then upload the base64-encoded `.pb`:

```bash
a6 proto create -f - <<EOF
{
  "id": "2",
  "content": "$(base64 -i service.pb)"
}
EOF
```

### Safe int64 handling for JavaScript clients

```json
{
  "plugins": {
    "grpc-transcode": {
      "proto_id": "1",
      "service": "order.OrderService",
      "method": "GetOrder",
      "pb_option": ["int64_as_string"]
    }
  }
}
```

Returns `{"order_id": "9223372036854775807"}` instead of `{"order_id": 9223372036854775807}` (which JavaScript would corrupt).

### Human-readable enums

```json
{
  "plugins": {
    "grpc-transcode": {
      "proto_id": "1",
      "service": "order.OrderService",
      "method": "GetOrder",
      "pb_option": ["enum_as_name", "int64_as_string"]
    }
  }
}
```

Returns `{"status": "PENDING"}` instead of `{"status": 1}`.

### gRPC error detail decoding

```json
{
  "plugins": {
    "grpc-transcode": {
      "proto_id": "1",
      "service": "helloworld.Greeter",
      "method": "SayHello",
      "show_status_in_body": true,
      "status_detail_type": "helloworld.ErrorDetail"
    }
  }
}
```

Error response body:
```json
{
  "error": {
    "code": 14,
    "message": "Out of service",
    "details": [
      {
        "type": "service",
        "message": "The server is out of service",
        "code": 1
      }
    ]
  }
}
```

### Timeout control with deadline

```json
{
  "plugins": {
    "grpc-transcode": {
      "proto_id": "1",
      "service": "slow.SlowService",
      "method": "LongRunning",
      "deadline": 5000
    }
  }
}
```

Request fails if the gRPC service doesn't respond within 5 seconds.

### Multiple gRPC methods on different routes

```json
// Route 1: GET /api/users/:id → user.UserService/GetUser
{
  "id": "grpc-get-user",
  "uri": "/api/users/*",
  "methods": ["GET"],
  "plugins": {
    "grpc-transcode": {
      "proto_id": "3",
      "service": "user.UserService",
      "method": "GetUser"
    }
  },
  "upstream": {"scheme": "grpc", "type": "roundrobin", "nodes": {"user-svc:50051": 1}}
}

// Route 2: POST /api/users → user.UserService/CreateUser
{
  "id": "grpc-create-user",
  "uri": "/api/users",
  "methods": ["POST"],
  "plugins": {
    "grpc-transcode": {
      "proto_id": "3",
      "service": "user.UserService",
      "method": "CreateUser"
    }
  },
  "upstream": {"scheme": "grpc", "type": "roundrobin", "nodes": {"user-svc:50051": 1}}
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "can not find proto" | Proto ID doesn't exist | Verify with `a6 proto get <id>` |
| "method not found" | Service or method name mismatch | Use fully qualified name: `package.Service`, case-sensitive |
| Connection refused to upstream | Wrong scheme or port | Set upstream `scheme` to `grpc`, verify port is gRPC port |
| Import errors in proto | Proto has imports but raw content uploaded | Compile to `.pb` with `protoc --include_imports` |
| int64 values corrupted | JavaScript precision loss | Use `pb_option: ["int64_as_string"]` |
| Enum shows numbers instead of names | Default behavior | Use `pb_option: ["enum_as_name"]` |
| Error details not decoded | `show_status_in_body` not set | Set `show_status_in_body: true` and `status_detail_type` |
| gRPC call times out silently | No deadline set | Set `deadline` in milliseconds |
| 502 Bad Gateway | gRPC service not running or not reachable | Check gRPC service is up and port is accessible from APISIX |

## Config Sync Example

```yaml
version: "1"
protos:
  - id: helloworld-proto
    content: |
      syntax = "proto3";
      package helloworld;
      service Greeter {
          rpc SayHello (HelloRequest) returns (HelloReply) {}
      }
      message HelloRequest {
          string name = 1;
      }
      message HelloReply {
          string message = 1;
      }
routes:
  - id: grpc-hello
    methods:
      - GET
      - POST
    uri: /grpc/hello
    plugins:
      grpc-transcode:
        proto_id: helloworld-proto
        service: helloworld.Greeter
        method: SayHello
        pb_option:
          - int64_as_string
          - enum_as_name
    upstream_id: grpc-backend
upstreams:
  - id: grpc-backend
    scheme: grpc
    type: roundrobin
    nodes:
      "grpc-server:50051": 1
```
