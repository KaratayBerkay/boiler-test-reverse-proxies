# Explanation — Load scenarios

14 scenarios, proxy pinned to 4 cores, backends to 12, load generator to 8, 15 s per scenario after a 3 s warm-up. The headline metric is requests/s, MB/s, p99 ms or 2xx passed depending on the scenario; p99 latency, proxy CPU (cores of 4 · µs per request) and errors follow. Scenarios a proxy cannot run (unsupported capability) are listed without numbers.

## HTTP/1.1 keep-alive, 64 connections, /small

`h1_keepalive` · tool: oha · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **10,546**| 19.0| 3.71| 352| 0 / 0|  |
Apache httpd 2.4| **12,858**| 11.7| 3.93| 306| 0 / 0|  |
Apache Traffic Server 9.2| **27,938**| 4.46| 3.78| 135| 0 / 0|  |
Caddy 2| **11,299**| 18.1| 3.90| 345| 0 / 0|  |
Envoy 1.39| **18,582**| 5.91| 3.99| 215| 0 / 0|  |
HAProxy 3.4| **31,887**| 3.10| 3.99| 125| 0 / 0|  |
Kong Gateway 3.9| **10,394**| 16.8| 4.00| 384| 0 / 0|  |
NGINX 1.29| **66,841**| 5.71| 3.98| 60| 0 / 0|  |
OpenResty 1.27| **52,081**| 2.09| 4.00| 77| 0 / 0|  |
Pingora (Rust, custom)| **25,376**| 4.13| 3.94| 155| 0 / 0|  |
Traefik v3| **12,396**| 15.4| 3.88| 313| 0 / 0|  |
Varnish 8 + hitch| **10,773**| 19.1| 3.95| 367| 0 / 0|  |

## HTTP/1.1 new connection per request, 64 in flight

`h1_no_keepalive` · tool: oha · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **3,662**| 41.1| 1.75| 476| 0 / 0|  |
Apache httpd 2.4| **3,743**| 41.3| 1.53| 410| 0 / 0|  |
Apache Traffic Server 9.2| **4,507**| 41.8| 1.20| 266| 0 / 0|  |
Caddy 2| **3,719**| 44.6| 1.98| 532| 0 / 0|  |
Envoy 1.39| **6,270**| 24.6| 1.95| 311| 0 / 0|  |
HAProxy 3.4| **21,763**| 5.70| 3.97| 182| 0 / 0|  |
Kong Gateway 3.9| **3,653**| 46.5| 1.86| 510| 0 / 0|  |
NGINX 1.29| **13,385**| 32.5| 1.81| 135| 0 / 0|  |
OpenResty 1.27| **5,983**| 38.1| 0.99| 165| 0 / 0|  |
Pingora (Rust, custom)| **4,194**| 37.7| 1.44| 344| 0 / 0|  |
Traefik v3| **3,751**| 44.2| 1.98| 528| 0 / 0|  |
Varnish 8 + hitch| **4,187**| 39.7| 2.09| 498| 0 / 0|  |

## wrk reference: 8 threads, 64 connections, /small

`wrk_h1` · tool: wrk · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **11,329**| 17.1| 3.93| 347| 0 / 0|  |
Apache httpd 2.4| **19,574**| 6.77| 3.92| 200| 0 / 0|  |
Apache Traffic Server 9.2| **31,729**| 20.0| 3.63| 114| 0 / 0|  |
Caddy 2| **11,639**| 18.3| 3.85| 331| 0 / 0|  |
Envoy 1.39| **18,995**| 5.50| 3.99| 210| 0 / 0|  |
HAProxy 3.4| **35,051**| 3.00| 3.99| 114| 0 / 0|  |
Kong Gateway 3.9| **10,798**| 17.7| 4.01| 371| 0 / 0|  |
NGINX 1.29| **68,018**| 9.41| 4.00| 59| 0 / 0|  |
OpenResty 1.27| **53,611**| 2.47| 4.00| 75| 0 / 0|  |
Pingora (Rust, custom)| **24,902**| 4.23| 3.94| 158| 0 / 0|  |
Traefik v3| **12,662**| 15.1| 3.88| 307| 0 / 0|  |
Varnish 8 + hitch| **10,524**| 20.1| 3.94| 374| 0 / 0|  |

## HTTPS HTTP/1.1 keep-alive, 64 connections

`tls_h1` · tool: oha · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **10,158**| 16.3| 3.99| 393| 0 / 0|  |
Apache httpd 2.4| **11,616**| 13.2| 3.92| 337| 0 / 0|  |
Apache Traffic Server 9.2| **21,403**| 5.85| 3.80| 178| 0 / 0|  |
Caddy 2| **11,036**| 19.4| 3.82| 346| 0 / 0|  |
Envoy 1.39| **17,336**| 6.10| 3.98| 229| 0 / 0|  |
HAProxy 3.4| **27,703**| 3.11| 3.98| 144| 0 / 0|  |
Kong Gateway 3.9| **8,770**| 18.5| 3.96| 451| 0 / 0|  |
NGINX 1.29| **48,844**| 6.83| 3.94| 81| 0 / 0|  |
OpenResty 1.27| **34,143**| 5.35| 3.61| 106| 0 / 0|  |
Pingora (Rust, custom)| **15,417**| 6.78| 3.95| 256| 0 / 0|  |
Traefik v3| **11,642**| 16.3| 3.88| 334| 0 / 0|  |
Varnish 8 + hitch| **7,525**| 26.0| 3.92| 520| 0 / 0|  |

## HTTPS HTTP/2: 16 connections x 8 streams

`tls_h2` · tool: oha · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **10,878**| 28.2| 3.98| 366| 1,232 / 0|  |
Apache httpd 2.4| **7,010**| 60.0| 3.19| 455| 0 / 0|  |
Apache Traffic Server 9.2| **24,182**| 14.6| 3.87| 160| 0 / 0|  |
Caddy 2| **9,113**| 36.1| 3.87| 425| 0 / 0|  |
Envoy 1.39| **21,090**| 9.71| 3.94| 187| 0 / 0|  |
HAProxy 3.4| **27,945**| 6.82| 3.98| 142| 0 / 0|  |
Kong Gateway 3.9| **9,212**| 44.1| 3.80| 413| 48 / 0|  |
NGINX 1.29| **59,485**| 10.9| 3.98| 67| 640 / 0|  |
OpenResty 1.27| **44,219**| 6.33| 3.99| 90| 472 / 0|  |
Pingora (Rust, custom)| **21,474**| 10.2| 3.92| 182| 0 / 0|  |
Traefik v3| **9,857**| 32.4| 3.91| 397| 0 / 0|  |
Varnish 8 + hitch| **5,985**| 86.1| 3.94| 658| 0 / 0|  |

## HTTP/3 (QUIC): 16 connections x 8 streams

`h3` · tool: h3load · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **9,083**| 28.0| 3.96| 435| 810 / 0|  |
Caddy 2| **9,456**| 33.9| 3.90| 412| 0 / 0|  |
Envoy 1.39| **10,252**| 22.1| 3.98| 388| 0 / 0|  |
HAProxy 3.4| **30,221**| 8.23| 3.80| 126| 0 / 0|  |
NGINX 1.29| **66,414**| 8.76| 3.83| 58| 106 / 0|  |
OpenResty 1.27| **57,012**| 6.52| 3.81| 67| 124 / 0|  |
Traefik v3| **10,164**| 30.8| 3.91| 385| 0 / 0|  |

Not run: Apache httpd 2.4 (unsupported: no HTTP/3 in httpd (mod_http2 stops at HTTP/2)) · Apache Traffic Server 9.2 (unsupported: the Ubuntu build has no QUIC (experimental in 9.x, needs quiche)) · Kong Gateway 3.9 (unsupported: no HTTP/3 in Kong Gateway 3.9 OSS) · Pingora (Rust, custom) (unsupported: no HTTP/3 in Pingora) · Varnish 8 + hitch (unsupported: no HTTP/3 in Varnish Cache or hitch (Varnish Enterprise / a QUIC terminator in front))

## 1 MiB responses, 32 connections (throughput MB/s)

`large_1mb` · tool: oha · headline: MB/s

| proxy | headline (MB/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **1,027.9**| 44.8| 4.00| 3,890| 0 / 0|  |
Apache httpd 2.4| **1,631.3**| 69.7| 3.98| 2,439| 0 / 0|  |
Apache Traffic Server 9.2| **3,703.0**| 11.9| 4.00| 1,080| 0 / 0|  |
Caddy 2| **2,966.4**| 32.4| 3.85| 1,299| 0 / 0|  |
Envoy 1.39| **3,642.2**| 13.7| 4.00| 1,098| 0 / 0|  |
HAProxy 3.4| **2,257.2**| 21.9| 3.98| 1,763| 0 / 0|  |
Kong Gateway 3.9| **1,377.3**| 43.6| 4.00| 2,903| 0 / 0|  |
NGINX 1.29| **4,388.8**| 17.5| 3.98| 907| 0 / 0|  |
OpenResty 1.27| **4,225.8**| 14.4| 3.96| 938| 0 / 0|  |
Pingora (Rust, custom)| **3,438.3**| 15.8| 3.98| 1,156| 0 / 0|  |
Traefik v3| **2,896.8**| 31.2| 3.85| 1,330| 0 / 0|  |
Varnish 8 + hitch| **3,603.0**| 19.5| 3.97| 1,102| 0 / 0|  |

## 64 KiB text compressed by the proxy (gzip), 64 connections

`gzip_64k` · tool: oha · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **4,788**| 29.7| 3.83| 801| 0 / 0|  |
Apache httpd 2.4| **5,519**| 37.9| 3.93| 711| 0 / 0|  |
Apache Traffic Server 9.2| **5,794**| 15.1| 4.00| 690| 0 / 0|  |
Caddy 2| **9,311**| 21.9| 3.89| 418| 0 / 0|  |
Envoy 1.39| **8,832**| 13.0| 4.00| 453| 0 / 0|  |
HAProxy 3.4| **12,847**| 6.69| 4.00| 311| 0 / 0|  |
Kong Gateway 3.9| **6,239**| 23.3| 3.99| 639| 0 / 0|  |
NGINX 1.29| **9,310**| 21.0| 4.00| 429| 0 / 0|  |
OpenResty 1.27| **6,447**| 16.3| 4.00| 620| 0 / 0|  |
Pingora (Rust, custom)| **13,458**| 7.92| 3.98| 295| 0 / 0|  |
Traefik v3| **9,375**| 20.5| 3.89| 415| 0 / 0|  |
Varnish 8 + hitch| **2,591**| 101| 3.93| 1,516| 0 / 0|  |

## served from the proxy cache, 64 connections

`cache_hit` · tool: oha · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **11,591**| 16.7| 3.87| 334| 0 / 0|  |
Apache httpd 2.4| **19,537**| 17.3| 3.63| 186| 0 / 0|  |
Apache Traffic Server 9.2| **52,600**| 2.38| 4.00| 76| 0 / 0|  |
Caddy 2| **1,662**| 199| 3.89| 2,340| 0 / 0|  |
HAProxy 3.4| **56,216**| 1.64| 4.00| 71| 0 / 0|  |
Kong Gateway 3.9| **11,389**| 15.3| 3.99| 351| 0 / 0|  |
NGINX 1.29| **63,485**| 7.70| 4.00| 63| 0 / 0|  |
OpenResty 1.27| **53,032**| 2.63| 3.98| 75| 0 / 0|  |
Pingora (Rust, custom)| **26,860**| 4.43| 3.97| 148| 0 / 0|  |
Varnish 8 + hitch| **34,387**| 5.32| 3.99| 116| 0 / 0|  |

Not run: Envoy 1.39 (unsupported: the HTTP cache filter is alpha; in 1.39 it makes its own internal upstream request that bypasses route-level header mutations, redirects and direct responses for every route (breaks 20+ probes), so it) · Traefik v3 (unsupported: no HTTP cache in Traefik OSS (Traefik Enterprise / plugins))

## WebSocket echo: 64 VUs x 500 messages (k6)

`ws_echo` · tool: k6 · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **104,346**| 3.00| 3.24| 31| 0 / 0|  |
Apache httpd 2.4| **65,424**| 3.00| 3.93| 60| 0 / 0|  |
Apache Traffic Server 9.2| **96,681**| 3.00| 3.66| 38| 0 / 0|  |
Caddy 2| **78,878**| 4.00| 3.20| 40| 0 / 0|  |
Envoy 1.39| **84,220**| 3.00| 3.73| 44| 0 / 0|  |
HAProxy 3.4| **102,366**| 3.00| 3.67| 36| 0 / 0|  |
Kong Gateway 3.9| **103,775**| 3.00| 3.28| 32| 0 / 0|  |
NGINX 1.29| **102,502**| 3.00| 3.58| 35| 0 / 0|  |
OpenResty 1.27| **105,329**| 3.00| 3.22| 31| 0 / 0|  |
Pingora (Rust, custom)| **81,950**| 3.00| 3.80| 46| 0 / 0|  |
Traefik v3| **76,534**| 4.00| 3.19| 42| 0 / 0|  |
Varnish 8 + hitch| **79,715**| 3.00| 3.82| 48| 0 / 0|  |

## gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)

`grpc_health` · tool: fortio · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **9,213**| 33.6| 3.99| 434| 0 / 0|  , 99.95, 41 > 0.05 <= 0.06 , 0.055 , 100.00, 68 > 0.06 <= 0.07 , 0.065 , 100.00, 5 > 0.07 <= 0.0706067 , 0.0703034 , 1… |
Apache httpd 2.4| **6,928**| 60.0| 3.28| 474| 0 / 0| 0.085 , 99.95, 76 > 0.09 <= 0.1 , 0.095 , 99.98, 29 > 0.1 <= 0.12 , 0.11 , 100.00, 18 > 0.12 <= 0.121893 , 0.120947 , 1… |
Caddy 2| **6,947**| 29.3| 3.80| 547| 0 / 0| 9.92, 40 > 0.04 <= 0.045 , 0.0425 , 99.97, 59 > 0.045 <= 0.05 , 0.0475 , 99.99, 14 > 0.05 <= 0.0557137 , 0.0528569 , 10… |
Envoy 1.39| **19,294**| 13.8| 3.86| 200| 0 / 0| , 1613 > 0.016 <= 0.018 , 0.017 , 99.95, 387 > 0.018 <= 0.02 , 0.019 , 99.99, 123 > 0.02 <= 0.0218296 , 0.0209148 , 100… |
HAProxy 3.4| **20,341**| 8.87| 3.99| 196| 0 / 0| , 155 > 0.018 <= 0.02 , 0.019 , 99.97, 95 > 0.02 <= 0.025 , 0.0225 , 100.00, 85 > 0.025 <= 0.0265828 , 0.0257914 , 100.… |
Kong Gateway 3.9| **7,711**| 38.7| 3.99| 518| 0 / 0| 5 , 99.88, 90 > 0.05 <= 0.06 , 0.055 , 99.94, 62 > 0.06 <= 0.07 , 0.065 , 99.98, 53 > 0.07 <= 0.0757207 , 0.0728604 , 1… |
NGINX 1.29| **9,720**| 18.0| 1.03| 106| 0 / 0| 9745 > 0.016 <= 0.018 , 0.017 , 99.02, 7014 > 0.018 <= 0.02 , 0.019 , 99.78, 1111 > 0.02 <= 0.0244314 , 0.0222157 , 100… |
OpenResty 1.27| **6,204**| 27.4| 1.02| 165| 0 / 0| , 99.90, 90 > 0.035 <= 0.04 , 0.0375 , 99.90, 5 > 0.04 <= 0.045 , 0.0425 , 99.97, 64 > 0.045 <= 0.0467473 , 0.0458736 ,… |
Pingora (Rust, custom)| **9,203**| 24.6| 3.00| 326| 0 / 0| , 8297 > 0.025 <= 0.03 , 0.0275 , 99.97, 719 > 0.03 <= 0.035 , 0.0325 , 100.00, 34 > 0.035 <= 0.0358492 , 0.0354246 , 1… |
Traefik v3| **7,026**| 28.7| 3.79| 540| 0 / 0| 9, 2376 > 0.03 <= 0.035 , 0.0325 , 99.97, 399 > 0.035 <= 0.04 , 0.0375 , 100.00, 32 > 0.04 <= 0.0406157 , 0.0403078 , 1… |

Not run: Apache Traffic Server 9.2 (unsupported: no HTTP/2 to origins, so no gRPC proxying) · Varnish 8 + hitch (unsupported: no gRPC: Varnish cannot proxy HTTP/2 with trailers to backends)

## open loop at exactly 5000 rps (64 conns): latency without coordinated omission

`open_loop_5k` · tool: fortio · headline: ms p99 (lower is better)

| proxy | headline (ms p99) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **11.7**| 11.7| 2.68| 539| 0 / 0| lse, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 128 Code 200 : 74493 (100.0 %) Response Header S… |
Apache httpd 2.4| **1.74**| 1.74| 2.28| 456| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
Apache Traffic Server 9.2| **3.94**| 3.94| 1.93| 386| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
Caddy 2| **5.20**| 5.20| 2.26| 452| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74897 (100.0 … |
Envoy 1.39| **3.69**| 3.69| 2.61| 522| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
HAProxy 3.4| **1.69**| 1.69| 1.73| 346| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
Kong Gateway 3.9| **9.44**| 9.44| 2.76| 557| 0 / 0| , Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74394 (100.0 %) Response Header Sizes… |
NGINX 1.29| **0.99**| 0.99| 1.06| 212| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
OpenResty 1.27| **0.99**| 0.99| 1.26| 253| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
Pingora (Rust, custom)| **1.68**| 1.68| 2.08| 416| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 … |
Traefik v3| **3.92**| 3.92| 2.24| 449| 0 / 0| orm: true, Jitter: false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74931 (100.0 … |
Varnish 8 + hitch| **1.89**| 1.89| 2.44| 489| 0 / 0| false, Catchup allowed: false IP addresses distribution: 10.77.0.2:8080: 64 Code 200 : 74944 (100.0 %) Response Header … |

## /limited (10 r/s) hammered at 200 rps for 10 s: how many get through

`ratelimit_accuracy` · tool: oha · headline: 2xx passed

| proxy | headline (2xx passed) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **106** of 2,001| 2.87| 0.20| 1,026| 0 / 1,895|  |
Caddy 2| **100** of 2,001| 1.71| 0.23| 1,139| 0 / 1,901|  |
Envoy 1.39| **114** of 2,001| 1.63| 0.12| 596| 0 / 1,887|  |
HAProxy 3.4| **10** of 2,001| 0.52| 0.08| 414| 0 / 1,991|  |
Kong Gateway 3.9| **110** of 2,001| 2.72| 0.26| 1,310| 0 / 1,891|  |
NGINX 1.29| **106** of 2,001| 1.09| 0.07| 343| 0 / 1,895|  |
OpenResty 1.27| **105** of 2,001| 1.06| 0.07| 364| 0 / 1,896|  |
Pingora (Rust, custom)| **100** of 2,001| 1.12| 0.08| 391| 0 / 1,901|  |
Traefik v3| **105** of 2,001| 48.6| 0.22| 1,096| 0 / 1,896|  |
Varnish 8 + hitch| **10** of 2,001| 0.59| 0.12| 591| 0 / 1,991|  |

Not run: Apache httpd 2.4 (unsupported: no request-rate limiting in the standard modules (mod_ratelimit is bandwidth only; mod_qos / mod_evasive are third-party)) · Apache Traffic Server 9.2 (unsupported: rate_limit.so limits concurrency per remap, not requests per second per client)

## 10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)

`c10k` · tool: oha · headline: req/s

| proxy | headline (req/s) | p99 ms | proxy cores | µs/req | errors / non-2xx | detail |
|---|---|---|---|---|---|---|
Apache APISIX 3.15| **5,296**| 2,345| 3.82| 721| 0 / 0|  |
Apache httpd 2.4| **464**| 61,412| 0.26| 562| 12,843 / 0|  |
Apache Traffic Server 9.2| **9,127**| 1,340| 2.35| 258| 0 / 0|  |
Caddy 2| **3,761**| 6,257| 3.84| 1,021| 0 / 5,466|  |
Envoy 1.39| **8,576**| 1,856| 2.82| 329| 0 / 0|  |
HAProxy 3.4| **18,936**| 997| 3.10| 164| 0 / 0|  |
Kong Gateway 3.9| **7,857**| 1,761| 3.88| 494| 0 / 0|  |
NGINX 1.29| **19,008**| 861| 2.50| 132| 0 / 0|  |
OpenResty 1.27| **18,552**| 1,014| 2.95| 159| 0 / 0|  |
Pingora (Rust, custom)| **13,670**| 1,070| 3.89| 285| 0 / 0|  |
Traefik v3| **4,073**| 7,195| 3.90| 959| 0 / 0|  |
Varnish 8 + hitch| **5,025**| 21,079| 2.66| 530| 0 / 0|  |

