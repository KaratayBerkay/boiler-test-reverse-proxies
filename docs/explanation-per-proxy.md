# Explanation — Per proxy

One section per proxy: what it runs, its full capability list (69 probes) and its full load results (14 scenarios).

## Apache APISIX 3.15

- **image**: `apache/apisix:3.15.0-debian` (559 MB)
- **version**: `3.15.0`
- **family**: api-gateway — API gateway on OpenResty (Apache): routes/upstreams/consumers/plugins, standalone yaml config (or etcd)
- **reload mechanism**: file-watch (standalone mode re-reads apisix.yaml when its mtime changes; routes are swapped without restart)
- **startup**: 2.8 s
- **docs**: <https://hub.docker.com/r/apache/apisix> · <https://apisix.apache.org/docs/apisix/deployment-modes/#standalone> · <https://apisix.apache.org/docs/apisix/plugins/traffic-split/> · <https://apisix.apache.org/docs/apisix/tutorials/health-check/> · <https://apisix.apache.org/docs/apisix/plugins/proxy-cache/>
- **notes**: Apache APISIX 3.15 in standalone mode (routes in apisix.yaml, hot-reloaded on change). Upstreams show roundrobin / weighted / least_conn / chash on a header, active + passive health checks and retries; traffic-split does the canary split and the cookie stickiness (rules matched on the cookie), proxy-mirror mirrors to shadow, forward-auth / jwt-auth / basic-auth / ip-restriction / limit-req / limit-conn / client-control / cors / fault-injection / redirect / proxy-cache (disk, PURGE) / gzip / brotli / request-id / prometheus / opentelemetry cover the rest; serverless functions set $limit_rate (bandwidth) and serve the static file. HTTP/3 on :8443, h2c on :8080, PROXY protocol on :8082, TCP/UDP stream routes, mTLS per SNI.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab:8443/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.08 {'app1': 137, 'slow': 25, 'app2': 138} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app1': 20}; 10 users -> {'app2': 15, 'app1': 6, 'app3': 9} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=app1; Path=/; HttpOnly' first=app1 then={'app1': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=5 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 13, 500: 7} last20={200: 36, 500: 4} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 3.2s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.6s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.100 {'app3': 60, 'app1': 60, 'app2': 60, 'canary': 20} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ✅| shadow received 20/20 |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app2': 2, 'app3': 3, 'app1': 2} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ✅| proto=HTTP/3.0 status={'200': 641} errors=0 [] |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app2 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.21s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ○| HTTP/2 to upstreams only for gRPC (scheme grpc/grpcs) |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': ''} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| APISIX cannot send PROXY protocol to HTTP upstreams (enable_tcp_pp_to_upstream is for stream routes) |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:32902 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:34770 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ✅| echo:app1:ping-a7012f |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ○| stream routes with `sni` terminate TLS; there is no SNI-based passthrough |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 80571E2694750000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client', 'X-Client-Cert-Verify': 'SUCCESS'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ○| no ACME client in APISIX (use cert-manager / acme.sh and push the certificate) |
caching| Response caching| `cache_hit`| ✅| origin app2#1 -> app2#1; Apisix-Cache-Status: MISS -> HIT age=None |
caching| Cache purge| `cache_purge`| ✅| purge -> 200; origin app1#1 -> app3#1; NOTE: the keep-alive connection that sent PURGE kept getting the old entry, a fresh connection saw the purge |
caching| Serve stale on upstream error| `cache_stale_on_error`| ○| proxy-cache has no stale-if-error mode |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 345 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ✅| Content-Encoding=br 165 bytes (65536 uncompressed) |
compression| Zstandard compression| `compress_zstd`| ○| gzip and brotli plugins only |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=apisix X-Powered-By=removed Server=APISIX |
headers| Request ID generation| `request_id`| ✅| 'c62571c7-b404-4c7c-9c24-7b7c41b93196' / '22bf7084-6e75-48c4-afb4-4d8698e5ee40' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 6, 429: 34} |
security| Concurrent connection limit| `connection_limit`| ✅| codes={200: 3, 429: 9} |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="basic") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 200 ACAO=* methods=GET,POST,PUT,DELETE,OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.00s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.17 codes={200: 83, 503: 17} |
security| Bandwidth limiting| `bandwidth_limit`| ✅| 200 1048576 bytes in 1.98s (528 KB/s) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes', 'cache', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'status', 'time', 'ua', 'upstream'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 2803 samples e.g. apisix_bandwidth{type="egress",route="a",service="",consumer="",node="10.77.0.12 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /v1/routes -> 200 '[{"modifiedIndex":1789329706,"key":"/routes/a","value":{"priority":100,"hosts":[' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ✅| jaeger traces for service 'apisix': 5 |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider (APISIX Ingress Controller does this on Kubernetes) |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 10,546| 5.82| 19.0| 51.2| 0 / 0| 3.71| 352| 201| 2.9 / 1.1|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 3,662| 17.1| 41.1| 67.7| 0 / 0| 1.75| 476| 201| 1.2 / 7.0|  |
wrk reference: 8 threads, 64 connections, /small| ok| 11,329| 5.49| 17.1| 43.0| 0 / 0| 3.93| 347| 204| 3.0 / 0.8|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 10,158| 5.76| 16.3| 97.1| 0 / 0| 3.99| 393| 210| 2.8 / 1.2|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 10,878| 10.6| 28.2| 49.6| 1,232 / 0| 3.98| 366| 209| 3.0 / 1.5|  |
HTTP/3 (QUIC): 16 connections x 8 streams| ok| 9,083| 12.9| 28.0| 56.3| 810 / 0| 3.96| 435| 228| 2.5 / 2.6|  |
1 MiB responses, 32 connections (throughput MB/s)| ok| 1,028| 32.6| 44.8| 76.1| 0 / 0| 4.00| 3,890| 227| 1.4 / 3.0|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 4,788| 13.8| 29.7| 74.5| 0 / 0| 3.83| 801| 212| 3.5 / 0.6|  |
served from the proxy cache, 64 connections| ok| 11,591| 5.52| 16.7| 89.6| 0 / 0| 3.87| 334| 214| 0.1 / 1.3|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 104,346| 1.00| 3.00| 23.0| 0 / 0| 3.24| 31| 215| 5.0 / 7.8|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 9,213| 12.9| 33.6| 70.6| 0 / 0| 3.99| 434| 219| 3.3 / 2.5|  , 99.95, 41 > 0.05 <= 0.06 , 0.055 , 100.00, 68 > 0.06 <= 0.07 , 0.065 , 100.00, 5 > 0.07 <= 0.0706067 , 0.0703034 , 1… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,965| 0.93| 11.7| 19.4| 0 / 0| 2.68| 539| 217| 1.7 / 0.7| lse, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 128 Code 200 : 74493 (100.0 %) Response Header S… |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.74| 2.87| 6.12| 0 / 1,895| 0.20| 1,026| 249| 0.2 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 5,296| 1,687| 2,345| 22,017| 0 / 0| 3.82| 721| 1,290| 2.3 / 0.9|  |

## Apache httpd 2.4

- **image**: `httpd:2.4` (175 MB)
- **version**: `Server version: Apache/2.4.68 (Unix)`
- **family**: c — the classic modular web server (C) used as a reverse proxy: mod_proxy + balancer + hcheck + cache + md
- **reload mechanism**: signal (graceful restart: SIGUSR1, children finish their requests, new children read the new config)
- **startup**: 3.3 s
- **docs**: <https://hub.docker.com/_/httpd> · <https://httpd.apache.org/docs/2.4/mod/mod_proxy.html> · <https://httpd.apache.org/docs/2.4/mod/mod_proxy_balancer.html> · <https://httpd.apache.org/docs/2.4/mod/mod_md.html> · <https://httpd.apache.org/docs/2.4/mod/mod_cache.html>
- **notes**: Official httpd 2.4 image, event MPM sized for 4 cores. Demonstrates mod_proxy (http/h2c/ws/tls upstreams), mod_proxy_balancer (byrequests, bybusyness, loadfactor, stickysession, failonstatus), mod_proxy_hcheck active health checks, mod_cache_disk with CacheStaleOnError, mod_deflate + mod_brotli, mod_ratelimit bandwidth limiting, mod_remoteip PROXY protocol, mod_md ACME against Pebble (activated by a graceful reload from MDMessageCmd), mTLS with SSL_CLIENT_S_DN_CN, mod_unique_id request ids, JSON access log and a Prometheus exporter sidecar. No HTTP/3, no L4, no rate limiting, no JWT/forward auth without third-party modules.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=http://app.lab:18080/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab:18080/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ❌| slow share=0.33 {'app1': 100, 'app2': 100, 'slow': 100} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ○| mod_proxy_balancer has byrequests / bytraffic / bybusyness / heartbeat only - no consistent hashing |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=.a1; path=/; HttpOnly' first=app1 then={'app1': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=4 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 19, 500: 1} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 6.2s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 2.2s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ○| no request mirroring in mod_proxy |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app2': 2, 'app1': 3, 'app3': 1} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app2",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ○| no HTTP/3 in httpd (mod_http2 stops at HTTP/2) |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app1 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.21s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ✅| upstream proto=HTTP/2.0 |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| mod_proxy cannot send PROXY protocol to upstreams (mod_remoteip only accepts it) |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:60728 |
protocols| TCP (L4) proxying| `tcp_l4`| ○| httpd is HTTP-only (no generic TCP proxying) |
protocols| UDP proxying| `udp_l4`| ○| httpd is HTTP-only |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ○| no L4 passthrough (mod_proxy terminates or re-encrypts TLS) |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 80B70709F6790000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'lab-client', 'X-Client-Cert-Verify': 'SUCCESS'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ✅| subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
caching| Response caching| `cache_hit`| ✅| origin app1#1 -> app1#1; X-Cache: MISS from app.lab -> HIT from app.lab age=0 |
caching| Cache purge| `cache_purge`| ○| mod_cache has no purge API (htcacheclean works offline on the disk cache) |
caching| Serve stale on upstream error| `cache_stale_on_error`| ✅| first 200 origin=app2#1; after expiry with origin 503: 200 origin=app2#1 X-Cache=HIT from app.lab |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 345 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ✅| Content-Encoding=br 98 bytes (65536 uncompressed) |
compression| Zstandard compression| `compress_zstd`| ○| no zstd output filter (mod_deflate = gzip, mod_brotli = br) |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab:18080' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=apache X-Powered-By=removed Server=lab-backend/1.0 |
headers| Request ID generation| `request_id`| ✅| 'aqb7z3J1sg6HPRY-VQeDMgAAAes' / 'aqb7z3J1sg6HPRY-VQeDMwAAAds' |
security| Request rate limiting| `rate_limit`| ○| no request-rate limiting in the standard modules (mod_ratelimit is bandwidth only; mod_qos / mod_evasive are third-party) |
security| Concurrent connection limit| `connection_limit`| ○| no per-client concurrency limit in the standard modules (mod_qos is third-party) |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ○| JWT validation needs a third-party module (mod_auth_openidc, mod_authnz_jwt) |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ○| no auth_request-style subrequest to an external authorizer in httpd core |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=* methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 502 after 2.01s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.18 codes={200: 82, 503: 18} |
security| Bandwidth limiting| `bandwidth_limit`| ✅| 200 1048576 bytes in 2.01s (522 KB/s) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes', 'cache', 'duration_us', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'status', 'time', 'ua', 'uri'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 83 samples e.g. apache_accesses_total 1130 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /server-status?auto -> 200 '127.0.0.1\nServerVersion: Apache/2.4.68 (Unix) OpenSSL/3.5.6\nServerMPM: event\nSer' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ○| the OpenTelemetry Apache module (otel-webserver-module) is a separate build |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 12,858| 4.59| 11.7| 52.0| 0 / 0| 3.93| 306| 73| 3.6 / 1.3|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 3,743| 16.4| 41.3| 73.3| 0 / 0| 1.53| 410| 77| 1.3 / 7.2|  |
wrk reference: 8 threads, 64 connections, /small| ok| 19,574| 3.07| 6.77| 17.3| 0 / 0| 3.92| 200| 78| 4.2 / 1.3|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 11,616| 5.04| 13.2| 129| 0 / 0| 3.92| 337| 97| 3.4 / 1.4|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 7,010| 14.1| 60.0| 141| 0 / 0| 3.19| 455| 108| 2.4 / 0.4|  |
| HTTP/3 (QUIC): 16 connections x 8 streams | unsupported | – | – | – | – | – | – | – | – | no HTTP/3 in httpd (mod_http2 stops at HTTP/2) |
1 MiB responses, 32 connections (throughput MB/s)| ok| 1,631| 13.7| 69.7| 137| 0 / 0| 3.98| 2,439| 113| 2.3 / 3.3|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 5,519| 9.88| 37.9| 112| 0 / 0| 3.93| 711| 122| 3.7 / 0.7|  |
served from the proxy cache, 64 connections| ok| 19,537| 0.75| 17.3| 52.3| 0 / 0| 3.63| 186| 122| 0.1 / 1.9|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 65,424| 1.00| 3.00| 18.0| 0 / 0| 3.93| 60| 124| 4.5 / 5.8|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 6,928| 15.8| 60.0| 122| 0 / 0| 3.28| 474| 127| 3.0 / 1.3| 0.085 , 99.95, 76 > 0.09 <= 0.1 , 0.095 , 99.98, 29 > 0.1 <= 0.12 , 0.11 , 100.00, 18 > 0.12 <= 0.121893 , 0.120947 , 1… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,996| 0.62| 1.74| 5.71| 0 / 0| 2.28| 456| 127| 2.0 / 0.8| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
| /limited (10 r/s) hammered at 200 rps for 10 s: how many get through | unsupported | – | – | – | – | – | – | – | – | no request-rate limiting in the standard modules (mod_ratelimit is bandwidth only; mod_qos / mod_evasive are third-part… |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 464| 503| 61,412| 61,922| 12,843 / 0| 0.26| 562| 85| 0.3 / 0.1|  |

## Apache Traffic Server 9.2

- **image**: `pxlab-ats:latest` (235 MB)
- **version**: `Traffic Server 9.2.3 Feb 12 2026 02:40:38 localhost`
- **family**: cache — CDN-grade caching proxy (C++): remap rules, NextHop strategies, plugins (Yahoo/Apple/Comcast lineage)
- **reload mechanism**: cli (traffic_ctl config reload re-reads remap.config / records.config / plugins without restart)
- **startup**: 6.1 s
- **docs**: <https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/configuration/index.en.html> · <https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/files/remap.config.en.html> · <https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/files/strategies.yaml.en.html> · <https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/plugins/header_rewrite.en.html> · <https://docs.trafficserver.apache.org/en/9.2.x/admin-guide/files/sni.yaml.en.html>
- **notes**: ATS 9.2.3 from Ubuntu packages. remap.config is generated from remap.spec because ATS compares the request URL's port with the from-URL; NextHop strategies.yaml provides round-robin, weights and passive failover; header_rewrite does routing by header/query, method 405, IP lists, basic auth, body limit, fault injection, CORS and security headers; conf_remap sets per-remap timeouts, fq_pacing paces bandwidth, rate_limit.so caps concurrency, multiplexer mirrors, statichit serves a file, sslheaders exposes the client certificate, compress.so does gzip/brotli, sni.yaml gives mTLS and SNI tunnels, and stats_over_http/traffic_ctl are the admin surface. JSON access log through logging.yaml to stdout.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=http://app.lab/landing |
routing| Header-based routing| `route_header`| ○| remap has no header/query conditions and header_rewrite's set-destination is overridden by the NextHop strategy that picks the origin |
routing| Query-parameter routing| `route_query`| ○| see route_header |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ○| strategies apply weights only to consistent_hash (same URL -> same host); there is no weighted round-robin in 9.2 |
load-balancing| Least-connections| `lb_least_conn`| ○| NextHop strategies offer rr_strict / rr_ip / first_live / latched / consistent_hash - no least-connections |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ○| consistent_hash keys are url / path / cache_key / hostname - a request header cannot be the key |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ○| no cookie stickiness (cookie_remap can route on cookies but does not set them) |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=22 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ○| strategies failover retries 5xx on the next host (errors hidden) but markdown_codes did not take the flaky host out of rotation in 9.2.3 |
load-balancing| Active health checks| `lb_active_health`| ○| ATS 9 strategies only do passive health (active origin checks arrived with ATS 10) |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ○| no weighted round-robin (see lb_weighted); a canary needs the consistent-hash weights on varying keys |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ✅| shadow received 20/20 |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app2': 1, 'app1': 1, 'app3': 1} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ○| cleartext HTTP/2 is not supported on plain ports (h2 via ALPN only) |
protocols| HTTP/3 (QUIC)| `http3`| ○| the Ubuntu build has no QUIC (experimental in 9.x, needs quiche) |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app1 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.20s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ○| no HTTP/2 to origins, so no gRPC proxying |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ○| ATS 9 speaks HTTP/1.1 to origins |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| no PROXY protocol towards origins in 9.2 |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:58464 |
protocols| TCP (L4) proxying| `tcp_l4`| ○| ATS is an HTTP proxy (sni.yaml tunnel_route is the only L4 feature) |
protocols| UDP proxying| `udp_l4`| ○| HTTP only |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 80C741128C710000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'Client-Ip': '10.77.0.1', 'X-Client-Cert-Issuer': 'CN = pxlab CA, O = pxlab', 'X-Client-Cert-Subject': 'CN = lab-client, O = pxlab'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ○| acme.so only serves challenge files; there is no ACME client |
caching| Response caching| `cache_hit`| ✅| origin app1#1 -> app1#1; X-Cache: miss -> hit-fresh age=0 |
caching| Cache purge| `cache_purge`| ✅| purge -> 200; origin app2#1 -> app3#1 |
caching| Serve stale on upstream error| `cache_stale_on_error`| ✅| first 200 origin=app1#1; after expiry with origin 503: 200 origin=app1#1 X-Cache=hit-fresh |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 380 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ○| the Ubuntu compress.so is built without brotli (gzip only) |
compression| Zstandard compression| `compress_zstd`| ○| compress.so does gzip and brotli |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab:18080' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=ats X-Powered-By=removed Server=ats |
headers| Request ID generation| `request_id`| ✅| 'f6f8202f-6652-49c4-8155-7153cd506fac-193' / 'f6f8202f-6652-49c4-8155-7153cd506fac-194' |
security| Request rate limiting| `rate_limit`| ○| rate_limit.so limits concurrency per remap, not requests per second per client |
security| Concurrent connection limit| `connection_limit`| ✅| codes={200: 3, 429: 9} |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (None) creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ○| no JWT validation plugin (uri_signing.so signs URLs; tslua could do it) |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ○| authproxy.so forwards the ORIGINAL path to the authorizer, which does not fit the lab's /auth service |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=* methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.86s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.14 codes={503: 14, 200: 86} |
security| Bandwidth limiting| `bandwidth_limit`| ○| fq_pacing.so needs the kernel fq qdisc (SO_MAX_PACING_RATE) on the interface, which a container does not have |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ○| origin error bodies pass through; body_factory only styles ATS-generated errors |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes', 'cache', 'duration_ms', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'status', 'time', 'ua', 'upstream'] |
operations| Prometheus metrics| `metrics_prometheus`| ○| stats_over_http.so exposes JSON at /_stats; Prometheus needs an exporter |
operations| Admin / stats / runtime API| `admin_api`| ✅| rc=0 'proxy.process.http.current_active_client_connections 0' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ○| no OpenTelemetry |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 27,938| 2.12| 4.46| 35.3| 0 / 0| 3.78| 135| 195| 4.7 / 2.8|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 4,507| 13.5| 41.8| 75.8| 0 / 0| 1.20| 266| 216| 1.4 / 7.6|  |
wrk reference: 8 threads, 64 connections, /small| ok| 31,729| 1.81| 20.0| 25.9| 0 / 0| 3.63| 114| 340| 4.7 / 2.0|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 21,403| 2.79| 5.85| 117| 0 / 0| 3.80| 178| 429| 4.5 / 3.0|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 24,182| 5.04| 14.6| 33.7| 0 / 0| 3.87| 160| 536| 4.3 / 1.8|  |
| HTTP/3 (QUIC): 16 connections x 8 streams | unsupported | – | – | – | – | – | – | – | – | the Ubuntu build has no QUIC (experimental in 9.x, needs quiche) |
1 MiB responses, 32 connections (throughput MB/s)| ok| 3,703| 8.55| 11.9| 39.4| 0 / 0| 4.00| 1,080| 554| 4.1 / 3.4|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 5,794| 11.0| 15.1| 49.1| 0 / 0| 4.00| 690| 579| 4.0 / 1.1|  |
served from the proxy cache, 64 connections| ok| 52,600| 1.13| 2.38| 24.0| 0 / 0| 4.00| 76| 801| 0.1 / 3.8|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 96,681| 1.00| 3.00| 18.0| 0 / 0| 3.66| 38| 804| 5.2 / 7.2|  |
| gRPC Health/Check over TLS: 16 connections x 8 streams (fortio) | unsupported | – | – | – | – | – | – | – | – | no HTTP/2 to origins, so no gRPC proxying |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,992| 1.41| 3.94| 12.5| 0 / 0| 1.93| 386| 826| 1.9 / 0.7| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
| /limited (10 r/s) hammered at 200 rps for 10 s: how many get through | unsupported | – | – | – | – | – | – | – | – | rate_limit.so limits concurrency per remap, not requests per second per client |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 9,127| 1,041| 1,340| 1,588| 0 / 0| 2.35| 258| 4,442| 1.9 / 1.0|  |

## Caddy 2

- **image**: `pxlab-caddy:latest` (160 MB)
- **version**: `v2.11.4 h1:XKxkMTgNSizEvKG6QHue6cAsFOteU2qA61w2tKkCWi0=`
- **family**: go — web server / reverse proxy (Go) with automatic HTTPS; extended with xcaddy plugins
- **reload mechanism**: api (caddy reload pushes the config through the admin API; zero-downtime, listeners kept)
- **startup**: 3.4 s
- **docs**: <https://hub.docker.com/_/caddy> · <https://caddyserver.com/docs/caddyfile/directives/reverse_proxy> · <https://caddyserver.com/docs/caddyfile/options> · <https://github.com/mholt/caddy-ratelimit> · <https://github.com/mholt/caddy-l4> · <https://github.com/caddyserver/cache-handler> · <https://github.com/ggicci/caddy-jwt>
- **notes**: Caddy 2 built with xcaddy: caddy-ratelimit, caddy-l4 (TCP/UDP/SNI passthrough), caddy-jwt, caddy-brotli and the Souin cache-handler (Caddy has no built-in cache). Automatic HTTPS stays on for acme.lab only (Pebble issuer, HTTP-01 on :80); every other site carries explicit certificates because Caddy would otherwise try to get Let's Encrypt certs for *.lab. h1/h2/h2c/h3 are enabled on the plain and TLS listeners; PROXY protocol is accepted on :8082 through a listener wrapper.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.02 {'slow': 6, 'app1': 150, 'app2': 144} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app3': 20}; 10 users -> {'app2': 9, 'app1': 15, 'app3': 6} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=916340cf243f672cd49155ba442cfd74ef69cbc40906c1aa6' first=app1 then={'app1': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=57 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 17, 500: 3} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 3.1s; while unhealthy: {'app2': 15, 'app1': 15} app3 hits=0; re-admitted after 3.7s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ○| no request mirroring / shadowing in reverse_proxy |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app3': 1, 'app2': 1, 'app1': 1} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app3",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ✅| proto=HTTP/3.0 status={'200': 677} errors=0 [] |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app1 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.20s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ✅| upstream proto=HTTP/2.0 |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'h2'} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ✅| listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 0, 'dst_ip': '0.0.0.0', 'dst_port': 0, 'protocol': '0x11'} |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:36410 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:48328 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ✅| echo:app1:ping-a6f7d1 |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_128_GCM_SHA256 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 80175DFDBC7A0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'CN=lab-client,O=pxlab'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ✅| subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
caching| Response caching| `cache_hit`| ✅| origin app2#1 -> app2#1; Cache-Status: Souin; fwd=uri-miss; stored; key=GET-http-app.lab:18080-/cacheable/a6f7d1 -> Souin; hit; ttl=59; key=GET-http-app.lab:18080-/cacheable/a6f7d1; detail=DEFAULT age=1 |
caching| Cache purge| `cache_purge`| ✅| purge -> 200; origin app3#1 -> app2#1 |
caching| Serve stale on upstream error| `cache_stale_on_error`| ✅| first 200 origin=app2#1; after expiry with origin 503: 200 origin=app2#1 Cache-Status=Souin; hit; ttl=-2; key=GET-http-app.lab:18080-/cacheable-short/a6f7d1; detail=DEFAULT; fwd=stale; fwd-status=503 |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 352 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ✅| Content-Encoding=br 417 bytes (65536 uncompressed) |
compression| Zstandard compression| `compress_zstd`| ✅| Content-Encoding=zstd 102 bytes (65536 uncompressed) |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=caddy X-Powered-By=removed Server=None |
headers| Request ID generation| `request_id`| ✅| '10942b52-3cc8-4cb8-882b-6220fda9920c' / '3b1d235e-dc0a-4447-b9a3-660ecc33a91d' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 10, 429: 30} |
security| Concurrent connection limit| `connection_limit`| ○| no per-client concurrency limit (caddy-ratelimit is a request-rate limiter only) |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="restricted") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.01s |
security| Fault injection| `fault_injection`| ○| no fault-injection primitive (a CEL matcher cannot draw random numbers); needs a plugin |
security| Bandwidth limiting| `bandwidth_limit`| ○| no bandwidth/throughput limiting |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 '{"level":"info","ts":1789327334.420578,"msg":"using config from file","file":"/etc/caddy/Caddyfile"}\n{"level":"info","ts'; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes_read', 'duration', 'level', 'logger', 'msg', 'request', 'resp_headers', 'size', 'spanID', 'status', 'traceID', 'ts'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 1093 samples e.g. caddy_admin_http_requests_total{code="200",handler="admin",method="POST",path="/ |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /config/ -> 200 '{"admin":{"listen":"0.0.0.0:2019"},"apps":{"cache":{"Storers":null,"SurrogateKey' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ✅| jaeger traces for service 'caddy': 3 |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| caddy-docker-proxy (lucaslorentz) is a separate distribution that generates the Caddyfile from labels |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 11,299| 4.70| 18.1| 41.0| 0 / 0| 3.90| 345| 49| 3.1 / 1.2|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 3,719| 15.2| 44.6| 73.2| 0 / 0| 1.98| 532| 43| 1.3 / 7.0|  |
wrk reference: 8 threads, 64 connections, /small| ok| 11,639| 5.02| 18.3| 41.3| 0 / 0| 3.85| 331| 48| 3.1 / 0.8|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 11,036| 4.73| 19.4| 97.3| 0 / 0| 3.82| 346| 51| 3.0 / 1.3|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 9,113| 12.8| 36.1| 68.0| 0 / 0| 3.87| 425| 56| 2.7 / 1.6|  |
HTTP/3 (QUIC): 16 connections x 8 streams| ok| 9,456| 12.3| 33.9| 67.2| 0 / 0| 3.90| 412| 51| 2.7 / 2.0|  |
1 MiB responses, 32 connections (throughput MB/s)| ok| 2,966| 9.29| 32.4| 68.8| 0 / 0| 3.85| 1,299| 55| 3.5 / 2.7|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 9,311| 5.88| 21.9| 50.8| 0 / 0| 3.89| 418| 85| 4.2 / 1.0|  |
served from the proxy cache, 64 connections| ok| 1,662| 21.1| 199| 505| 0 / 0| 3.89| 2,340| 331| 0.2 / 0.3|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 78,878| 1.00| 4.00| 18.0| 0 / 0| 3.20| 40| 70| 4.7 / 6.3|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 6,947| 17.4| 29.3| 55.7| 0 / 0| 3.80| 547| 63| 2.1 / 2.8| 9.92, 40 > 0.04 <= 0.045 , 0.0425 , 99.97, 59 > 0.045 <= 0.05 , 0.0475 , 99.99, 14 > 0.05 <= 0.0557137 , 0.0528569 , 10… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,992| 0.70| 5.20| 23.6| 0 / 0| 2.26| 452| 50| 1.8 / 0.7| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74897 (100.0 … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.70| 1.71| 4.62| 0 / 1,901| 0.23| 1,139| 48| 0.2 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 3,761| 1,842| 6,257| 8,142| 0 / 5,466| 3.84| 1,021| 1,998| 1.9 / 0.5|  |

## Envoy 1.39

- **image**: `envoyproxy/envoy:v1.39-latest` (293 MB)
- **version**: `envoy  version: b579d07d3ad7ee11d32b105e91a5a39ad24718d7/1.39.1/Clean/RELEASE/BoringSSL`
- **family**: envoy — cloud-native L4/L7 proxy (C++): the data plane of Istio & co, configured through xDS
- **reload mechanism**: xds-file-watch (a new rds.yaml version is picked up by the watched directory and swapped in without restart)
- **startup**: 2.9 s
- **docs**: <https://hub.docker.com/r/envoyproxy/envoy> · <https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/http_filters> · <https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/load_balancing> · <https://www.envoyproxy.io/docs/envoy/latest/configuration/overview/xds_api> · <https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/http_conn_man>
- **notes**: Official Envoy image with a bootstrap + file-based xDS (LDS/CDS/RDS files in a watched directory: bumping a version is the reload). lds.yaml is generated from lds.src.yaml because Envoy's YAML parser has no merge keys. Demonstrates ExtensionWithMatcher (ext_authz / basic_auth only where wanted), per-route filter configs (fault, local rate limit, RBAC, buffer, bandwidth limit, Lua error page, JWT), ring-hash cookies, outlier detection, mirroring, weighted clusters, h2c/TLS/PROXY-protocol upstreams, QUIC/HTTP/3, UDP proxy, OTel tracing and JSON access logs.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app1 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=http://app.lab/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 308 Location=https://redirect.lab:8443/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app2': 25, 'app1': 75} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.05 {'slow': 16, 'app2': 145, 'app1': 139} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app2': 20}; 10 users -> {'app1': 12, 'app2': 9, 'app3': 9} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky="0604085547a40599"; Max-Age=3600; Path=/; HttpOnl' first=app1 then={'app1': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=29 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 1.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 2.2s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.085 {'app1': 92, 'app2': 91, 'canary': 17} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ✅| shadow received 20/20 |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app3': 2, 'app2': 2, 'app1': 1} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ✅| proto=HTTP/3.0 status={'200': 933} errors=0 [] |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app2 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.21s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ✅| upstream proto=HTTP/2.0 |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.2', 'sni': 'backend.lab', 'alpn': 'http/1.1'} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ✅| listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 48844, 'dst_ip': '10.77.0.2', 'dst_port': 8080, 'protocol': '0x11'} |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:53348 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:33056 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ✅| echo:app1:ping-a705b8 |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 8097564FCB7F0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client', 'X-Forwarded-Client-Cert': 'Hash=b5b0abe3c4cbc70e95d53bec923720b854f94b69c2db078d93fba7d7e55b6f07;Subject="O=pxlab,CN=lab-client"'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ○| no ACME client in Envoy (certificates come from SDS / a control plane such as cert-manager) |
caching| Response caching| `cache_hit`| ○| the HTTP cache filter is alpha; in 1.39 it makes its own internal upstream request that bypasses route-level header mutations, redirects and direct responses for every route (breaks 20+ probes), so it is left out |
caching| Cache purge| `cache_purge`| ○| no cache filter in use (and the alpha cache filter has no invalidation API) |
caching| Serve stale on upstream error| `cache_stale_on_error`| ○| no cache filter in use (and the alpha cache filter has no stale-if-error mode) |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 690 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ✅| Content-Encoding=br 100 bytes (65536 uncompressed) |
compression| Zstandard compression| `compress_zstd`| ✅| Content-Encoding=zstd 99 bytes (65536 uncompressed) |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=envoy X-Powered-By=removed Server=envoy |
headers| Request ID generation| `request_id`| ✅| 'a1f68bef-f89f-4ad4-8957-93a09c62606e' / '66703245-e9c1-4846-8bab-d6b3975c2dd9' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 15, 429: 25} |
security| Concurrent connection limit| `connection_limit`| ○| the connection_limit network filter is per listener; per-client concurrency needs the global rate-limit service |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="http://app.lab/basic") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 200 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.00s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.17 codes={200: 83, 503: 17} |
security| Bandwidth limiting| `bandwidth_limit`| ❌| 200 1048576 bytes in 1.13s (928 KB/s) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['authority', 'bytes_sent', 'client', 'duration_ms', 'flags', 'method', 'path', 'protocol', 'request_id', 'status', 'time', 'ua'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 6286 samples e.g. envoy_bw_http_bandwidth_limit_request_allowed_total_size{} 0 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /server_info -> 200 '{\n "version": "b579d07d3ad7ee11d32b105e91a5a39ad24718d7/1.39.1/Clean/RELEASE/Bor' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ✅| jaeger traces for service 'envoy': 5 |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider; endpoints come from xDS (or STRICT_DNS as here) |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 18,582| 3.43| 5.91| 36.3| 0 / 0| 3.99| 215| 34| 4.3 / 1.9|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 6,270| 9.74| 24.6| 47.7| 0 / 0| 1.95| 311| 40| 2.0 / 3.0|  |
wrk reference: 8 threads, 64 connections, /small| ok| 18,995| 3.25| 5.50| 13.5| 0 / 0| 3.99| 210| 40| 4.4 / 1.4|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 17,336| 3.50| 6.10| 80.3| 0 / 0| 3.98| 229| 39| 4.3 / 2.1|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 21,090| 5.88| 9.71| 21.1| 0 / 0| 3.94| 187| 40| 4.0 / 1.0|  |
HTTP/3 (QUIC): 16 connections x 8 streams| ok| 10,252| 13.2| 22.1| 42.4| 0 / 0| 3.98| 388| 44| 3.0 / 3.2|  |
1 MiB responses, 32 connections (throughput MB/s)| ok| 3,642| 8.52| 13.7| 27.4| 0 / 0| 4.00| 1,098| 76| 4.0 / 2.6|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 8,832| 6.79| 13.0| 27.5| 0 / 0| 4.00| 453| 82| 4.4 / 1.2|  |
| served from the proxy cache, 64 connections | unsupported | – | – | – | – | – | – | – | – | the HTTP cache filter is alpha; in 1.39 it makes its own internal upstream request that bypasses route-level header mut… |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 84,220| 1.00| 3.00| 18.0| 0 / 0| 3.73| 44| 82| 4.7 / 6.6|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 19,294| 6.05| 13.8| 21.8| 0 / 0| 3.86| 200| 82| 3.4 / 2.7| , 1613 > 0.016 <= 0.018 , 0.017 , 99.95, 387 > 0.018 <= 0.02 , 0.019 , 99.99, 123 > 0.02 <= 0.0218296 , 0.0209148 , 100… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,995| 1.37| 3.69| 8.58| 0 / 0| 2.61| 522| 82| 1.9 / 0.7| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.62| 1.63| 1.79| 0 / 1,887| 0.12| 596| 83| 0.1 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 8,576| 1,145| 1,856| 2,043| 0 / 0| 2.82| 329| 1,380| 2.5 / 0.9|  |

## HAProxy 3.4

- **image**: `haproxy:lts` (185 MB)
- **version**: `HAProxy version 3.4.4-7f03ae6 2026/08/27 - https://haproxy.org/`
- **family**: haproxy — TCP/HTTP load balancer (C, event-driven, multi-threaded); the reference L4/L7 balancer
- **reload mechanism**: signal (SIGUSR2 to the master → new worker with the new config, listeners handed over via expose-fd, old worker drains)
- **startup**: 2.9 s
- **docs**: <https://hub.docker.com/_/haproxy> · <https://docs.haproxy.org/3.4/configuration.html> · <https://github.com/haproxy/wiki/wiki/ACME:--native-haproxy> · <https://www.haproxy.com/documentation/haproxy-configuration-tutorials/>
- **notes**: Official HAProxy LTS image (3.4.4): QUIC/HTTP/3 through OpenSSL 3.5's native QUIC API, ACME client (experimental, crt-store starts with a temporary key pair until Pebble issues the certificate), Lua forward-auth through the internal httpclient, jwt_verify for JWTs, stick-tables for rate/connection limits, bwlim filter, built-in cache and Prometheus exporter. Master-worker mode makes `kill -USR2 1` a seamless reload. No UDP, no mirroring, no purge, gzip only.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab:18080/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.03 {'slow': 8, 'app2': 147, 'app1': 145} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app3': 20}; 10 users -> {'app1': 15, 'app2': 9, 'app3': 6} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=a1; path=/; HttpOnly' first=app1 then={'app1': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=3 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 2.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.1s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ○| no native request mirroring; use tcp-level tee or SPOE + an external agent |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app2': 2, 'app1': 2, 'app3': 1} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ✅| proto=HTTP/3.0 status={'200': 1025} errors=0 [] |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app2 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.21s total=1.20s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ✅| upstream proto=HTTP/2.0 |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'http/1.1'} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ✅| listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 33228, 'dst_ip': '10.77.0.2', 'dst_port': 8080, 'protocol': '0x11'} |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:33726 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:49882 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ○| HAProxy proxies TCP and QUIC only; there is no generic UDP proxying (only syslog/DNS forwarding) |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 80070F3C2A780000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'lab-client', 'X-Client-Cert-Verify': '0'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ✅| subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
caching| Response caching| `cache_hit`| ✅| origin app1#1 -> app1#1; X-Cache: MISS -> HIT age=0 |
caching| Cache purge| `cache_purge`| ○| the built-in cache is a small-object accelerator without an invalidation API; entries expire by max-age (or reload) |
caching| Serve stale on upstream error| `cache_stale_on_error`| ○| the cache has no stale-if-error / grace mode; an expired entry is refetched and the origin's 503 is returned |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 1544 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ○| compression uses libslz (gzip/deflate only); no brotli or zstd support |
compression| Zstandard compression| `compress_zstd`| ○| no zstd (slz only) |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='proto=http;host="app.lab:18080";for=10.77.0.1' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=haproxy X-Powered-By=removed Server=haproxy |
headers| Request ID generation| `request_id`| ✅| '0A4D0001:81AE_0A4D0002:1F90_6AA6F689_07EA:0008' / '0A4D0001:81AE_0A4D0002:1F90_6AA6F689_07EB:0008' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 10, 429: 30} |
security| Concurrent connection limit| `connection_limit`| ✅| codes={200: 3, 429: 9} |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.00s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.24 codes={200: 76, 503: 24} |
security| Bandwidth limiting| `bandwidth_limit`| ✅| 200 1048576 bytes in 2.10s (499 KB/s) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['backend', 'bytes', 'client_ip', 'frontend', 'method', 'proto', 'request_id', 'server', 'ssl', 'status', 'time', 'time_ms'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 4525 samples e.g. haproxy_process_nbthread 4 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /stats -> 200 '<!DOCTYPE html>\n<html lang="en"><head><title>Statistics Report for HAProxy</titl' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ○| no OpenTelemetry exporter in the official build (the OpenTracing filter needs a separate addon build) |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider; the Data Plane API / Ingress Controller do this in other setups |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 31,887| 1.98| 3.10| 22.3| 0 / 0| 3.99| 125| 306| 4.1 / 2.4|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 21,763| 2.88| 5.70| 18.4| 0 / 0| 3.97| 182| 307| 3.4 / 5.3|  |
wrk reference: 8 threads, 64 connections, /small| ok| 35,051| 1.79| 3.00| 11.3| 0 / 0| 3.99| 114| 306| 4.3 / 1.8|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 27,703| 2.29| 3.11| 109| 0 / 0| 3.98| 144| 310| 3.8 / 2.5|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 27,945| 4.50| 6.82| 23.0| 0 / 0| 3.98| 142| 311| 4.0 / 2.4|  |
HTTP/3 (QUIC): 16 connections x 8 streams| ok| 30,221| 4.11| 8.23| 28.2| 0 / 0| 3.80| 126| 309| 4.1 / 5.0|  |
1 MiB responses, 32 connections (throughput MB/s)| ok| 2,257| 13.9| 21.9| 54.4| 0 / 0| 3.98| 1,763| 309| 3.0 / 6.0|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 12,847| 4.91| 6.69| 22.8| 0 / 0| 4.00| 311| 308| 4.8 / 1.9|  |
served from the proxy cache, 64 connections| ok| 56,216| 1.05| 1.64| 22.1| 0 / 0| 4.00| 71| 310| 0.2 / 3.6|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 102,366| 1.00| 3.00| 21.0| 0 / 0| 3.67| 36| 310| 4.9 / 7.7|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 20,341| 6.29| 8.87| 26.6| 0 / 0| 3.99| 196| 310| 4.1 / 3.6| , 155 > 0.018 <= 0.02 , 0.019 , 99.97, 95 > 0.02 <= 0.025 , 0.0225 , 100.00, 85 > 0.025 <= 0.0265828 , 0.0257914 , 100.… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,996| 0.61| 1.69| 4.90| 0 / 0| 1.73| 346| 311| 1.9 / 0.8| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.36| 0.52| 1.97| 0 / 1,991| 0.08| 414| 310| 0.1 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 18,936| 502| 997| 1,096| 0 / 0| 3.10| 164| 746| 3.7 / 2.0|  |

## Kong Gateway 3.9

- **image**: `kong:3.9` (528 MB)
- **version**: `3.9.3`
- **family**: api-gateway — API gateway on OpenResty (Lua plugins): routes/services/upstreams/consumers/plugins, DB-less declarative config
- **reload mechanism**: api (POST /config on the admin API re-applies the declarative file atomically; `kong reload` only HUPs nginx and does NOT re-read it)
- **startup**: 4.4 s
- **docs**: <https://hub.docker.com/_/kong> · <https://docs.konghq.com/gateway/latest/production/deployment-topologies/db-less-and-declarative-config/> · <https://docs.konghq.com/gateway/latest/key-concepts/routes/expressions/> · <https://docs.konghq.com/hub/> · <https://docs.konghq.com/gateway/latest/reference/configuration/>
- **notes**: Kong Gateway OSS 3.9 in DB-less mode with the expressions router. Upstreams demonstrate round-robin / weighted / least-connections / consistent-hashing (header, cookie stickiness), active + passive health checks and retries; bundled plugins cover rate limiting, IP restriction, basic auth, JWT, CORS, request/response transformers, proxy-cache (+ admin purge), request size limiting, correlation-id, prometheus, opentelemetry and acme (Pebble); pre/post-function serverless plugins do redirects, 405, fault injection, static files and the custom error page. Stream routes give TCP, UDP and TLS passthrough.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app1 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app2': 10, 'app3': 10, 'app1': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.05 {'app1': 139, 'app2': 145, 'slow': 16} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app2': 20}; 10 users -> {'app1': 9, 'app3': 12, 'app2': 9} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=f1c67503-dc16-43e8-b915-9fab0d301660; Path=/; Sam' first=app2 then={'app2': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=5 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 17, 500: 3} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 2.1s; while unhealthy: {'app2': 15, 'app1': 15} app3 hits=0; re-admitted after 1.6s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.100 {'app1': 60, 'app3': 60, 'app2': 60, 'canary': 20} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ○| no traffic mirroring in Kong OSS |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app1': 2, 'app3': 2, 'app2': 1} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ○| no HTTP/3 in Kong Gateway 3.9 OSS |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app2 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.21s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ○| HTTP/2 to upstreams only for gRPC services (protocol grpc/grpcs) |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| Kong cannot send PROXY protocol to upstreams |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:56778 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:48750 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ✅| echo:app1:ping-a6fff2 |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 806756E04D7D0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ○| mtls-auth is a Kong Enterprise plugin; nginx-level ssl_verify_client would apply to every TLS listener |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ✅| subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
caching| Response caching| `cache_hit`| ✅| origin app2#1 -> app2#1; X-Cache-Status: Miss -> Hit age=0 |
caching| Cache purge| `cache_purge`| ✅| purge -> 204; origin app1#1 -> app3#1 |
caching| Serve stale on upstream error| `cache_stale_on_error`| ○| proxy-cache has no stale-if-error mode |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 611 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ○| gzip only (nginx gzip injected through KONG_NGINX_PROXY_GZIP) |
compression| Zstandard compression| `compress_zstd`| ○| gzip only |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=kong X-Powered-By=removed Server=lab-backend/1.0 |
headers| Request ID generation| `request_id`| ✅| 'b349ff86-f185-4cd5-a062-5046e908601f' / '41ae2ab5-ab09-4063-9f0e-b22c4304bda3' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 10, 429: 30} |
security| Concurrent connection limit| `connection_limit`| ○| no per-client concurrency limit in OSS (rate-limiting is per request) |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ○| no forward-auth plugin in Kong OSS (openid-connect is Enterprise; write a pre-function with lua-resty-http) |
security| CORS preflight answered by the proxy| `cors`| ✅| 200 ACAO=* methods=GET,POST,PUT,DELETE,OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.01s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.28 codes={200: 72, 503: 28} |
security| Bandwidth limiting| `bandwidth_limit`| ○| no bandwidth limiting (response-ratelimiting counts requests) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'status', 'time', 'ua', 'upstream', 'upstream_time'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 1972 samples e.g. kong_bandwidth_bytes{service="app",route="a",direction="egress",workspace="defau |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /status -> 200 '{"server":{"connections_active":15,"total_requests":1154,"connections_reading":0' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ✅| jaeger traces for service 'kong': 5 |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider (Kong Ingress Controller does this on Kubernetes) |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 10,394| 5.35| 16.8| 61.1| 0 / 0| 4.00| 384| 1,036| 2.9 / 1.1|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 3,653| 16.0| 46.5| 82.0| 0 / 0| 1.86| 510| 1,029| 1.3 / 6.9|  |
wrk reference: 8 threads, 64 connections, /small| ok| 10,798| 6.18| 17.7| 42.5| 0 / 0| 4.01| 371| 1,040| 2.9 / 0.8|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 8,770| 6.99| 18.5| 168| 0 / 0| 3.96| 451| 1,040| 2.6 / 1.1|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 9,212| 13.8| 44.1| 82.0| 48 / 0| 3.80| 413| 1,045| 2.6 / 1.3|  |
| HTTP/3 (QUIC): 16 connections x 8 streams | unsupported | – | – | – | – | – | – | – | – | no HTTP/3 in Kong Gateway 3.9 OSS |
1 MiB responses, 32 connections (throughput MB/s)| ok| 1,377| 21.2| 43.6| 91.0| 0 / 0| 4.00| 2,903| 1,048| 1.9 / 3.1|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 6,239| 10.1| 23.3| 54.0| 0 / 0| 3.99| 639| 1,052| 4.0 / 0.8|  |
served from the proxy cache, 64 connections| ok| 11,389| 5.64| 15.3| 40.9| 0 / 0| 3.99| 351| 1,052| 0.1 / 1.3|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 103,775| 1.00| 3.00| 20.0| 0 / 0| 3.28| 32| 1,054| 4.9 / 7.7|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 7,711| 15.3| 38.7| 75.7| 0 / 0| 3.99| 518| 1,065| 3.0 / 2.5| 5 , 99.88, 90 > 0.05 <= 0.06 , 0.055 , 99.94, 62 > 0.06 <= 0.07 , 0.065 , 99.98, 53 > 0.07 <= 0.0757207 , 0.0728604 , 1… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,959| 0.84| 9.44| 41.4| 0 / 0| 2.76| 557| 1,059| 1.7 / 0.7| , Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74394 (100.0 %) Response Header Sizes… |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.88| 2.72| 3.71| 0 / 1,891| 0.26| 1,310| 1,060| 0.1 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 7,857| 1,198| 1,761| 2,067| 0 / 0| 3.88| 494| 1,338| 3.2 / 1.1|  |

## NGINX 1.29

- **image**: `nginx:1.29-otel` (250 MB)
- **version**: `nginx version: nginx/1.29.8`
- **family**: nginx — event-driven web server / reverse proxy (C); the most deployed proxy on the internet
- **reload mechanism**: signal (SIGHUP — new workers start with the new config, old workers finish their connections)
- **startup**: 3.4 s
- **docs**: <https://hub.docker.com/_/nginx> · <https://nginx.org/en/docs/http/ngx_http_proxy_module.html> · <https://nginx.org/en/docs/http/ngx_http_upstream_module.html> · <https://nginx.org/en/docs/http/ngx_http_acme_module.html> · <https://nginx.org/en/docs/ngx_otel_module.html> · <https://nginx.org/en/docs/njs/>
- **notes**: Open-source nginx from the official `-otel` image, which also ships the njs, ACME (1.29 preview) and OpenTelemetry dynamic modules. Sticky sessions are done the OSS way (cookie = upstream address, map -> proxy_pass variable) because `sticky` is Plus-only; JWT is verified by an njs handler behind auth_request; PURGE is a refreshing subrequest (real purge is Plus / ngx_cache_purge); active health checks, brotli/zstd and HTTP/2 to non-gRPC upstreams are Plus / third-party features and are declared unsupported.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=http://app.lab:8080/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.03 {'app1': 145, 'app2': 145, 'slow': 10} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app3': 20}; 10 users -> {'app2': 12, 'app1': 9, 'app3': 9} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=10.77.0.13:8080; Path=/; HttpOnly' first=app3 then={'app3': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=3 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ○| active health checks (health_check directive) are NGINX Plus only; open source is passive (max_fails / fail_timeout / proxy_next_upstream) - app3 keeps receiving traffic while its /healthz says 503 |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.080 {'app1': 62, 'app2': 61, 'app3': 61, 'canary': 16} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ✅| shadow received 20/20 |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app1': 1, 'app2': 1, 'app3': 1} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app2",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ✅| proto=HTTP/3.0 status={'200': 1170} errors=0 [] |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app3 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.21s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ○| proxy_pass speaks HTTP/1.x to upstreams only; HTTP/2 towards upstreams exists solely for gRPC (grpc_pass) |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': ''} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| PROXY protocol towards upstreams is a stream (L4) feature (proxy_protocol on); for HTTP upstreams nginx sends X-Forwarded-For instead |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:46896 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:46592 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ✅| echo:app1:ping-a6f52b |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 8027B05DE8780000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: status 400; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client', 'X-Client-Cert-Verify': 'SUCCESS'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ✅| subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
caching| Response caching| `cache_hit`| ✅| origin app2#1 -> app2#1; X-Cache: MISS -> HIT age=None |
caching| Cache purge| `cache_purge`| ✅| purge -> 200; origin app3#1 -> app1#1 |
caching| Serve stale on upstream error| `cache_stale_on_error`| ✅| first 200 origin=app2#1; after expiry with origin 503: 200 origin=app2#1 X-Cache=STALE |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 345 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ○| ngx_brotli is a third-party module, not built into the official image (NGINX Plus ships it); build your own image to add it |
compression| Zstandard compression| `compress_zstd`| ○| zstd-nginx-module is third-party, not in the official image |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=nginx X-Powered-By=removed Server=nginx |
headers| Request ID generation| `request_id`| ✅| '84e511bc7542dc70105d0fdc7fab0c4c' / '1b17a8960320ea4d7220e053baf4bc08' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 6, 429: 34} |
security| Concurrent connection limit| `connection_limit`| ✅| codes={200: 3, 429: 9} |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.00s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.12 codes={200: 88, 503: 12} |
security| Bandwidth limiting| `bandwidth_limit`| ✅| 200 1048576 bytes in 2.00s (523 KB/s) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 '2026/09/13 19:10:53 [notice] 275#275: js vm init njs: 00006483E75BF280\n2026/09/13 19:10:53 [notice] 275#275: signal proc'; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes', 'cache', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'ssl', 'status', 'time', 'ua'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 57 samples e.g. go_gc_duration_seconds{quantile="0"} 0 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /nginx_status -> 200 'Active connections: 3 \nserver accepts handled requests\n 66 66 2256 \nReading: 0 W' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ✅| jaeger traces for service 'nginx': 3 |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| nginx has no Docker/label provider; nginx-proxy (docker-gen) or NGINX Plus' API are separate projects |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 66,841| 0.50| 5.71| 30.5| 0 / 0| 3.98| 60| 442| 7.5 / 3.5|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 13,385| 2.14| 32.5| 68.4| 0 / 0| 1.81| 135| 445| 2.5 / 7.8|  |
wrk reference: 8 threads, 64 connections, /small| ok| 68,018| 0.62| 9.41| 20.6| 0 / 0| 4.00| 59| 444| 7.3 / 3.0|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 48,844| 0.55| 6.83| 102| 0 / 0| 3.94| 81| 448| 5.8 / 3.2|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 59,485| 0.96| 10.9| 29.0| 640 / 0| 3.98| 67| 457| 6.7 / 3.5|  |
HTTP/3 (QUIC): 16 connections x 8 streams| ok| 66,414| 1.21| 8.76| 41.2| 106 / 0| 3.83| 58| 481| 7.2 / 6.8|  |
1 MiB responses, 32 connections (throughput MB/s)| ok| 4,389| 6.76| 17.5| 64.0| 0 / 0| 3.98| 907| 483| 4.2 / 3.3|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 9,310| 5.80| 21.0| 47.9| 0 / 0| 4.00| 429| 487| 4.5 / 1.1|  |
served from the proxy cache, 64 connections| ok| 63,485| 0.30| 7.70| 21.8| 0 / 0| 4.00| 63| 487| 0.1 / 3.6|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 102,502| 1.00| 3.00| 26.0| 0 / 0| 3.58| 35| 486| 5.1 / 7.7|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 9,720| 13.1| 18.0| 24.4| 0 / 0| 1.03| 106| 498| 3.1 / 2.7| 9745 > 0.016 <= 0.018 , 0.017 , 99.02, 7014 > 0.018 <= 0.02 , 0.019 , 99.78, 1111 > 0.02 <= 0.0244314 , 0.0222157 , 100… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,996| 0.58| 0.99| 3.83| 0 / 0| 1.06| 212| 497| 1.8 / 0.7| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.32| 1.09| 1.44| 0 / 1,895| 0.07| 343| 497| 0.2 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 19,008| 501| 861| 1,231| 0 / 0| 2.50| 132| 563| 4.1 / 2.3|  |

## OpenResty 1.27

- **image**: `pxlab-openresty:latest` (634 MB)
- **version**: `nginx version: openresty/1.27.1.2`
- **family**: nginx — nginx + LuaJIT: the programmable nginx (the base of Kong and APISIX)
- **reload mechanism**: signal (SIGHUP — new workers with the new config + Lua code, old workers drain)
- **startup**: 3.4 s
- **docs**: <https://hub.docker.com/r/openresty/openresty> · <https://github.com/openresty/lua-nginx-module> · <https://github.com/openresty/lua-resty-limit-traffic> · <https://github.com/fffonion/lua-resty-acme> · <https://github.com/knyar/nginx-lua-prometheus> · <https://github.com/SkyLothar/lua-resty-jwt>
- **notes**: OpenResty 1.27.1.2 (alpine-fat) with lua-resty-jwt, nginx-lua-prometheus, lua-resty-acme (+http/openssl) from opm. Same nginx core config as stacks/nginx, but JWT, rate/connection limits, forward auth, fault injection, a real cache purge (os.remove of the cache file), ACME (certificate requested from Pebble on the first TLS handshake for acme.lab) and Prometheus metrics are Lua. HTTP/3, stream L4 and sticky/hash balancing are nginx-native.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=http://app.lab:8080/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.04 {'app1': 146, 'app2': 143, 'slow': 11} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app3': 20}; 10 users -> {'app2': 12, 'app1': 9, 'app3': 9} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=10.77.0.13:8080; Path=/; HttpOnly' first=app3 then={'app3': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=3 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ○| active health checks need lua-resty-upstream-healthcheck (opm) driving the balancer; the plain upstream is passive like nginx |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.090 {'app1': 61, 'app2': 61, 'app3': 60, 'canary': 18} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ✅| shadow received 20/20 |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app1': 2, 'app2': 1, 'app3': 2} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app3",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ✅| proto=HTTP/3.0 status={'200': 1097} errors=0 [] |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app1 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.20s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ○| proxy_pass is HTTP/1.x only (h2c upstreams only for gRPC via grpc_pass), same as nginx |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': ''} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| PROXY protocol towards upstreams is a stream-module feature only, same as nginx |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:40162 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:58548 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ✅| echo:app1:ping-a6fe99 |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 80079F15AC7C0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: status 400; with cert: 200; forwarded: {'X-Client-Cert-Cn': 'O=pxlab,CN=lab-client'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ✅| subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
caching| Response caching| `cache_hit`| ✅| origin app3#1 -> app3#1; X-Cache: MISS -> HIT age=None |
caching| Cache purge| `cache_purge`| ✅| purge -> 200; origin app1#1 -> app2#1 |
caching| Serve stale on upstream error| `cache_stale_on_error`| ✅| first 200 origin=app3#1; after expiry with origin 503: 200 origin=app3#1 X-Cache=HIT |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 345 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ○| no brotli module in the OpenResty image |
compression| Zstandard compression| `compress_zstd`| ○| no zstd module |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=openresty X-Powered-By=removed Server=openresty |
headers| Request ID generation| `request_id`| ✅| 'c357e9acbafaa6c23506984afd08c503' / '70e64010be7764a1b407afb5eb97947d' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 6, 429: 34} |
security| Concurrent connection limit| `connection_limit`| ✅| codes={200: 3, 429: 9} |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.00s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.25 codes={200: 75, 503: 25} |
security| Bandwidth limiting| `bandwidth_limit`| ✅| 200 1048576 bytes in 2.00s (524 KB/s) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 '2026/09/13 19:51:07 [notice] 81#81: signal process started'; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes', 'cache', 'host', 'method', 'proto', 'remote_addr', 'request_id', 'request_time', 'ssl', 'status', 'time', 'ua'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 429 samples e.g. nginx_http_connections{state="active"} 2 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /nginx_status -> 200 'Active connections: 2 \nserver accepts handled requests\n 65 65 2183 \nReading: 0 W' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ○| no OpenTelemetry module in the OpenResty image (opentelemetry-lua is a separate integration) |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 52,081| 1.17| 2.09| 19.9| 0 / 0| 4.00| 77| 82| 6.0 / 3.1|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 5,983| 3.08| 38.1| 68.0| 0 / 0| 0.99| 165| 83| 1.5 / 7.6|  |
wrk reference: 8 threads, 64 connections, /small| ok| 53,611| 1.21| 2.47| 16.8| 0 / 0| 4.00| 75| 83| 6.0 / 2.5|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 34,143| 1.25| 5.35| 113| 0 / 0| 3.61| 106| 83| 4.7 / 2.8|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 44,219| 2.66| 6.33| 21.5| 472 / 0| 3.99| 90| 83| 5.3 / 3.1|  |
HTTP/3 (QUIC): 16 connections x 8 streams| ok| 57,012| 2.08| 6.52| 43.8| 124 / 0| 3.81| 67| 104| 6.4 / 5.9|  |
1 MiB responses, 32 connections (throughput MB/s)| ok| 4,226| 7.88| 14.4| 44.3| 0 / 0| 3.96| 938| 106| 3.9 / 3.1|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 6,447| 10.5| 16.3| 33.5| 0 / 0| 4.00| 620| 85| 4.2 / 0.8|  |
served from the proxy cache, 64 connections| ok| 53,032| 1.52| 2.63| 22.5| 0 / 0| 3.98| 75| 85| 0.1 / 3.5|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 105,329| 1.00| 3.00| 19.0| 0 / 0| 3.22| 31| 85| 5.0 / 7.9|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 6,204| 21.3| 27.4| 46.7| 0 / 0| 1.02| 165| 87| 2.0 / 2.1| , 99.90, 90 > 0.035 <= 0.04 , 0.0375 , 99.90, 5 > 0.04 <= 0.045 , 0.0425 , 99.97, 64 > 0.045 <= 0.0467473 , 0.0458736 ,… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,996| 0.58| 0.99| 6.17| 0 / 0| 1.26| 253| 85| 1.8 / 0.7| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.33| 1.06| 1.63| 0 / 1,896| 0.07| 364| 85| 0.1 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 18,552| 502| 1,014| 1,369| 0 / 0| 2.95| 159| 91| 3.9 / 2.2|  |

## Pingora (Rust, custom)

- **image**: `pxlab-pingora:latest` (180 MB)
- **version**: `pingora-lab 0.1.0 (pingora 0.9)`
- **family**: rust — a proxy written in Rust on Cloudflare's Pingora framework - routing and policies as code
- **reload mechanism**: zero-downtime upgrade (new process started with -u takes the listening sockets over the upgrade socket; the old one gets SIGQUIT and drains)
- **startup**: 3.3 s
- **docs**: <https://github.com/cloudflare/pingora> · <https://github.com/cloudflare/pingora/blob/main/docs/user_guide/index.md> · <https://docs.rs/pingora-proxy/latest/pingora_proxy/trait.ProxyHttp.html> · <https://docs.rs/pingora-load-balancing/latest/> · <https://docs.rs/pingora-cache/latest/>
- **notes**: A ~700-line Rust proxy on Pingora 0.9 (Cloudflare's framework): ProxyHttp hooks implement host/path routing, round-robin / weighted / ketama hashing / cookie stickiness, HTTP health checks, retries on connect failure, outlier ejection, h2c and verified-TLS upstreams, gRPC, rate and concurrency limits (pingora-limits), JWT (jsonwebtoken), basic auth, IP lists, fault injection, per-route timeouts, response cache (pingora-cache MemCache), compression, mTLS, SNI certificate callback, a static file, a custom error page, JSON access log, Prometheus metrics, a status API and a raw TCP proxy app. Zero-downtime upgrade via the framework's socket hand-off. What is missing is missing from the code, not from the framework's limits (mostly).

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ○| pingora-load-balancing ships round-robin / random / consistent-hash selection; least-connections would be a custom BackendSelection |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app1': 20}; 10 users -> {'app2': 15, 'app1': 6, 'app3': 9} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=app3; Path=/; HttpOnly' first=app3 then={'app3': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=3 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 17, 500: 3} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 2.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 2.1s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.100 {'app1': 60, 'app2': 60, 'app3': 60, 'canary': 20} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ○| no mirroring in the framework (would be a second upstream request written by hand) |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app2': 1, 'app1': 1, 'app3': 2} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app2",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ○| no HTTP/3 in Pingora |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app2 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.20s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ✅| upstream proto=HTTP/2.0 |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'http/1.1'} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| no PROXY protocol towards upstreams |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ○| no PROXY protocol on listeners |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:53200 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ○| Pingora is TCP/HTTP only |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ○| the L4 app in this proxy copies bytes; SNI parsing for passthrough is not implemented |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 800798FF1F7F0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Client-Cert-Org': 'pxlab'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ○| no ACME client (certificates come from files / callbacks) |
caching| Response caching| `cache_hit`| ✅| origin app1#1 -> app1#1; X-Cache: MISS -> HIT age=0 |
caching| Cache purge| `cache_purge`| ○| pingora-cache serves PURGE only for storages implementing purge; MemCache does in principle but the lab keeps it out of scope |
caching| Serve stale on upstream error| `cache_stale_on_error`| ○| stale-if-error is wired through should_serve_stale(); the in-memory cache expires objects before the lab's 2 s window |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 609 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ○| pingora's compression module in this build negotiates gzip/zstd (brotli support is feature-gated) |
compression| Zstandard compression| `compress_zstd`| ✅| Content-Encoding=zstd 99 bytes (65536 uncompressed) |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=pingora X-Powered-By=removed Server=pingora |
headers| Request ID generation| `request_id`| ✅| 'cf72452e-6150-4d0d-9f3a-5a9dce0d2eb6' / '23924bf1-8cce-4be3-8d5c-239db894bda1' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 10, 429: 30} |
security| Concurrent connection limit| `connection_limit`| ✅| codes={200: 3, 429: 9} |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ○| no built-in subrequest to an authorizer (would be a hand-written upstream call) |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 502 after 2.00s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.19 codes={200: 81, 503: 19} |
security| Bandwidth limiting| `bandwidth_limit`| ○| no built-in bandwidth limiting (body filters are synchronous) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['cache', 'duration_ms', 'error', 'host', 'method', 'remote_addr', 'status', 'time', 'tries', 'upstream', 'uri'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 261 samples e.g. pingora_http_request_duration_seconds_bucket{host="",le="0.005"} 3 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET / -> 200 '{"outliers":[],"proxy":"pingora-lab","requests_seen":0,"uptime_s":2,"version":"0' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ○| no OpenTelemetry integration in this binary |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 25,376| 2.49| 4.13| 18.6| 0 / 0| 3.94| 155| 24| 3.8 / 2.0|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 4,194| 13.9| 37.7| 63.8| 0 / 0| 1.44| 344| 27| 1.4 / 7.6|  |
wrk reference: 8 threads, 64 connections, /small| ok| 24,902| 2.54| 4.23| 10.7| 0 / 0| 3.94| 158| 30| 3.9 / 1.5|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 15,417| 4.09| 6.78| 73.1| 0 / 0| 3.95| 256| 32| 3.4 / 2.3|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 21,474| 5.80| 10.2| 18.1| 0 / 0| 3.92| 182| 32| 4.0 / 1.5|  |
| HTTP/3 (QUIC): 16 connections x 8 streams | unsupported | – | – | – | – | – | – | – | – | no HTTP/3 in Pingora |
1 MiB responses, 32 connections (throughput MB/s)| ok| 3,438| 9.18| 15.8| 33.8| 0 / 0| 3.98| 1,156| 62| 3.7 / 2.8|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 13,458| 4.68| 7.92| 20.4| 0 / 0| 3.98| 295| 62| 5.0 / 1.7|  |
served from the proxy cache, 64 connections| ok| 26,860| 2.36| 4.43| 27.0| 0 / 0| 3.97| 148| 32| 0.1 / 3.5|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 81,950| 1.00| 3.00| 14.0| 0 / 0| 3.80| 46| 46| 4.7 / 6.5|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 9,203| 13.7| 24.6| 35.8| 0 / 0| 3.00| 326| 46| 3.0 / 1.8| , 8297 > 0.025 <= 0.03 , 0.0275 , 99.97, 719 > 0.03 <= 0.035 , 0.0325 , 100.00, 34 > 0.035 <= 0.0358492 , 0.0354246 , 1… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,995| 0.60| 1.68| 5.47| 0 / 0| 2.08| 416| 46| 1.9 / 0.8| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.33| 1.12| 1.33| 0 / 1,901| 0.08| 391| 46| 0.1 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 13,670| 710| 1,070| 1,515| 0 / 0| 3.89| 285| 619| 3.7 / 1.9|  |

## Traefik v3

- **image**: `traefik:v3` (252 MB)
- **version**: `Version:      3.7.13`
- **family**: go — cloud-native edge router (Go): dynamic configuration from providers (Docker, Kubernetes, files)
- **reload mechanism**: file-watch (the file provider re-applies dynamic config on change; routers/services are swapped without restart)
- **startup**: 2.9 s
- **docs**: <https://hub.docker.com/_/traefik> · <https://doc.traefik.io/traefik/routing/routers/> · <https://doc.traefik.io/traefik/middlewares/http/overview/> · <https://doc.traefik.io/traefik/https/acme/> · <https://doc.traefik.io/traefik/observability/tracing/overview/>
- **notes**: Official Traefik v3 image with the file provider (watched: edits are the reload) and the Docker provider (whoami.lab is discovered from labels). HTTP/3 on :8443, ACME against Pebble (LEGO_CA_CERTIFICATES), mirroring, weighted traffic split, p2c balancing, sticky cookies, forwardAuth, mTLS with passTLSClientCert, TCP/UDP/SNI-passthrough routers. No cache, no JWT, no request-id, no Forwarded header, no file serving in the open-source edition.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app3 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app2': 11, 'app1': 10, 'app3': 9} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.75 {'app1': 75, 'app2': 25} |
load-balancing| Least-connections| `lb_least_conn`| ✅| slow share=0.03 {'app1': 161, 'slow': 8, 'app2': 131} |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ○| no hash-based balancing (wrr / p2c / sticky cookies only) |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=682614ad3435cf07; Path=/; HttpOnly' first=app1 then={'app1': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=77 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ○| no passive per-server ejection: the circuitBreaker middleware opens for the whole service, health checks probe /healthz only |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 1.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.1s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.100 {'app2': 88, 'app1': 87, 'canary': 20, 'app3': 5} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ✅| shadow received 20/20 |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app1': 2, 'app2': 2, 'app3': 2} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ✅| proto=HTTP/3.0 status={'200': 655} errors=0 [] |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app1 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.21s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ✅| tls:8443: SERVING |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ✅| upstream proto=HTTP/2.0 |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'backend.lab', 'alpn': 'h2'} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ○| PROXY protocol towards upstreams exists only for TCP services (tcp.serversTransports.proxyProtocol), not HTTP |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:47854 |
protocols| TCP (L4) proxying| `tcp_l4`| ✅| instance=app1 remote_addr=10.77.0.2:47866 headers=['Connection'] |
protocols| UDP proxying| `udp_l4`| ✅| echo:app1:ping-a6f92e |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ✅| subject=CN = backend.lab, O = pxlab TLSv1.3 |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_128_GCM_SHA256 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 8077E52C0B7B0000:error:0A00042E:SSL routines:ssl3_read_bytes:tlsv1 alert protocol version:../ssl/record/rec_layer_s3.c:918:SSL alert number 70 Protocol: TLSv1.1     Protocol  : TLSv1.1 |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {'X-Forwarded-Tls-Client-Cert-Info': 'Subject%3D%22O%3Dpxlab%2CCN%3Dlab-client%22%2CSubject%3D%22O%3Dpxlab%2CCN%3Dpxlab+CA%22'} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ✅| subject= issuer=CN = Pebble Intermediate CA 386164 sans=DNS:acme.lab |
caching| Response caching| `cache_hit`| ○| no HTTP cache in Traefik OSS (Traefik Enterprise / plugins) |
caching| Cache purge| `cache_purge`| ○| no cache |
caching| Serve stale on upstream error| `cache_stale_on_error`| ○| no cache |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 352 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ✅| Content-Encoding=br 94 bytes (65536 uncompressed) |
compression| Zstandard compression| `compress_zstd`| ✅| Content-Encoding=zstd 102 bytes (65536 uncompressed) |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ○| Traefik sets X-Forwarded-* only; no RFC 7239 Forwarded generation |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=traefik X-Powered-By=removed Server=lab-backend/1.0 |
headers| Request ID generation| `request_id`| ○| no request-id generation (a plugin or the upstream has to do it) |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 6, 429: 34} |
security| Concurrent connection limit| `connection_limit`| ✅| codes={200: 3, 429: 9} |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ○| no JWT validation in OSS (ForwardAuth, a plugin such as traefik-jwt-plugin, or Traefik Enterprise) |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 200 ACAO=* methods=GET,POST,PUT,DELETE,OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 504 after 2.00s |
security| Fault injection| `fault_injection`| ○| no fault-injection middleware |
security| Bandwidth limiting| `bandwidth_limit`| ○| no bandwidth limiting (rateLimit is per request) |
operations| Static file serving| `static_files`| ○| Traefik has no file server; static content must come from an upstream |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 ''; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['ClientAddr', 'ClientHost', 'ClientPort', 'ClientUsername', 'DownstreamContentSize', 'DownstreamStatus', 'Duration', 'OriginContentSize', 'OriginDuration', 'OriginStatus', 'Overhead', 'RequestAddr'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 418 samples e.g. go_gc_duration_seconds{quantile="0"} 1.9343e-05 |
operations| Admin / stats / runtime API| `admin_api`| ✅| GET /api/rawdata -> 200 '{"routers":{"a-tls@file":{"entryPoints":["websecure"],"middlewares":["common@fil' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ✅| jaeger traces for service 'traefik': 1 |
operations| Service discovery from Docker labels| `docker_label_discovery`| ✅| 200 'Hostname: 000d81002bc0\nIP: 127.0.0.1\nIP: ::1\nIP: 10.77.0.32\n' |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 12,396| 4.38| 15.4| 39.5| 0 / 0| 3.88| 313| 52| 3.1 / 1.3|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 3,751| 15.0| 44.2| 77.8| 0 / 0| 1.98| 528| 48| 1.3 / 6.9|  |
wrk reference: 8 threads, 64 connections, /small| ok| 12,662| 4.65| 15.1| 34.7| 0 / 0| 3.88| 307| 56| 3.2 / 0.9|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 11,642| 4.64| 16.3| 93.2| 0 / 0| 3.88| 334| 69| 3.0 / 1.4|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 9,857| 11.9| 32.4| 54.8| 0 / 0| 3.91| 397| 65| 2.6 / 1.8|  |
HTTP/3 (QUIC): 16 connections x 8 streams| ok| 10,164| 11.6| 30.8| 65.3| 0 / 0| 3.91| 385| 63| 2.6 / 2.2|  |
1 MiB responses, 32 connections (throughput MB/s)| ok| 2,897| 9.72| 31.2| 70.5| 0 / 0| 3.85| 1,330| 44| 3.3 / 2.7|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 9,375| 5.93| 20.5| 47.4| 0 / 0| 3.89| 415| 78| 4.2 / 1.0|  |
| served from the proxy cache, 64 connections | unsupported | – | – | – | – | – | – | – | – | no HTTP cache in Traefik OSS (Traefik Enterprise / plugins) |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 76,534| 1.00| 4.00| 18.0| 0 / 0| 3.19| 42| 61| 4.5 / 6.1|  |
gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)| ok| 7,026| 17.8| 28.7| 40.6| 0 / 0| 3.79| 540| 49| 2.0 / 2.7| 9, 2376 > 0.03 <= 0.035 , 0.0325 , 99.97, 399 > 0.035 <= 0.04 , 0.0375 , 100.00, 32 > 0.04 <= 0.0406157 , 0.0403078 , 1… |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,995| 0.70| 3.92| 16.1| 0 / 0| 2.24| 449| 48| 1.7 / 0.7| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74931 (100.0 … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.65| 48.6| 53.2| 0 / 1,896| 0.22| 1,096| 34| 0.2 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 4,073| 1,483| 7,195| 10,398| 0 / 0| 3.90| 959| 2,428| 2.0 / 0.5|  |

## Varnish 8 + hitch

- **image**: `varnish:8.0` (458 MB)
- **version**: `varnishd (varnish-8.0.2 revision fb46a7bb50531f1a86e17173aa64116fd98a8b86)`
- **family**: cache — HTTP accelerator / caching reverse proxy (C, VCL-programmable) with hitch for TLS
- **reload mechanism**: cli (varnishreload: vcl.load + vcl.use over the management interface; the new VCL takes over instantly, old VCL retires)
- **startup**: 4.7 s
- **docs**: <https://hub.docker.com/_/varnish> · <https://varnish-cache.org/docs/8.0/users-guide/vcl.html> · <https://varnish-cache.org/docs/8.0/reference/vmod_directors.html> · <https://github.com/varnish/hitch/blob/master/docs/configuration.md> · <https://github.com/varnish/varnish-modules>
- **notes**: Official varnish:8.0 image (ships vmod_vsthrottle, digest, reqwest, saintmode, fileserver, uuid, cookie ...) behind hitch for TLS (PROXY v2 between them, h2 via ALPN, mTLS on :8444). VCL implements routing, shard hashing, cookie stickiness, saintmode outlier ejection, retries, grace (stale-on-error), PURGE, vsthrottle rate limiting, JWT verification with vmod_digest, forward auth and a TLS/h2 backend with vmod_reqwest, static files with vmod_fileserver and custom error pages. varnishncsa and a Prometheus exporter run as sidecars on the shared VSM directory; varnishreload swaps VCL without dropping connections. No HTTP/3, gRPC, L4, ACME or brotli.

### Capabilities (69 probes with results)

| group | capability | id | result | detail / reason |
|---|---|---|---|---|
routing| Host-based routing| `route_host`| ✅| a.lab -> app2 (X-Route=a), b.lab -> b1 |
routing| Path prefix route + strip prefix| `route_path_prefix`| ✅| upstream path=/hello query=x=1 X-Route=api |
routing| Regex path route| `route_path_regex`| ✅| path=/v2/things X-Route=versioned |
routing| URL rewrite (regex capture)| `route_rewrite`| ✅| upstream path=/new/thing X-Route=rewritten |
routing| Redirect issued by the proxy| `route_redirect`| ✅| 301 Location=/landing |
routing| Header-based routing| `route_header`| ✅| instance=canary |
routing| Query-parameter routing| `route_query`| ✅| instance=canary |
routing| Method-based rule| `route_method`| ✅| DELETE -> 405 (x-instance=None) |
routing| HTTP -> HTTPS redirect| `redirect_https`| ✅| 301 Location=https://redirect.lab/x?q=1 |
load-balancing| Round-robin over 3 backends| `lb_round_robin`| ✅| {'app3': 10, 'app1': 10, 'app2': 10} |
load-balancing| Weighted round-robin (3:1)| `lb_weighted`| ✅| app1 share=0.73 {'app1': 73, 'app2': 27} |
load-balancing| Least-connections| `lb_least_conn`| ○| vmod_directors has round_robin / random / fallback / hash / shard - no least-connections director |
load-balancing| Consistent hashing on a header| `lb_hash_header`| ✅| u1 -> {'app2': 20}; 10 users -> {'app1': 18, 'app3': 3, 'app2': 9} |
load-balancing| Cookie stickiness| `lb_sticky_cookie`| ✅| cookie='lab_sticky=app3; Path=/; HttpOnly' first=app3 then={'app3': 12} |
load-balancing| Retry on connect failure| `lb_retry_dead_member`| ✅| codes={200: 30} max_ms=4 |
load-balancing| Passive health / outlier ejection| `lb_outlier_ejection`| ✅| first20={200: 20} last20={200: 40} flaky hits in last 20=0 |
load-balancing| Active health checks| `lb_active_health`| ✅| ejected after 2.1s; while unhealthy: {'app1': 15, 'app2': 15} app3 hits=0; re-admitted after 1.7s |
load-balancing| Weighted traffic split (canary)| `lb_canary_split`| ✅| canary share=0.090 {'app1': 68, 'app2': 52, 'canary': 18, 'app3': 62} |
load-balancing| Request mirroring / shadowing| `lb_mirror`| ○| no request mirroring |
load-balancing| Upstream connection pooling| `lb_upstream_keepalive`| ✅| new upstream connections for 60 requests: {'app1': 2, 'app3': 2, 'app2': 2} |
protocols| HTTP/2 (TLS, ALPN)| `http2_tls`| ✅| HTTP/2 200 upstream proto=HTTP/1.1 |
protocols| HTTP/2 cleartext (prior knowledge) on :8080| `h2c_frontend`| ✅| status=200 body=b'{\n "instance": "app1",\n "pool": "app",\n ' |
protocols| HTTP/3 (QUIC)| `http3`| ○| no HTTP/3 in Varnish Cache or hitch (Varnish Enterprise / a QUIC terminator in front) |
protocols| WebSocket proxying| `websocket`| ✅| text echo='hello' binary 4096=4096 instance=app1 |
protocols| Server-sent events (no response buffering)| `sse_streaming`| ✅| events=5 first=0.0s total=1.21s |
protocols| gRPC proxying (h2 -> upstream h2c :9090)| `grpc`| ○| no gRPC: Varnish cannot proxy HTTP/2 with trailers to backends |
protocols| HTTP/2 to the upstream (h2c)| `h2_upstream`| ○| Varnish speaks HTTP/1.1 to backends; h2 is only available via vmod_reqwest over TLS (used for tls.lab) |
protocols| TLS re-encryption to the upstream (verified)| `tls_upstream`| ✅| listener=tls tls={'version': 'TLS1.3', 'sni': 'app1', 'alpn': ''} |
protocols| PROXY protocol v2 to the upstream| `proxy_protocol_upstream`| ✅| listener=pp proxy_protocol={'version': 2, 'src_ip': '10.77.0.1', 'src_port': 42730, 'dst_ip': '10.77.0.2', 'dst_port': 8080, 'protocol': '0x11'} |
protocols| Accept PROXY protocol from clients (:8082)| `proxy_protocol_accept`| ✅| X-Forwarded-For=203.0.113.9 remote_addr=10.77.0.2:36512 |
protocols| TCP (L4) proxying| `tcp_l4`| ○| Varnish is HTTP-only |
protocols| UDP proxying| `udp_l4`| ○| Varnish is HTTP-only |
protocols| TLS passthrough by SNI (L4)| `tls_passthrough_sni`| ○| no L4 passthrough (hitch terminates TLS) |
tls| TLS termination| `tls_termination`| ✅| 200 cert=CN = app.lab, O = pxlab TLSv1.3 X-Forwarded-Proto=https |
tls| TLS 1.3 negotiated| `tls13`| ✅| TLSv1.3 TLS_AES_256_GCM_SHA384 |
tls| TLS 1.0/1.1 refused| `tls_legacy_refused`| ✅| 8047BA5AB87A0000:error:8000006F:system library:BIO_connect:Connection refused:../crypto/bio/bio_sock2.c:183:calling connect() 8047BA5AB87A0000:error:10000067:BIO routines:BIO_connect:connect error:../ |
tls| Mutual TLS (client certificate required)| `mtls_client_cert`| ✅| without cert: ReadError: [SSL: TLSV13_ALERT_CERTIFICATE_REQUIRED] tlsv13 alert certificate req; with cert: 200; forwarded: {} |
tls| Multiple certificates selected by SNI| `sni_multi_cert`| ✅| app.lab -> CN = app.lab, O = pxlab; b.lab -> CN = b.lab, O = pxlab |
tls| Automatic certificate via ACME (Pebble)| `acme_auto_cert`| ○| hitch has no ACME client (use certbot/lego and reload hitch) |
caching| Response caching| `cache_hit`| ✅| origin app3#1 -> app3#1; X-Cache: MISS -> HIT age=0 |
caching| Cache purge| `cache_purge`| ✅| purge -> 200; origin app1#1 -> app2#1 |
caching| Serve stale on upstream error| `cache_stale_on_error`| ✅| first 200 origin=app3#1; after expiry with origin 503: 200 origin=app3#1 X-Cache=HIT |
compression| gzip compression| `compress_gzip`| ✅| Content-Encoding=gzip 345 bytes (65536 uncompressed) |
compression| Brotli compression| `compress_brotli`| ○| Varnish compresses with gzip only |
compression| Zstandard compression| `compress_zstd`| ○| gzip only |
headers| X-Forwarded-* headers| `xff_headers`| ✅| XFF=10.77.0.1 Proto=http Host=app.lab:18080 X-Real-IP=10.77.0.1 |
headers| RFC 7239 Forwarded header| `forwarded_rfc7239`| ✅| Forwarded='for=10.77.0.1;proto=http;host=app.lab:18080' |
headers| Header manipulation| `header_add_remove`| ✅| X-Lab-Proxy=varnish X-Powered-By=removed Server=varnish |
headers| Request ID generation| `request_id`| ✅| 'cea3123b-6e1d-4856-bdab-f318f8bd7400' / '5d5eb2de-1df5-4e00-88a3-2df22975112e' |
security| Request rate limiting| `rate_limit`| ✅| codes={200: 10, 429: 30} |
security| Concurrent connection limit| `connection_limit`| ○| no per-client concurrency limit (vsthrottle is a request-rate limiter) |
security| IP allow / deny lists| `ip_allow_deny`| ✅| /allowed=200 /denied=403 |
security| HTTP basic authentication| `basic_auth`| ✅| no creds=401 (Basic realm="pxlab") creds=200 |
security| JWT validation (HS256)| `jwt_auth`| ✅| none=401 valid=200 bad-sig=401 |
security| External authorization (forward auth / auth_request / ext_authz)| `forward_auth`| ✅| none=401 token=200 X-Auth-User=alice |
security| CORS preflight answered by the proxy| `cors`| ✅| 204 ACAO=https://example.com methods=GET, POST, PUT, DELETE, OPTIONS |
security| Security response headers| `security_headers`| ✅| {'strict-transport-security': 'max-age=31536000; includeSubDomains', 'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'} |
security| Request body size limit| `body_size_limit`| ✅| 2MiB=413 100KiB=200 |
security| Upstream read timeout| `upstream_timeout`| ✅| 503 after 2.00s |
security| Fault injection| `fault_injection`| ✅| 503 share=0.25 codes={200: 75, 503: 25} |
security| Bandwidth limiting| `bandwidth_limit`| ○| no bandwidth limiting in Varnish Cache (Enterprise has vmod_tcp/..) |
operations| Static file serving| `static_files`| ✅| 200 '<!doctype html><title>pxlab static</title><p>pxlab static fi' x-instance=None |
operations| Custom error page| `custom_error_page`| ✅| 503 X-Error-Page=custom body='<!doctype html><title>pxlab error</title><h1>Custom error pa' |
operations| Configuration reload without restart| `hot_reload`| ✅| reload rc=0 "VCL 'reload_20260913_194547_507' compiled\nVCL 'reload_20260913_194547_507' now active"; then 200 |
operations| Structured (JSON) access log| `access_log_json`| ✅| json keys: ['bytes', 'duration_s', 'handling', 'host', 'method', 'remote_addr', 'request_id', 'status', 'time', 'ua', 'uri'] |
operations| Prometheus metrics| `metrics_prometheus`| ✅| 200 552 samples e.g. varnish_backend_bereq_bodybytes{backend="app1",server="unknown"} 0 |
operations| Admin / stats / runtime API| `admin_api`| ✅| rc=0 'Child in state running' |
operations| Distributed tracing (OpenTelemetry -> Jaeger)| `tracing_otel`| ○| no OpenTelemetry in Varnish Cache |
operations| Service discovery from Docker labels| `docker_label_discovery`| ○| no Docker provider |

### Load (14 scenarios)

| scenario | status | rps | p50 ms | p99 ms | max ms | errors / non-2xx | proxy cores | µs/req | mem MB | backend / loadgen cores | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
HTTP/1.1 keep-alive, 64 connections, /small| ok| 10,773| 5.04| 19.1| 47.1| 0 / 0| 3.95| 367| 281| 3.1 / 1.4|  |
HTTP/1.1 new connection per request, 64 in flight| ok| 4,187| 13.6| 39.7| 62.7| 0 / 0| 2.09| 498| 286| 1.4 / 6.5|  |
wrk reference: 8 threads, 64 connections, /small| ok| 10,524| 5.45| 20.1| 41.6| 0 / 0| 3.94| 374| 380| 3.0 / 0.9|  |
HTTPS HTTP/1.1 keep-alive, 64 connections| ok| 7,525| 7.27| 26.0| 111| 0 / 0| 3.92| 520| 258| 2.3 / 1.2|  |
HTTPS HTTP/2: 16 connections x 8 streams| ok| 5,985| 15.6| 86.1| 214| 0 / 0| 3.94| 658| 329| 1.9 / 1.5|  |
| HTTP/3 (QUIC): 16 connections x 8 streams | unsupported | – | – | – | – | – | – | – | – | no HTTP/3 in Varnish Cache or hitch (Varnish Enterprise / a QUIC terminator in front) |
1 MiB responses, 32 connections (throughput MB/s)| ok| 3,603| 8.48| 19.5| 41.3| 0 / 0| 3.97| 1,102| 411| 4.1 / 2.3|  |
64 KiB text compressed by the proxy (gzip), 64 connections| ok| 2,591| 18.1| 101| 211| 0 / 0| 3.93| 1,516| 389| 2.2 / 0.5|  |
served from the proxy cache, 64 connections| ok| 34,387| 1.90| 5.32| 28.9| 0 / 0| 3.99| 116| 397| 0.1 / 3.2|  |
WebSocket echo: 64 VUs x 500 messages (k6)| ok| 79,715| 1.00| 3.00| 16.0| 0 / 0| 3.82| 48| 398| 4.9 / 6.7|  |
| gRPC Health/Check over TLS: 16 connections x 8 streams (fortio) | unsupported | – | – | – | – | – | – | – | – | no gRPC: Varnish cannot proxy HTTP/2 with trailers to backends |
open loop at exactly 5000 rps (64 conns): latency without coordinated omission| ok| 4,995| 0.70| 1.89| 3.67| 0 / 0| 2.44| 489| 440| 1.9 / 0.8| false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 %) Response Header … |
/limited (10 r/s) hammered at 200 rps for 10 s: how many get through| ok| 200| 0.49| 0.59| 2.18| 0 / 1,991| 0.12| 591| 436| 0.2 / 0.0|  |
10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)| ok| 5,025| 523| 21,079| 29,009| 0 / 0| 2.66| 530| 3,423| 2.0 / 0.9|  |

