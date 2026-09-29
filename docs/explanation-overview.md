# Explanation — Overview

One row per proxy. Capabilities = ok / fail / declared-unsupported counts out of 69 probes. Throughput: HTTP/1.1 keep-alive, 64 connections, proxy pinned to 4 cores. µs/req = proxy CPU microseconds per request (lower is cheaper). Failover/reload errors are load errors / timeline failures from the chaos phase.

| proxy | what it is | capabilities ✅/❌/○ | h1 rps | µs/req | TLS h2 rps | h3 rps | WS msg/s | failover errors load/timeline | reload errors load/timeline | image | start s |
|---|---|---|---|---|---|---|---|---|---|---|---|
**Apache APISIX 3.15** 3.15.0| API gateway on OpenResty (Apache): routes/upstreams/consumers/plugins, standalone yaml config (or etcd)| 62✅ 0❌ 7○| **10,546**| 352| 10,878| 9,083| 104,346| 0 / 0| 0 / 0| 559 MB| 2.8 |
**Apache httpd 2.4** Apache/2.4.68 (Unix)| the classic modular web server (C) used as a reverse proxy: mod_proxy + balancer + hcheck + cache + md| 53✅ 1❌ 15○| **12,858**| 306| 7,010| –| 65,424| 0 / 0| 48 / 1| 175 MB| 3.3 |
**Apache Traffic Server 9.2** Traffic Server 9.2.3 Feb 12 2026 02:40:38 localhost| CDN-grade caching proxy (C++): remap rules, NextHop strategies, plugins (Yahoo/Apple/Comcast lineage)| 42✅ 0❌ 27○| **27,938**| 135| 24,182| –| 96,681| 0 / 0| 0 / 0| 235 MB| 6.1 |
**Caddy 2** v2.11.4 h1:XKxkMTgNSizEvKG6QHue6cAsFOteU2qA61w2tKkCWi0=| web server / reverse proxy (Go) with automatic HTTPS; extended with xcaddy plugins| 64✅ 0❌ 5○| **11,299**| 345| 9,113| 9,456| 78,878| 0 / 0| 0 / 0| 160 MB| 3.4 |
**Envoy 1.39** b579d07d3ad7ee11d32b105e91a5a39ad24718d7/1.39.1/Clean/RELEASE/BoringSSL| cloud-native L4/L7 proxy (C++): the data plane of Istio & co, configured through xDS| 62✅ 1❌ 6○| **18,582**| 215| 21,090| 10,252| 84,220| 0 / 0| 0 / 0| 293 MB| 2.9 |
**HAProxy 3.4** 3.4.4-7f03ae6 2026/08/27 - https://haproxy.org/| TCP/HTTP load balancer (C, event-driven, multi-threaded); the reference L4/L7 balancer| 61✅ 0❌ 8○| **31,887**| 125| 27,945| 30,221| 102,366| 0 / 0| 0 / 0| 185 MB| 2.9 |
**Kong Gateway 3.9** 3.9.3| API gateway on OpenResty (Lua plugins): routes/services/upstreams/consumers/plugins, DB-less declarative config| 57✅ 0❌ 12○| **10,394**| 384| 9,212| –| 103,775| 0 / 0| 0 / 0| 528 MB| 4.4 |
**NGINX 1.29** nginx/1.29.8| event-driven web server / reverse proxy (C); the most deployed proxy on the internet| 63✅ 0❌ 6○| **66,841**| 60| 59,485| 66,414| 102,502| 0 / 0| 52 / 0| 250 MB| 3.4 |
**OpenResty 1.27** openresty/1.27.1.2| nginx + LuaJIT: the programmable nginx (the base of Kong and APISIX)| 62✅ 0❌ 7○| **52,081**| 77| 44,219| 57,012| 105,329| 0 / 0| 28 / 0| 634 MB| 3.4 |
**Pingora (Rust, custom)** pingora-lab 0.1.0 (pingora 0.9)| a proxy written in Rust on Cloudflare's Pingora framework - routing and policies as code| 54✅ 0❌ 15○| **25,376**| 155| 21,474| –| 81,950| 1 / 0| 37 / 0| 180 MB| 3.3 |
**Traefik v3** 3.7.13| cloud-native edge router (Go): dynamic configuration from providers (Docker, Kubernetes, files)| 57✅ 0❌ 12○| **12,396**| 313| 9,857| 10,164| 76,534| 12 / 0| 0 / 0| 252 MB| 2.9 |
**Varnish 8 + hitch** varnishd (varnish-8.0.2 revision fb46a7bb50531f1a86e17173aa64116fd98a8b86)| HTTP accelerator / caching reverse proxy (C, VCL-programmable) with hitch for TLS| 54✅ 0❌ 15○| **10,773**| 367| 5,985| –| 79,715| 0 / 0| 0 / 0| 458 MB| 4.7 |
