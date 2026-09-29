---
name: reverse-proxy-load-testing
description: Benchmark and load-test reverse proxies, API gateways and load balancers honestly and comparably - NGINX, HAProxy, Caddy, Traefik, Envoy, Apache, Varnish, OpenResty, Kong, APISIX, Pingora, ATS or anything in front of HTTP backends. Covers the tools (oha, wrk, h2load, fortio, k6, a QUIC/h3 loader, grpcurl), closed-loop vs open-loop, keep-alive vs new connections, TLS/h2/h3, large bodies, compression and cache scenarios, WebSocket and gRPC load, rate-limit accuracy, c10k memory, CPU pinning, exact per-container CPU/memory from cgroup v2, warm-up, and how to read rps / p99 / µs-per-request. Use this whenever someone wants to measure a proxy, compare proxies, size a proxy tier, reproduce "requests per second" claims, or asks why their proxy benchmark numbers look wrong or inconsistent.
---

# Load-testing reverse proxies

The reverse-proxies lab ran 14 scenarios against 12 proxies on identical hardware (`reverse-proxies/results/SUMMARY.md`).
This skill is the method that made those numbers comparable, plus what they showed. Read `references/methodology.md`
for the details and `references/measured.md` for the numbers before quoting any figure.

## The method in eight rules

1. **Pin CPUs, isolate roles.** Proxy on its own cores (`cpuset: "0-3"`), backends on others, load generator on
   others still. Without this the generator steals cycles from the proxy and every number is a lie about the host.
2. **Load from inside the Docker network.** Published ports go through `docker-proxy` (userland copy, ~40 % of the
   throughput, and every client looks like the bridge gateway). Run the generator as a container on the same network
   and hit `http://proxy:8080`.
3. **Make the backend faster than the proxy.** A `/small` endpoint answering from memory on 12 cores; if backends
   saturate first you measure them. Check backend CPU in the results (the lab records it).
4. **Warm up 3 s, run >= 15 s, keep-alive on.** Discard the first seconds (connection setup, JIT in Lua/Go
   gateways, TLS session cache). Run the no-keep-alive case separately - it measures accept + TLS handshake cost.
5. **Report CPU per request, not just rps.** `µs of proxy CPU per request = cores_used x 1e6 / rps` from cgroup v2
   `cpu.stat` deltas per container. rps saturates at the core limit; µs/req tells you the efficiency and the
   headroom. Memory: `memory.current` before/after and its peak.
6. **Closed loop for throughput, open loop for latency.** oha/wrk with N connections find the ceiling; fortio at a
   fixed QPS (`-qps 5000 -nocatchup -uniform`) reports the p99 users would see without coordinated omission.
7. **Count aborted requests as aborted.** oha `-w` waits for in-flight requests at the deadline; without it they
   appear as errors. Separate `errors` (transport) from `non2xx` (the proxy said no - e.g. rate limits).
8. **One proxy at a time, same seconds, same tool versions.** Sequential runs; tools baked into one image
   (`shared/loadgen/Dockerfile`).

## Scenario set (copy it - it exposes different bottlenecks)

| scenario | tool / command | what it exposes |
|---|---|---|
| h1 keep-alive 64 conns `/small` | `oha --no-tui --output-format json -w -H 'Host: app.lab' -z 15s -c 64 URL` | per-request CPU of the proxy's HTTP path |
| h1 no keep-alive | `... --disable-keepalive` | accept/close cost, ephemeral ports, `keepalive_requests` |
| wrk reference | `wrk -t8 -c64 -d15s --latency -H 'Host: app.lab' URL` | the number everybody quotes; note wrk counts differently than oha |
| TLS h1 keep-alive | `oha ... --insecure https://proxy:8443/small` | record-layer cost (handshakes amortised) |
| TLS h2 16 x 8 streams | `oha --http2 -c 16 -p 8` (no Host header: h2 `:authority` must match) | HPACK/stream multiplexing efficiency |
| HTTP/3 16 x 8 | `h3load -url https://proxy:8443/small -host app.lab -conns 16 -streams 8` (quic-go) | QUIC cost - typically 2-4x the CPU of h2 |
| 1 MiB bodies 32 conns | `oha -c 32 URL/bin/1048576` -> MB/s | copy path, buffering, `sendfile`/splice |
| gzip 64 KiB | `oha -H 'Accept-Encoding: gzip' URL/compressible` | compression CPU (level matters more than proxy choice) |
| cache hit | prime once, then `oha URL/cacheable/x` | the proxy's cache path - usually faster than proxying |
| WebSocket echo | `k6 run --vus 64 -e URL=ws://proxy:8080/ws` with a 500-message script | message round-trip, upgrade handling |
| gRPC health | `fortio load -grpc -health -cacert ca.crt -c 16 -s 8 -qps 0 -json -` | h2 to h2c bridging (nginx `grpc_pass` ~ 1 conn per stream) |
| open loop 5 000 rps | `fortio load -qps 5000 -c 64 -nocatchup -uniform -json -` | latency at a realistic rate, not at saturation |
| rate-limit accuracy | `oha -q 200 -c 8 -z 10s URL/limited` (10 r/s limit) | how many 2xx leak past the limiter (burst semantics) |
| c10k | `oha -c 10000 -z 20s URL/delay/500` + `ulimit -n 1048576` | memory per idle connection, accept backlog |

## Reading the results

- **rps at ~100 % of the allowed cores** = the proxy is the bottleneck: compare µs/req. **rps at 30 % CPU** = something
  else is (backend, generator, network); look at the other cgroups before blaming the proxy.
- **p50 vs p99 vs max**: p99 under closed loop at saturation is queueing, not proxy latency - use the open-loop number.
  A max of ~3 s during a failover = a connect timeout.
- **h3 CPU 2-4x h2** is expected (userspace QUIC); **gzip level 5 on 64 KiB** costs more than the proxying itself.
- **c10k memory**: the delta `mem_end - mem_start` divided by 10 000 gives bytes per connection; workers with
  per-connection buffers (nginx `proxy_buffers`, Envoy `per_connection_buffer_limit_bytes`) dominate.
- **Rate-limit leakage**: a token bucket with burst 5 lets ~15 through in the first second; sliding windows are exact
  but cost more; different proxies interpret "10 r/s" differently - measure, do not assume.

## Files
- `references/methodology.md` - cgroup accounting, tool parsing quirks, the loadgen image, pitfalls per tool.
- `references/measured.md` - the lab's numbers (12 proxies x 14 scenarios) with commentary.
- `scripts/proxy-bench.sh` - run the core scenarios against any proxy URL from a throwaway container and print a table.
