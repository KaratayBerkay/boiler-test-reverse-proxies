# Protocols - construct per proxy

Probe ids: `http2_tls`, `h2c_frontend`, `http3`, `websocket`, `sse_streaming`, `grpc`, `h2_upstream`, `tls_upstream`,
`proxy_protocol_upstream`, `proxy_protocol_accept`, `tcp_l4`, `udp_l4`, `tls_passthrough_sni`.

## HTTP/2 over TLS, h2c on plain ports, HTTP/3
| proxy | h2 (ALPN) | h2c prior knowledge | HTTP/3 |
|---|---|---|---|
| nginx / OpenResty | `listen 8443 ssl; http2 on;` | `http2 on;` also enables h2c on plain listeners | `listen 8443 quic reuseport;` + `add_header Alt-Svc 'h3=":8443"'` |
| HAProxy | `bind :8443 ssl crt ... alpn h2,http/1.1` | detected implicitly on `bind :8080` | `bind quic4@:8443 ssl crt ... alpn h3` (OpenSSL 3.5 QUIC) |
| Caddy | on by default | `servers { protocols h1 h2 h2c h3 }` | on by default on TLS sites (UDP port published) |
| Traefik | on by default | always on | `entryPoints.websecure.http3: { advertisedPort: 8443 }` |
| Envoy | `alpn_protocols: [h2, http/1.1]` on the DownstreamTlsContext | `codec_type: AUTO` | a UDP listener with `QuicDownstreamTransport` + HCM `codec_type: HTTP3` |
| Apache | `Protocols h2 h2c http/1.1` (mod_http2) | same directive | **unsupported** |
| Varnish + hitch | hitch `alpn-protos = "h2, http/1.1"`, varnishd `-p feature=+http2` | `-p feature=+http2` on the plain listener | **unsupported** |
| Kong | `KONG_PROXY_LISTEN "... 8443 http2 ssl"` | `0.0.0.0:8080 http2` | **unsupported** (3.9 OSS) |
| APISIX | `apisix.enable_http2: true` | same (apisix-level in 3.9+) | `ssl.listen: [{ port: 8443, enable_http3: true }]` |
| Pingora | `TlsSettings::enable_h2()` | `HttpServerOptions { h2c: true }` | **unsupported** |
| ATS | ALPN on `8443:ssl` | **unsupported** | **unsupported** (Ubuntu build without quiche) |

## WebSocket and streaming (SSE)
- nginx / OpenResty: `proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection $connection_upgrade;` (map) for WS; `proxy_buffering off` (+ `proxy_cache off`) for SSE.
- HAProxy: nothing for WS (`timeout tunnel 1h` sets its lifetime); SSE streams by default.
- Caddy: nothing for WS; `flush_interval -1` for SSE.
- Traefik: nothing for either.
- Envoy: route `upgrade_configs: [{ upgrade_type: websocket }]` + `timeout: 0s`; SSE needs `timeout: 0s`; put a router-only filter chain in the HCM `upgrade_configs` if buffer/compressor filters are in the chain (they hung the upgrade).
- Apache: `ProxyPass /ws ws://app1:8080/ws` (mod_proxy_wstunnel); SSE streams with the event MPM.
- Varnish: `if (req.http.Upgrade ~ "(?i)websocket") { return (pipe); }` + copy the Upgrade headers in `vcl_pipe`; SSE: `do_stream = true` and **no gzip** for `text/event-stream`.
- Kong: WS is automatic; SSE works with the default (buffering off for streaming responses).
- APISIX: route `enable_websocket: true`; SSE default.
- Pingora: upgrades pass through; SSE needs compression level 0 (the compression module buffers).
- ATS: WebSocket needs `ws://` / `wss://` **remap rules** (`map ws://app.lab/ ws://app1:8080/`).

## gRPC (`grpc`: h2/TLS or h2c in, h2c to :9090)
- nginx / OpenResty: `grpc_pass grpc://pool_grpc;` (upstream `keepalive 256`; ~1 upstream connection per stream - measured ~8k rps).
- HAProxy: `server app1 app1:9090 proto h2` + `option tcp-check` (inherited `httpchk` would fail).
- Caddy: `reverse_proxy h2c://app1:9090`.
- Traefik: service `url: h2c://app1:9090`.
- Envoy: cluster with `explicit_http_config: { http2_protocol_options: {} }`; route `timeout: 30s`.
- Apache: `ProxyPass /grpc.health.v1.Health/ h2c://app1:9090/...` (mod_proxy_http2).
- Varnish: **unsupported** (no h2 with trailers to backends).
- Kong: service `protocol: grpc`, route `protocols: [grpc, grpcs]`.
- APISIX: upstream `scheme: grpc`.
- Pingora: `HttpPeer` with `options.alpn = ALPN::H2` on a plaintext peer.
- ATS: **unsupported** (HTTP/1.1 to origins).

## Upstream transports: h2c, TLS, PROXY protocol (`h2_upstream`, `tls_upstream`, `proxy_protocol_upstream`)
| proxy | h2c to a plain HTTP upstream | verified TLS to the upstream | PROXY v2 to the upstream |
|---|---|---|---|
| nginx / OpenResty | **unsupported** (gRPC only) | `proxy_pass https://...; proxy_ssl_verify on; proxy_ssl_trusted_certificate ca.crt; proxy_ssl_server_name on; proxy_ssl_name backend.lab;` | **unsupported** in http (stream only: `proxy_protocol on`) |
| HAProxy | `server ... proto h2` | `server ... ssl verify required ca-file ca.crt sni str(backend.lab) check check-sni backend.lab` | `server ... send-proxy-v2 check check-send-proxy` |
| Caddy | `reverse_proxy h2c://app1:8080` | `reverse_proxy https://app1:8443 { transport http { tls_server_name backend.lab  tls_trust_pool file ca.crt } }` | `transport http { proxy_protocol v2 }` |
| Traefik | `url: h2c://app1:8080` | `serversTransport: { serverName: backend.lab, rootCAs: [ca.crt] }` | **unsupported** for HTTP (tcp services only) |
| Envoy | cluster `http2_protocol_options: {}` | `UpstreamTlsContext { sni: backend.lab, validation_context: { trusted_ca, match_typed_subject_alt_names } }` | `transport_socket: envoy.transport_sockets.upstream_proxy_protocol` (V2) |
| Apache | `ProxyPass / h2c://app1:8080/` | `SSLProxyEngine On; SSLProxyVerify require; SSLProxyCACertificateFile ca.crt; SSLProxyCheckPeerName on; ProxyPreserveHost Off` | **unsupported** |
| Varnish | only via `vmod_reqwest` over TLS | `reqwest.client(base_url = "https://app1:8443", ...)` (system trust store) | backend `.proxy_header = 2` |
| Kong | **unsupported** (grpc only) | service `protocol: https, tls_verify: true, ca_certificates: [id]` | **unsupported** |
| APISIX | **unsupported** (grpc only) | upstream `scheme: https, tls: { verify: true }, pass_host: rewrite, upstream_host: backend.lab` + `ssl_trusted_certificate` | **unsupported** for HTTP |
| Pingora | `HttpPeer` + `ALPN::H2` | `HttpPeer::new(addr, true, "backend.lab")` + `verify_cert`, `verify_hostname`, `ca` | **unsupported** |
| ATS | **unsupported** | `map ... https://app1:8443/` + `ssl.client.verify.server.policy ENFORCED`, `sni_policy remap`, `connect_ports 8443` | **unsupported** |

## Accepting PROXY protocol from clients (`proxy_protocol_accept`)
- nginx / OpenResty: `listen 8082 proxy_protocol;` + `set_real_ip_from 10.77.0.0/24; real_ip_header proxy_protocol;` · HAProxy: `bind :8082 accept-proxy` · Caddy: `servers :8082 { listener_wrappers { proxy_protocol { allow 0.0.0.0/0 } } }` · Traefik: `entryPoints.pp.proxyProtocol.trustedIPs` · Envoy: `listener_filters: envoy.filters.listener.proxy_protocol` · Apache: `RemoteIPProxyProtocol On` in the vhost (mod_remoteip) · Varnish: `-a pp=:8082,PROXY` · Kong: `KONG_PROXY_LISTEN "... 8082 proxy_protocol"` + `KONG_REAL_IP_HEADER proxy_protocol` + `KONG_TRUSTED_IPS` · APISIX: `apisix.proxy_protocol.listen_http_port: 8082` + `real-ip { source: proxy_protocol_addr }` · Pingora: **unsupported** · ATS: `server_ports ... 8082:pp` + `proxy_protocol_allowlist`.

## L4: TCP, UDP, TLS passthrough by SNI (`tcp_l4`, `udp_l4`, `tls_passthrough_sni`)
- nginx / OpenResty: `stream { server { listen 9000; proxy_pass ...; } server { listen 9001 udp; proxy_pass ...; proxy_responses 1; } map $ssl_preread_server_name $t {...} server { listen 8445; ssl_preread on; proxy_pass $t; } }`.
- HAProxy: `frontend fe_tcp mode tcp bind :9000`; passthrough: `tcp-request inspect-delay 5s; tcp-request content accept if { req.ssl_hello_type 1 }; use_backend x if { req.ssl_sni -i passthrough.lab }`; **no UDP**.
- Caddy (caddy-l4): global `layer4 { :9000 { route { proxy app1:8080 } }  udp/:9001 { route { proxy udp/app1:9002 } }  :8445 { @pass tls sni passthrough.lab  route @pass { proxy app1:8443 } } }`.
- Traefik: `tcp.routers` with `HostSNI(*)` / `HostSNI(passthrough.lab)` + `tls: { passthrough: true }`; `udp.routers`.
- Envoy: `tcp_proxy` network filter; `udp_proxy` listener filter with a matcher; `tls_inspector` + `filter_chain_match: { server_names: [passthrough.lab] }` + `tcp_proxy`.
- Apache: **unsupported** (HTTP only).
- Varnish: **unsupported**.
- Kong: `KONG_STREAM_LISTEN "9000, 9001 udp, 8445 ssl"` + services `protocol: tcp|udp|tls_passthrough` with routes `destinations: [{port}]` / `snis: [passthrough.lab]` (the passthrough listener must carry `ssl`).
- APISIX: `apisix.proxy_mode: http&stream`, `stream_proxy: { tcp: [9000], udp: [9001] }`, `stream_routes` with `server_port`; SNI passthrough **unsupported** (stream `sni` routes terminate TLS).
- Pingora: a `ServerApp` copying bytes (`copy_bidirectional`) for TCP; **no UDP**, no SNI parsing in the lab.
- ATS: only `sni.yaml` `tunnel_route: app1:8443` for a blind TLS tunnel (needs `connect_ports`); **no generic TCP/UDP**.
