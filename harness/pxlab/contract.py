"""The proxy contract: what every stack in stacks/<key>/ must expose so the same probes and load scenarios apply.

Ports are *inside* the pxlab network (the load generator hits `proxy:<port>` directly) and published on the host
with a 1xxxx prefix (the functional probes use those). Hostnames select behaviours; paths under app.lab select
features. A stack that cannot implement a behaviour declares it in lab.yaml `unsupported:` with the reason and
the matrix shows `--` instead of a failure. Full description: docs/contract.md.
"""
from __future__ import annotations

NETWORK = "pxlab"
SUBNET = "10.77.0.0/24"
CLIENT_IP = "10.77.0.1"          # what the proxy sees as the source of a request coming from the host (docker-proxy / bridge gateway)
PROXY_HOST = "proxy"             # network alias every proxy service carries
LOADGEN_CPUSET = "10-13,24-27"
PROXY_CPUSET = "0-3"
BACKEND_CPUSET = "4-9,18-23"

# proxy listener -> (port inside the network, port published on the host)
PORTS = {
    "http": (8080, 18080),          # HTTP/1.1 (+ h2c where the proxy can)
    "https": (8443, 18443),         # TLS: HTTP/1.1 + HTTP/2 (+ HTTP/3 on UDP where the proxy can)
    "mtls": (8444, 18444),          # TLS with a required client certificate
    "passthrough": (8445, 18445),   # L4 TLS passthrough routed by SNI -> backend :8443
    "pp": (8082, 18082),            # HTTP listener that *accepts* PROXY protocol from the client
    "tcp": (9000, 19000),           # L4 TCP proxy -> app1:8080
    "udp": (9001, 19001),           # L4 UDP proxy -> app1:9002
    "metrics": (9100, 19100),       # Prometheus /metrics (native or exporter sidecar)
    "admin": (9101, 19101),         # stats / admin / config API
}

BACKENDS = {  # instance -> (ip, host port to its :8080 for admin toggles)
    "app1": ("10.77.0.11", 18101), "app2": ("10.77.0.12", 18102), "app3": ("10.77.0.13", 18103),
    "slow": ("10.77.0.14", 18104), "flaky": ("10.77.0.15", 18105), "canary": ("10.77.0.16", 18106),
    "shadow": ("10.77.0.17", 18107), "b1": ("10.77.0.18", 18108),
}
POOL_APP = {"app1", "app2", "app3"}

# hostnames -> behaviour (Host header on :8080, SNI + Host on :8443)
HOSTS = {
    "app.lab": "default vhost: pool app (app1,app2,app3) round-robin; every path-based feature lives here",
    "a.lab": "host routing -> pool app, request header X-Route: a",
    "b.lab": "host routing -> pool b (b1) with its OWN certificate (CN=b.lab) on :8443",
    "weighted.lab": "weighted round-robin app1:3 app2:1",
    "leastconn.lab": "least-connections over app1, app2, slow(100 ms)",
    "hash.lab": "consistent hashing on the X-User header (fallback: client IP)",
    "sticky.lab": "cookie stickiness (cookie lab_sticky) over app1,app2,app3",
    "retry.lab": "pool app1, app2 + a dead member (app3:8099); retry on connect failure must hide it",
    "cb.lab": "outlier detection / circuit breaker over app1, app2, flaky (passive: eject after consecutive 5xx)",
    "health.lab": "active health checks (GET /healthz every 1-2 s) over app1, app2, app3",
    "canary.lab": "traffic split 90% pool app / 10% canary",
    "mirror.lab": "pool app + mirror (shadow) every request to shadow",
    "pp.lab": "sends PROXY protocol v2 to the upstream (app1:8081)",
    "h2.lab": "talks HTTP/2 (h2c) to the upstream (app1:8080)",
    "tls.lab": "re-encrypts to the upstream (app1:8443) and verifies it against the lab CA (SNI backend.lab)",
    "auth.lab": "forward auth: every request is authorized by GET app1:8080/auth first (X-Auth-Token: lab-secret)",
    "jwt.lab": "requires a valid HS256 JWT (Authorization: Bearer)",
    "acme.lab": "certificate obtained automatically from the Pebble ACME server (on :8443)",
    "mtls.lab": "on :8444 - client certificate required; CN forwarded in X-Client-Cert-CN when possible",
    "passthrough.lab": "on :8445 - TLS passthrough by SNI to app1:8443 (client sees CN=backend.lab)",
    "redirect.lab": "on :8080 - permanent redirect to https://",
    "whoami.lab": "discovered from Docker labels (Traefik docker provider) - n/a elsewhere",
}

# paths under app.lab -> feature
PATHS = {
    "/": "echo (pool app)",
    "/api/<x>": "prefix route: strips /api, upstream sees /<x>, request header X-Route: api",
    "/v<n>/<x>": "regex route ^/v[0-9]+/, request header X-Route: versioned",
    "/old/<x>": "rewrite to /new/<x>, request header X-Route: rewritten",
    "/redirect-me": "301 -> /landing",
    "/ws": "WebSocket upgrade to the pool",
    "/sse": "server-sent events, must not be buffered",
    "/grpc.health.v1.Health/*": "gRPC (h2) -> app1:9090 (h2c)",
    "/limited": "rate limit 10 r/s (burst 5) per client -> 429",
    "/conn-limited": "max 3 concurrent connections per client -> 503/429 (upstream /delay/1000)",
    "/allowed": "allowed only from 10.77.0.1 (the host)",
    "/denied": "denied for 10.77.0.0/24 -> 403",
    "/basic": "basic auth lab:lab-pass",
    "/upload": "request body limited to 1 MiB -> 413",
    "/timeout": "upstream /delay/5000 with a 2 s read timeout -> 504",
    "/fault": "fault injection: ~20% of requests get an immediate 503 from the proxy",
    "/bw": "bandwidth limit 500 KB/s on a 1 MiB body (upstream /bin/1048576)",
    "/static/": "served from the proxy's own filesystem (shared/static)",
    "/error-page": "upstream /status/503 replaced by the proxy's custom error page (X-Error-Page: custom)",
    "/cors": "CORS: OPTIONS preflight answered by the proxy with Access-Control-Allow-Origin",
    "/secure": "security headers added by the proxy (HSTS, X-Content-Type-Options, X-Frame-Options)",
    "/cacheable/*": "response cache (honours Cache-Control max-age=60); X-Cache: HIT|MISS",
    "/cacheable-short/*": "cache with max-age=2 + serve-stale-on-error",
    "/compressible": "upstream /size/65536 text; proxy compresses (gzip / br / zstd)",
    "/small": "~200 B JSON for throughput tests",
    "/bin/<n>": "n incompressible bytes",
    "/delay/<ms>": "upstream delay",
    "/status/<code>": "upstream status",
}

JWT_SECRET = "pxlab-jwt-secret-please-change-0123456789"
BASIC_USER, BASIC_PASS = "lab", "lab-pass"
AUTH_TOKEN = "lab-secret"
