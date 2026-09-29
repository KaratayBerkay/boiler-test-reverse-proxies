# Stack index (from reverse-proxies/stacks/*/compose.yaml, verified 2026-09)

Common to all: `cpuset: "0-3"`, `ulimits.nofile 1048576`, network `pxlab` (external, `10.77.0.0/24`) with aliases
`proxy app.lab a.lab b.lab acme.lab redirect.lab`, mounts `../../shared/certs:/certs:ro`,
`../../shared/static:/static:ro` (+ `../../shared/auth:/auth:ro` where htpasswd/JWKS are needed), host ports
18080/18443(+udp)/18444/18445/18082/19000/19001udp/19100/19101.

## nginx - `nginx:1.29-otel` (250 MB; njs, otel, acme modules included)
- command: `["nginx", "-c", "/etc/nginx/lab/nginx.conf", "-g", "daemon off;"]`; mount `./:/etc/nginx/lab:ro`, volume `nginx-cache:/var/cache/nginx`.
- healthcheck: `curl -fsS http://127.0.0.1:9101/healthz` (image has curl).
- sidecar: `nginx/nginx-prometheus-exporter:1.4 --nginx.scrape-uri=http://proxy:9101/nginx_status` -> 19100:9113, `depends_on: proxy: condition: service_healthy`.
- reload: `nginx -c /etc/nginx/lab/nginx.conf -s reload`. Startup ~3 s.

## haproxy - `haproxy:lts` (3.4)
- mount `./:/usr/local/etc/haproxy:ro` (haproxy.cfg + lab.lua + errors/); runs as `haproxy` -> `sysctls: net.ipv4.ip_unprivileged_port_start: 0` for :80.
- healthcheck: `bash -c "exec 3<>/dev/tcp/127.0.0.1/9999 && echo 'show info' >&3 && timeout 2 grep -q -m1 Uptime <&3"` (runtime API on `stats socket ipv4@0.0.0.0:9999`); also publish 19999:9999 for host-side `socat`.
- reload: `haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg -q && kill -USR2 1` (master-worker is the image default).

## caddy - custom `pxlab-caddy` (FROM `caddy:2-builder` xcaddy `--with github.com/mholt/caddy-ratelimit --with github.com/mholt/caddy-l4 --with github.com/ggicci/caddy-jwt --with github.com/ueffel/caddy-brotli --with github.com/caddyserver/cache-handler`; then `FROM caddy:2` + `COPY --from=builder /usr/bin/caddy /usr/bin/caddy`)
- command: `caddy run --config /etc/caddy/Caddyfile --adapter caddyfile`; mount `./:/etc/caddy:ro` (directory), a volume for `/data` if certificates must survive restarts.
- env for tracing: `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, `OTEL_TRACES_SAMPLER=parentbased_traceidratio`, `OTEL_TRACES_SAMPLER_ARG=0.001`.
- admin API: `admin 0.0.0.0:2019` -> publish 19101:2019. healthcheck: `wget -qO- http://127.0.0.1:9100/healthz` (busybox wget exists, no curl).
- reload: `caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile`.

## traefik - `traefik:v3` (3.7)
- command: `--configFile=/etc/traefik/traefik.yml`; mounts `./traefik.yml:/etc/traefik/traefik.yml:ro`, `./dynamic:/etc/traefik/dynamic:ro`, `/var/run/docker.sock:/var/run/docker.sock:ro` (Docker provider), volume `traefik-data:/data` (acme.json).
- env: `LEGO_CA_CERTIFICATES=/certs/pebble-ca.pem` for a private ACME CA.
- healthcheck: `traefik healthcheck --configFile=...` (needs `ping:` in the static config).
- reload: edit `dynamic/dynamic.yml` (`providers.file.watch: true`).

## envoy - `envoyproxy/envoy:v1.39-latest`
- command: `["envoy", "-c", "/etc/envoy/envoy.yaml", "--concurrency", "4", "--log-level", "warn", "--log-format", "%L %v"]`; mount `./:/etc/envoy:ro` (bootstrap + lds/cds/rds files; `watched_directory` = the mount); `pre_up: python3 gen.py` builds `lds.yaml`.
- healthcheck: `bash -c "exec 3<>/dev/tcp/127.0.0.1/9101; printf 'GET /ready HTTP/1.1\r\nHost: admin\r\nConnection: close\r\n\r\n' >&3; timeout 3 cat <&3 | grep -q LIVE"`.
- reload: `sed -i 's/^version_info: .*/version_info: "<epoch>"/' rds.yaml` (or rename a regenerated file into the directory).

## apache - `httpd:2.4` + `lusotycoon/apache-exporter`
- command: `sh -c "(while sleep 1; do if [ -f /md/reload.flag ]; then rm -f /md/reload.flag; httpd -k graceful -f /usr/local/apache2/lab/httpd.conf; fi; done) & exec httpd-foreground -f /usr/local/apache2/lab/httpd.conf"` (root loop turns mod_md's unprivileged hook into a graceful restart).
- mounts: `./:/usr/local/apache2/lab:ro`, `../../shared/certs/pebble-ca.pem:/etc/ssl/certs/ca-certificates.crt:ro` (mod_md trusts the system bundle only); `tmpfs: [/md:mode=1777, /var/cache/apache:mode=1777]`.
- healthcheck: bash `/dev/tcp` GET `/server-status?auto` on :9101, grep `Uptime`. exporter: `--scrape_uri=http://proxy:9101/server-status?auto`.
- reload: `httpd -k graceful -f ...`.

## varnish - `varnish:8.0` + `hitch:latest` + varnishncsa + custom exporter (`varnish:8.0` + prometheus_varnish_exporter 1.6.1)
- varnishd: `varnishd -F -n /var/lib/varnish/pxlab -f /etc/varnish/default.vcl -a http=:8080,HTTP -a http80=:80,HTTP -a proxy=:6086,PROXY -a pp=:8082,PROXY -p feature=+http2 -p http_gzip_support=on -p thread_pools=2 -p thread_pool_min=200 -p thread_pool_max=4000 -p workspace_client=128k -p http_req_size=64k -s malloc,512m -t 120`; volume `varnish-vsm:/var/lib/varnish` shared with the varnishncsa and exporter containers (they read the VSM); `./default.vcl:/etc/varnish/default.vcl:ro` (single file: recreate after edits).
- hitch: `hitch --config /etc/hitch/hitch.conf` with `/certs` (needs `.pem` = key+cert bundles), publishes 8443/8444.
- healthcheck: `varnishadm -n /var/lib/varnish/pxlab status`. reload: `varnishreload -n /var/lib/varnish/pxlab`.
- access log = `docker logs pxlab-varnish-log` (varnishncsa `-F` JSON).

## openresty - custom (`openresty/openresty:1.27.1.2-alpine-fat` + `opm get SkyLothar/lua-resty-jwt knyar/nginx-lua-prometheus fffonion/lua-resty-acme ledgetech/lua-resty-http` + `apk add curl`)
- command: `openresty -c /etc/openresty/nginx.conf -g 'daemon off;'`; mount `./:/etc/openresty:ro`; env `ACME_EAGER=1`; volume for `/var/cache/nginx`.
- healthcheck: `curl -fsS http://127.0.0.1:9101/healthz`. reload: `openresty -c ... -s reload`.

## kong - `kong:3.9`, `user: kong`
- env: `KONG_DATABASE=off`, `KONG_DECLARATIVE_CONFIG=/kong/kong.yml`, `KONG_ROUTER_FLAVOR=expressions`, `KONG_PROXY_LISTEN`, `KONG_STREAM_LISTEN` (`... 8445 ssl` for tls_passthrough), `KONG_ADMIN_LISTEN=0.0.0.0:8001`, `KONG_STATUS_LISTEN=0.0.0.0:9100`, `KONG_ADMIN_GUI_LISTEN=off` (Manager would take 8445), `KONG_SSL_CERT/KEY`, `KONG_TRUSTED_IPS`, `KONG_REAL_IP_HEADER=proxy_protocol`, `KONG_LUA_SSL_TRUSTED_CERTIFICATE`, `KONG_NGINX_WORKER_PROCESSES=4`, `KONG_UPSTREAM_KEEPALIVE_POOL_SIZE`, `KONG_NGINX_HTTP_LOG_FORMAT` + `KONG_PROXY_ACCESS_LOG=/dev/stdout json_lab`, `KONG_NGINX_PROXY_GZIP=on`, `KONG_TRACING_INSTRUMENTATIONS=all`, `KONG_PLUGINS=bundled`, `KONG_UNTRUSTED_LUA=on`.
- `sysctls: net.ipv4.ip_unprivileged_port_start: 0`; mount `./kong.yml:/kong/kong.yml:ro` (generated by `gen.py`).
- healthcheck: `kong health`. reload: `curl -X POST http://127.0.0.1:19101/config -F config=@kong.yml`.

## apisix - `apache/apisix:3.15.0-debian`
- mounts: `./config.yaml:/usr/local/apisix/conf/config.yaml:ro`, `./apisix.yaml:/usr/local/apisix/conf/apisix.yaml:ro` (generated); `deployment.role_data_plane.config_provider: yaml`.
- healthcheck: bash `/dev/tcp` GET `/v1/healthcheck` on :9101 (control API), grep `200 OK`; no curl/wget.
- reload: `touch apisix.yaml` after regenerating.

## pingora - custom (`rust:1-slim` build with `pkg-config libssl-dev cmake perl make g++`; runtime `debian:trixie-slim` + `libssl3t64 ca-certificates curl procps`)
- CMD `sh -c "pingora-lab -c /etc/pingora/config.yaml; while true; do sleep 3600; done"` (PID 1 survives the upgrade); mount `./config.yaml:/etc/pingora/config.yaml:ro`; `.dockerignore` with `target/`.
- healthcheck: `curl -fsS http://127.0.0.1:9100/healthz`. reload: `OLD=$(pgrep -o -x pingora-lab); nohup pingora-lab -u -c /etc/pingora/config.yaml >/proc/1/fd/1 2>/proc/1/fd/2 & sleep 0.5; kill -QUIT $OLD`.

## ats - custom (`ubuntu:24.04` + `trafficserver trafficserver-experimental-plugins curl`, `USER trafficserver`)
- command: `traffic_manager --nosyslog` (manager + server; `traffic_ctl` needs the manager); mounts for `records.config`, `remap.config` (generated), `strategies.yaml`, `sni.yaml`, `ssl_multicert.config`, `plugin.config`, `compress.config`, `logging.yaml`, `ip_allow.yaml`, `storage.config`, `hdr/`; `sysctls: net.ipv4.ip_unprivileged_port_start: 0`.
- healthcheck: `curl -fsS -H 'Host: app.lab' http://127.0.0.1:8080/_stats` (stats_over_http). reload: `traffic_ctl config reload`. Access log is a file: `/var/log/trafficserver/access.log`.

## shared backends (`reverse-proxies/shared/compose.yaml`)
Go origin image `pxlab-backend` (h1+h2c :8080, PROXY :8081, TLS :8443, gRPC :9090, UDP :9002) x8 with static IPs and
env `INSTANCE/POOL/DELAY_MS/FAIL_RATE`; `ghcr.io/letsencrypt/pebble:latest` (`-config /config/pebble-config.json
-dnsserver 127.0.0.11:53`, http 80 / tls 443, directory :14000); `jaegertracing/jaeger:2.9.0` (4317/4318/16686);
`nginx:1.29-otel` static origin (error page, ACME directory shim for Kong); `traefik/whoami` with labels.
