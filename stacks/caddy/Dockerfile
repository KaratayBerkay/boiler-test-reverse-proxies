# Caddy 2 with the plugins the lab needs (the official image has no rate limiting, no L4, no JWT, no brotli, no cache):
#   caddy-ratelimit (Matt Holt), caddy-l4 (TCP/UDP/TLS passthrough), caddy-jwt, caddy-brotli, cache-handler (Souin).
# `xcaddy build` compiles Caddy with the modules; this is THE way to extend Caddy.
FROM caddy:2-builder AS builder
RUN xcaddy build \
    --with github.com/mholt/caddy-ratelimit \
    --with github.com/mholt/caddy-l4 \
    --with github.com/ggicci/caddy-jwt \
    --with github.com/ueffel/caddy-brotli \
    --with github.com/caddyserver/cache-handler

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
