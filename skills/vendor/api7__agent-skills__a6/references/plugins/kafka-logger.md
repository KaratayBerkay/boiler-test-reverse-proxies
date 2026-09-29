---
title: "kafka-logger plugin"
description: "Skill for configuring the Apache APISIX kafka-logger plugin via the a6 CLI. Covers pushing access logs to Apache Kafka topics, broker configuration, SASL authentication (PLAIN, SCRAM-SHA-256/512), custom log formats, producer tuning, and batch processing."
metadata:
  category: plugin
  plugin_name: kafka-logger
  apisix_version: ">=3.0.0"
  a6_commands:
    - a6 route create
    - a6 route update
    - a6 config sync
  source: https://github.com/api7/a6/blob/main/skills/a6-plugin-kafka-logger/SKILL.md
---
# kafka-logger plugin

> Part of the `a6` skill for Apache APISIX. Read [a6 CLI conventions](../shared.md) first if you have not already.

## Overview

The `kafka-logger` plugin pushes request/response logs to Apache Kafka
topics. It supports multiple brokers, SASL authentication, async/sync
producing, custom log formats, and batch processing for efficient delivery.

## When to Use

- Stream access logs to Kafka for downstream processing
- Feed real-time API analytics pipelines
- Integrate with Kafka-based logging infrastructure
- Need SASL-authenticated Kafka clusters

## Plugin Configuration Reference

### Core Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `brokers` | array | **Yes** | — | Kafka broker list |
| `brokers[].host` | string | **Yes** | — | Broker hostname or IP |
| `brokers[].port` | integer | **Yes** | — | Broker port (1-65535) |
| `kafka_topic` | string | **Yes** | — | Target Kafka topic |
| `key` | string | No | — | Partition key for routing |
| `timeout` | integer | No | `3` | Connection timeout in seconds |

### SASL Authentication

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `brokers[].sasl_config` | object | No | — | SASL config per broker |
| `brokers[].sasl_config.mechanism` | string | No | `"PLAIN"` | `PLAIN`, `SCRAM-SHA-256`, or `SCRAM-SHA-512` |
| `brokers[].sasl_config.user` | string | Yes* | — | SASL username (*if sasl_config set) |
| `brokers[].sasl_config.password` | string | Yes* | — | SASL password (*if sasl_config set) |

### Producer Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `producer_type` | string | `"async"` | `async` (batched) or `sync` (immediate) |
| `required_acks` | integer | `1` | `1` (leader ack) or `-1` (all replicas) |
| `producer_batch_num` | integer | `200` | Messages per Kafka batch |
| `producer_batch_size` | integer | `1048576` | Batch size in bytes (1MB) |
| `producer_max_buffering` | integer | `50000` | Max buffered messages |
| `producer_time_linger` | integer | `1` | Flush interval in seconds |
| `meta_refresh_interval` | integer | `30` | Kafka metadata refresh in seconds |
| `cluster_name` | integer | `1` | Cluster identifier (for multi-cluster) |

### Log Format Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `meta_format` | string | `"default"` | `default` (JSON) or `origin` (raw HTTP) |
| `log_format` | object | — | Custom log format with `$variable` syntax |
| `include_req_body` | boolean | `false` | Include request body |
| `include_req_body_expr` | array | — | Conditional request body logging |
| `include_resp_body` | boolean | `false` | Include response body |
| `include_resp_body_expr` | array | — | Conditional response body logging |
| `max_req_body_bytes` | integer | `524288` | Max request body size to log (512KB) |
| `max_resp_body_bytes` | integer | `524288` | Max response body size to log (512KB) |

### Batch Processing Parameters

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `batch_max_size` | integer | `1000` | Max entries per batch |
| `inactive_timeout` | integer | `5` | Seconds before flushing incomplete batch |
| `buffer_duration` | integer | `60` | Max age of oldest entry |
| `max_retry_count` | integer | `0` | Retry attempts on failure |
| `retry_delay` | integer | `1` | Seconds between retries |

## Step-by-Step: Ship Logs to Kafka

### 1. Create a route with kafka-logger

```bash
a6 route create -f - <<'EOF'
{
  "id": "kafka-logged-api",
  "uri": "/api/*",
  "plugins": {
    "kafka-logger": {
      "brokers": [
        {"host": "kafka-1", "port": 9092},
        {"host": "kafka-2", "port": 9092}
      ],
      "kafka_topic": "apisix-logs",
      "batch_max_size": 100
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "backend:8080": 1
    }
  }
}
EOF
```

### 2. Verify messages in Kafka

```bash
kafka-console-consumer --bootstrap-server kafka-1:9092 --topic apisix-logs --from-beginning
```

## Common Patterns

### SASL-authenticated Kafka cluster

```json
{
  "plugins": {
    "kafka-logger": {
      "brokers": [
        {
          "host": "kafka.example.com",
          "port": 9092,
          "sasl_config": {
            "mechanism": "SCRAM-SHA-256",
            "user": "apisix",
            "password": "secret"
          }
        }
      ],
      "kafka_topic": "api-logs",
      "required_acks": -1
    }
  }
}
```

### Custom log format

```json
{
  "plugins": {
    "kafka-logger": {
      "brokers": [{"host": "kafka", "port": 9092}],
      "kafka_topic": "api-logs",
      "log_format": {
        "@timestamp": "$time_iso8601",
        "client_ip": "$remote_addr",
        "method": "$request_method",
        "uri": "$request_uri",
        "status": "$status",
        "latency": "$request_time",
        "upstream": "$upstream_addr"
      }
    }
  }
}
```

### Partition by route ID

```json
{
  "plugins": {
    "kafka-logger": {
      "brokers": [{"host": "kafka", "port": 9092}],
      "kafka_topic": "api-logs",
      "key": "$route_id"
    }
  }
}
```

### High-throughput tuning

```json
{
  "plugins": {
    "kafka-logger": {
      "brokers": [
        {"host": "kafka-1", "port": 9092},
        {"host": "kafka-2", "port": 9092},
        {"host": "kafka-3", "port": 9092}
      ],
      "kafka_topic": "api-logs",
      "producer_type": "async",
      "producer_batch_num": 500,
      "producer_batch_size": 2097152,
      "producer_max_buffering": 100000,
      "producer_time_linger": 2,
      "batch_max_size": 5000,
      "inactive_timeout": 10,
      "required_acks": 1
    }
  }
}
```

### Raw HTTP log format

```json
{
  "plugins": {
    "kafka-logger": {
      "brokers": [{"host": "kafka", "port": 9092}],
      "kafka_topic": "raw-logs",
      "meta_format": "origin"
    }
  }
}
```

Produces raw HTTP request text instead of JSON.

## Config Sync Example

```yaml
version: "1"
routes:
  - id: kafka-logged-api
    uri: /api/*
    plugins:
      kafka-logger:
        brokers:
          - host: kafka-1
            port: 9092
          - host: kafka-2
            port: 9092
        kafka_topic: apisix-logs
        producer_type: async
        required_acks: 1
        batch_max_size: 200
        inactive_timeout: 5
    upstream_id: my-upstream
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No messages in Kafka | Broker unreachable | Verify broker host/port; check firewall |
| SASL auth failure | Wrong credentials or mechanism | Verify user/password; ensure mechanism matches Kafka config |
| Messages delayed | Large batch/timeout settings | Reduce `inactive_timeout` and `producer_time_linger` |
| Messages dropped | Buffer overflow | Increase `producer_max_buffering`; add more brokers |
| Topic not found | Topic doesn't exist and auto-create disabled | Create topic manually or enable `auto.create.topics.enable` |
| High latency | `required_acks: -1` with slow replicas | Use `required_acks: 1` for lower latency (less durability) |
