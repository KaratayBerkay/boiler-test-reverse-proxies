# TLS - construct per proxy

Probe ids: `tls_termination`, `tls13`, `tls_legacy_refused`, `mtls_client_cert`, `sni_multi_cert`, `acme_auto_cert`.

## Termination, versions, ciphers
- nginx / OpenResty: `listen 8443 ssl; ssl_certificate fullchain.crt; ssl_certificate_key key; ssl_protocols TLSv1.2 TLSv1.3; ssl_prefer_server_ciphers off; ssl_session_cache shared:SSL:20m; ssl_session_tickets off;`
- HAProxy: `bind :8443 ssl crt /certs/app.lab.pem` (**cert+key in one PEM**), `ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets`, `ssl-default-bind-ciphersuites ...`.
- Caddy: `tls /certs/app.lab.fullchain.crt /certs/app.lab.key { protocols tls1.2 tls1.3 }` per site; automatic HTTPS otherwise.
- Traefik: `tls.certificates: [{certFile, keyFile}]`, `tls.stores.default.defaultCertificate`, `tls.options.default: { minVersion: VersionTLS12, alpnProtocols: [h2, http/1.1] }`.
- Envoy: `DownstreamTlsContext { common_tls_context: { tls_params: { tls_minimum_protocol_version: TLSv1_2 }, tls_certificates: [...] } }` per filter chain.
- Apache: `SSLEngine on; SSLCertificateFile; SSLCertificateKeyFile; SSLProtocol -all +TLSv1.2 +TLSv1.3; SSLCipherSuite ...; SSLSessionCache shmcb:...`.
- Varnish: **hitch** in front (`frontend = { host = "*" port = "8443" }`, `pem-file`, `tls-protos = TLSv1.2 TLSv1.3`, `write-proxy-v2 = on` to Varnish); Varnish Cache itself has no TLS.
- Kong: `KONG_SSL_CERT/KONG_SSL_CERT_KEY` defaults + declarative `certificates` + `snis`; protocol versions via `KONG_SSL_PROTOCOLS`.
- APISIX: `ssls: [{ snis, cert, key }]` (PEM inline), `apisix.ssl.ssl_protocols: TLSv1.2 TLSv1.3`.
- Pingora: `TlsSettings::intermediate(cert, key)` (Mozilla intermediate profile: TLS 1.2+).
- ATS: `server_ports 8443:ssl`, `ssl_multicert.config`, `proxy.config.ssl.TLSv1_2/1_3 INT 1`, `TLSv1/TLSv1_1 INT 0`.

## Multiple certificates by SNI (`sni_multi_cert`)
- nginx: one `server` block per name with its own `ssl_certificate`. · HAProxy: `crt a.pem crt b.pem` on one bind (or `crt /dir/`); SNI/SAN selects. · Caddy: separate site blocks (`https://b.lab:8443 { tls b.crt b.key }`); **always name hosts** on TLS sites or one cert is pinned on every SNI. · Traefik: list every certificate under `tls.certificates`; SANs decide. · Envoy: `filter_chain_match: { server_names: [b.lab] }` + `tls_inspector`. · Apache: a vhost per name with its own `SSLCertificateFile`. · hitch: multiple `pem-file` lines, first = default. · Kong: `snis: [{ name, certificate: { id } }]`. · APISIX: `ssls` entries with `snis`. · Pingora: `TlsAccept::certificate_callback` reading `ssl.servername(NameType::HOST_NAME)`. · ATS: `ssl_multicert.config` lines (`dest_ip=*` = default).

## Mutual TLS (`mtls_client_cert`) - client cert required, CN forwarded
- nginx: `ssl_client_certificate ca.crt; ssl_verify_client on;` + `proxy_set_header X-Client-Cert-CN $ssl_client_s_dn;`
- HAProxy: `bind :8444 ssl crt ... ca-file ca.crt verify required` + `http-request set-header X-Client-Cert-CN %[ssl_c_s_dn(CN)] if { ssl_c_used }`.
- Caddy: `tls ... { client_auth { mode require_and_verify  trust_pool file ca.crt } }` + `header_up X-Client-Cert-CN {http.request.tls.client.subject}`.
- Traefik: `tls.options.mtls.clientAuth: { caFiles: [ca.crt], clientAuthType: RequireAndVerifyClientCert }` + `passTLSClientCert { info: { subject: { commonName: true } } }` (arrives as `X-Forwarded-Tls-Client-Cert-Info`).
- Envoy: `require_client_certificate: true` + `validation_context.trusted_ca`; HCM `forward_client_cert_details: SANITIZE_SET`, `set_current_client_cert_details: { subject: true }` (XFCC) or a route header `%DOWNSTREAM_PEER_SUBJECT%`.
- Apache: `SSLCACertificateFile ca.crt; SSLVerifyClient require; SSLOptions +StdEnvVars; RequestHeader set X-Client-Cert-CN "%{SSL_CLIENT_S_DN_CN}s"`.
- hitch: a **separate frontend** with its own `pem-file`, `client-verify = required`, `client-verify-ca = ca.crt` (frontend-level verify applies only to pem-files declared inside that frontend).
- Kong OSS: **unsupported** (mtls-auth is Enterprise; nginx-level `ssl_verify_client` would hit every listener).
- APISIX: the `ssls` entry for that SNI: `client: { ca: <pem>, depth: 2 }` + `proxy-rewrite` header `$ssl_client_s_dn`.
- Pingora: `TlsSettings::set_ca_file` + `set_verify(SslVerifyMode::PEER | FAIL_IF_NO_PEER_CERT)`.
- ATS: `sni.yaml` `- fqdn: mtls.lab  verify_client: STRICT` (CA = global `proxy.config.ssl.CA.cert.filename`; per-fqdn `verify_client_ca_certs` broke the handshake in 9.2.3); `sslheaders.so` exposes the subject.

## ACME (`acme_auto_cert`, against a Pebble test CA on `https://pebble:14000/dir`, HTTP-01 on port 80)
- nginx 1.29: `acme_issuer pebble { uri ...; ssl_trusted_certificate pebble-ca.pem; state_path ...; accept_terms_of_service; }` + in the server: `acme_certificate pebble; ssl_certificate $acme_certificate; ssl_certificate_key $acme_certificate_key;` (needs `resolver` and a `listen 80` in that server).
- HAProxy 3.2+: `expose-experimental-directives`; `acme pebble { directory ...; challenge http-01; keytype ECDSA; map virt@acme }`; `crt-store { load crt "/tmp/acme.lab.pem" alias "acme" acme pebble domains "acme.lab" }`; bind `crt "@/acme"`; answer `/.well-known/acme-challenge/` with `http-request return ... map(virt@acme)`; `httpclient.ssl.ca-file` for a private CA.
- Caddy: `tls { issuer acme { dir ...; trusted_roots pebble-ca.pem; disable_tlsalpn_challenge } }` on the site (default: Let's Encrypt for every named site - disable or give explicit certs elsewhere; `auto_https disable_redirects`).
- Traefik: `certificatesResolvers.pebble.acme: { caServer, httpChallenge: { entryPoint: web80 }, storage }` + router `tls: { certResolver: pebble }`; `LEGO_CA_CERTIFICATES=pebble-ca.pem` for a private CA.
- Envoy: **unsupported** (SDS / cert-manager).
- Apache mod_md: `MDCertificateAuthority ...; MDCAChallenges http-01; MDPortMap http:80 https:8443; MDStoreDir; MDomain acme.lab` + `MDMessageCmd` hook to trigger `httpd -k graceful` (the new cert is only active after a graceful restart); mount the CA into the system bundle.
- Varnish/hitch: **unsupported** (certbot + hitch reload).
- OpenResty: `lua-resty-acme` - `autossl.init({...}, { api_uri = ... })` in `init_by_lua`, `init_worker`, `ssl_certificate_by_lua_block { autossl.ssl_certificate() }`, a challenge location; `lua_ssl_trusted_certificate` for the CA.
- Kong: `acme` plugin (`api_uri`, `domains`, `storage: shm`) - it appends `/directory` to `api_uri`.
- APISIX: **unsupported** (push certificates from cert-manager/acme.sh).
- Pingora: **unsupported** (files/callbacks).
- ATS: **unsupported** (`acme.so` only serves challenge files).

## Self-signed lab PKI notes
OpenSSL and curl refuse wildcard SANs on public-suffix-less names like `*.lab` - list every host as a SAN. Regenerating
certificates requires restarting anything that loaded them (backends included). Keep cert+key bundles (`.pem`) for
HAProxy and hitch next to the split files.
