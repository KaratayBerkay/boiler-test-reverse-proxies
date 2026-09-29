#!/usr/bin/env bash
# Generate the lab PKI (run once; idempotent unless --force). Everything is EC P-256, 10-year validity, world-readable
# because containers run as unprivileged users (haproxy, caddy, kong ...). LAB ONLY - never reuse these files.
#
#   ca.crt / ca.key              the lab CA (proxies verify backends and clients against it; probes verify proxies)
#   app.lab.crt/.key/.pem        CN=app.lab, SAN *.lab + app.lab + localhost + 127.0.0.1   (default TLS cert; .pem = key+cert+chain for HAProxy/hitch)
#   b.lab.crt/.key/.pem          CN=b.lab                                                  (second cert: proves SNI-based selection)
#   backend.crt/.key             CN=backend.lab, SAN every backend service name + passthrough.lab (the origin's TLS listener)
#   client.crt/.key/.pem         CN=lab-client (clientAuth)                                (mTLS probe)
#   pebble-ca.pem                Pebble's own CA (so proxies can trust the ACME directory https://pebble:14000/dir)
#   ../auth/htpasswd*            basic-auth users in apr1 / bcrypt / sha1 formats (lab : lab-pass)
#   ../auth/jwt.*                HS256 secret (raw and as a JWK set for Envoy/Kong/APISIX)
set -euo pipefail
cd "$(dirname "$0")"
if [ -f ca.crt ] && [ "${1:-}" != "--force" ]; then echo "certs exist (use --force to regenerate)"; exit 0; fi
rm -f ./*.crt ./*.key ./*.pem ./*.csr ./*.srl ./*.cnf

DAYS=3650
ca() {
  openssl ecparam -name prime256v1 -genkey -noout -out ca.key
  openssl req -x509 -new -key ca.key -sha256 -days $DAYS -subj "/CN=pxlab CA/O=pxlab" -out ca.crt \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign"
}
# cert <name> <CN> <SAN list comma-separated> <extKeyUsage>
cert() {
  local name=$1 cn=$2 san=$3 eku=$4
  openssl ecparam -name prime256v1 -genkey -noout -out "$name.key"
  openssl req -new -key "$name.key" -subj "/CN=$cn/O=pxlab" -out "$name.csr"
  cat > "$name.cnf" <<EOF
basicConstraints=CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=$eku
subjectAltName=$san
EOF
  openssl x509 -req -in "$name.csr" -CA ca.crt -CAkey ca.key -CAcreateserial -days $DAYS -sha256 -extfile "$name.cnf" -out "$name.crt"
  cat "$name.key" "$name.crt" ca.crt > "$name.pem"      # HAProxy / hitch style bundle
  rm -f "$name.csr" "$name.cnf"
}
ca
HOSTS="app.lab a.lab weighted.lab leastconn.lab hash.lab sticky.lab retry.lab cb.lab health.lab canary.lab mirror.lab pp.lab h2.lab tls.lab auth.lab jwt.lab mtls.lab redirect.lab whoami.lab"
SAN="DNS:localhost,DNS:proxy,DNS:static,IP:127.0.0.1"; for h in $HOSTS; do SAN="$SAN,DNS:$h"; done
# (no wildcard: OpenSSL/curl refuse *.lab because it would match a whole TLD)
cert app.lab  app.lab  "$SAN" serverAuth
cert b.lab    b.lab    "DNS:b.lab" serverAuth
cert backend  backend.lab "DNS:backend.lab,DNS:passthrough.lab,DNS:app1,DNS:app2,DNS:app3,DNS:slow,DNS:flaky,DNS:canary,DNS:shadow,DNS:b1,DNS:localhost,IP:127.0.0.1" serverAuth
cert client   lab-client "DNS:client.lab,email:client@pxlab.test" clientAuth
cat app.lab.crt ca.crt > app.lab.fullchain.crt
cat b.lab.crt ca.crt > b.lab.fullchain.crt
cat backend.crt ca.crt > backend.fullchain.crt
rm -f ca.srl
# Pebble's CA for the ACME directory endpoint (the leaf certs it issues chain to a root generated at each start).
cid=$(docker create ghcr.io/letsencrypt/pebble:latest 2>/dev/null || true)
if [ -n "$cid" ]; then
  docker cp "$cid:/test/certs/pebble.minica.pem" pebble-ca.pem >/dev/null && docker cp "$cid:/test/config/pebble-config.json" ../pebble/pebble-config.default.json >/dev/null || true
  docker rm -f "$cid" >/dev/null
else
  echo "WARN: could not extract pebble CA (image missing?)"
fi
chmod 644 ./*.key ./*.crt ./*.pem

mkdir -p ../auth
htp() { docker run --rm pxlab-loadgen:latest htpasswd -nb "$@" 2>/dev/null | tr -d '\r' | sed '/^$/d'; }
htp -m lab lab-pass  > ../auth/htpasswd          # apr1 (nginx, apache, traefik, openresty, kong/apisix ignore)
htp -B lab lab-pass  > ../auth/htpasswd.bcrypt   # bcrypt (caddy, traefik)
htp -s lab lab-pass  > ../auth/htpasswd.sha1     # {SHA} (envoy basic_auth filter)
SECRET="pxlab-jwt-secret-please-change-0123456789"
printf '%s' "$SECRET" > ../auth/jwt.secret
K=$(printf '%s' "$SECRET" | openssl base64 -A | tr '+/' '-_' | tr -d '=')
cat > ../auth/jwt.jwks.json <<EOF
{"keys":[{"kty":"oct","kid":"pxlab","alg":"HS256","k":"$K"}]}
EOF
ls -la . ../auth
