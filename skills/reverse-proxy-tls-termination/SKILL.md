---
name: reverse-proxy-tls-termination
description: Set up TLS on a reverse proxy correctly - termination with TLS 1.2/1.3 only, HTTP/2 and HTTP/3 (QUIC) negotiation, multiple certificates chosen by SNI, mutual TLS with client-certificate identity forwarded upstream, re-encryption to TLS upstreams with verification and SNI, SNI passthrough without termination, and automatic certificates via ACME (Let's Encrypt or a private CA such as Pebble/step-ca) - for NGINX, HAProxy, Caddy, Traefik, Envoy, Apache httpd, Varnish+hitch, OpenResty, Kong, APISIX, Pingora and ATS. Use this whenever a task mentions certificates, HTTPS, SNI, mTLS/client certs, ACME/Let's Encrypt/certbot, HSTS, QUIC/h3, or "the proxy shows the wrong certificate", even if the proxy name is not mentioned.
---

# TLS on reverse proxies

Verified in the reverse-proxies lab: six TLS probes x 12 proxies (`tls_termination`, `tls13`, `tls_legacy_refused`,
`mtls_client_cert`, `sni_multi_cert`, `acme_auto_cert`) plus the h2/h3 and TLS-upstream probes. Construct-per-proxy
tables live in the sibling skill `reverse-proxy-capability-mapping/references/tls.md` and `protocols.md`; this page is
the *how to get it right*.

## Decide these five things first

1. **Where TLS ends.** Terminate at the proxy (normal), re-encrypt to upstreams (`tls.lab` pattern: verify against
   your CA and send the *upstream's* name as SNI, never the client's Host), or pass through by SNI at L4 (the client
   sees the backend's certificate; the proxy cannot route on paths or add headers).
2. **Which names need which certificates.** One certificate with all SANs is simplest; per-name certificates are
   selected by SNI in every proxy - but only when the site/vhost/filter-chain is *named*. Caddy pins a host-less
   `:8443` site's certificate on every SNI; Traefik and Envoy match SANs against the SNI automatically; HAProxy and
   hitch take the first `crt`/`pem-file` as default.
3. **Protocol floor**: TLS 1.2 minimum, 1.3 preferred, tickets off unless you rotate keys (`ssl_session_tickets off`,
   `no-tls-tickets`, `session_ticket.enable INT 0`). The lab's `tls_legacy_refused` probe confirms every proxy refuses
   a TLS 1.1 client with these settings.
4. **h2 and h3**: h2 needs ALPN on the TLS listener (`alpn h2,http/1.1`; on by default in Caddy/Traefik/Envoy). h3 needs a
   UDP listener on the same port **and** `Alt-Svc: h3=":8443"` so browsers upgrade; publish the UDP port in compose.
   Not available in Apache, Varnish, Kong OSS, Pingora, the Ubuntu ATS build.
5. **Who issues certificates**: files (any proxy), or a built-in ACME client (nginx 1.29, HAProxy 3.2+, Caddy,
   Traefik, Apache mod_md, OpenResty lua-resty-acme, Kong acme plugin). Envoy, Varnish/hitch, APISIX, Pingora and ATS
   need certbot/lego/cert-manager plus a reload.

## mTLS checklist
- Require *and* verify: nginx `ssl_verify_client on` (not `optional`), HAProxy `verify required`, Caddy
  `mode require_and_verify`, Traefik `RequireAndVerifyClientCert`, Envoy `require_client_certificate: true`, Apache
  `SSLVerifyClient require`, hitch `client-verify = required`, APISIX `ssls[].client.ca`, Pingora
  `PEER | FAIL_IF_NO_PEER_CERT`, ATS `verify_client: STRICT`.
- Forward the identity, never trust an incoming header for it: set `X-Client-Cert-CN` from the TLS variable
  (`$ssl_client_s_dn`, `%[ssl_c_s_dn(CN)]`, `{http.request.tls.client.subject}`, XFCC/`%DOWNSTREAM_PEER_SUBJECT%`,
  `%{SSL_CLIENT_S_DN_CN}s`, `$ssl_client_s_dn`, ...) and **delete** it from client requests on non-mTLS listeners.
- Keep mTLS on its own port/listener (8444 in the lab): mixing optional client auth on the public listener leaks the
  CA list in every handshake and complicates browsers.
- hitch: a frontend-level `client-verify` applies only to `pem-file`s declared inside that frontend block.
- ATS 9.2: per-fqdn `verify_client_ca_certs` broke the handshake; use the global CA file.

## ACME checklist (works with Let's Encrypt and private CAs)
- HTTP-01 arrives on **port 80** of the name being issued - the proxy must listen on 80 (as root or with
  `net.ipv4.ip_unprivileged_port_start=0`) and answer `/.well-known/acme-challenge/` itself. Apache maps ports with
  `MDPortMap http:80 https:8443` when the TLS vhost is not on 443.
- Private CA (Pebble, step-ca): give the ACME client the CA bundle - nginx `ssl_trusted_certificate` in `acme_issuer`,
  HAProxy `httpclient.ssl.ca-file`, Caddy `trusted_roots`, Traefik `LEGO_CA_CERTIFICATES`, Apache: mount into the
  system bundle, OpenResty `lua_ssl_trusted_certificate`, Kong `KONG_LUA_SSL_TRUSTED_CERTIFICATE`.
- Directory URL quirks: Kong's plugin appends `/directory`; Pebble serves `/dir` (a tiny TLS shim fixed it). Kong and
  OpenResty need the *client* config in the right place (`api_uri` is the second argument of `autossl.init`).
- Activation: Apache mod_md needs `httpd -k graceful` after issuance (`MDMessageCmd` hook -> flag -> root loop);
  HAProxy's crt-store starts with a temporary self-signed pair until the first issuance; OpenResty issues lazily on the
  first handshake unless you trigger it in `init_worker`.
- Rate limits: Let's Encrypt has strict duplicate-certificate limits - test against Pebble or the staging endpoint.

## Lab PKI notes you will hit elsewhere
- OpenSSL/curl refuse wildcard SANs on single-label suffixes (`*.lab`): list every SAN.
- HAProxy and hitch want cert+key in one `.pem`; nginx/Caddy/Envoy want separate files; Kong/APISIX want the PEM text
  inline in the declarative config (generate it, do not commit it).
- Restart *everything* that loaded a certificate you regenerated (backends too: "unable to verify the first certificate").
- ECDSA P-256 keys are the cheapest for TLS 1.3; the lab's TLS h2 numbers use them.

## Verify
```bash
openssl s_client -connect proxy:8443 -servername b.lab -alpn h2 </dev/null 2>/dev/null | openssl x509 -noout -subject
openssl s_client -connect proxy:8443 -tls1_1 </dev/null                       # must fail
curl --cacert ca.crt --cert client.pem https://mtls.lab:8444/                  # 200 with X-Client-Cert-CN upstream
curl --cacert ca.crt -sI https://acme.lab:8443/ | grep -i alt-svc              # h3 advertised
```
