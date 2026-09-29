---
name: docker-compose-reverse-proxies
description: Stand up any reverse proxy or API gateway in Docker Compose the way that actually works - NGINX, HAProxy, Caddy, Traefik, Envoy, Apache httpd, Varnish+hitch, OpenResty, Kong (DB-less), APISIX (standalone), a Pingora/Rust proxy, Apache Traffic Server - with verified images, entrypoints, mounts, healthchecks for images without curl, unprivileged port 80, writable state, CPU pinning, registry-mirror pulls and reload commands. Use this whenever someone writes or debugs a compose file / Dockerfile / container healthcheck for a proxy, gateway, ingress or load balancer, asks which image tag to use, or hits "config change not picked up", "port already allocated", "permission denied binding :80", "healthcheck failing" for one of these.
---

# Reverse proxies in Docker Compose

Every pattern here runs in `reverse-proxies/stacks/<proxy>/compose.yaml` and was exercised by 69 probes + load + chaos
per proxy. `references/stack-index.md` has the per-proxy facts (image, command, mounts, healthcheck, reload, ports,
gotchas). Read that file for the proxy at hand; this page has the rules that apply to all of them.

## Rules that saved the most time

1. **Mount the config directory, not the file.** Editors and `sed -i` replace the inode; a single-file bind mount keeps
   serving the old content inside the container. Mount `./:/etc/<proxy>/lab:ro` and point the command at the file.
2. **Compose does not recreate a container when only a mounted config changed.** Use `docker compose up -d
   --force-recreate` (the lab's `pxlab up` always does) or the proxy's reload command.
3. **Healthchecks without curl.** Most official images (haproxy, envoy, httpd, apisix) have no curl/wget. Use bash's
   `/dev/tcp`: `exec 3<>/dev/tcp/127.0.0.1/9101; printf 'GET /ready HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n' >&3;
   timeout 3 cat <&3 | grep -q LIVE` - or the proxy's own CLI (`kong health`, `traefik healthcheck`, `varnishadm status`).
   Envoy's admin rejects HTTP/1.0, so send HTTP/1.1 with a Host header.
4. **Port 80 as a non-root user** (needed for ACME HTTP-01): `sysctls: net.ipv4.ip_unprivileged_port_start: 0`
   (haproxy, kong, ats). Images whose master runs as root (nginx, httpd, traefik, envoy, varnish) do not need it.
5. **Writable state on read-only images**: tmpfs with `mode=1777` for Apache's `mod_md` store and `mod_cache_disk`
   root; named volumes for nginx/OpenResty `proxy_cache_path`, Caddy `/data`, Traefik `/data/acme.json`.
6. **Generated configs**: Envoy (`lds.src.yaml` -> `lds.yaml`), Kong (`kong.src.yml` -> `kong.yml`, PEMs inlined),
   APISIX (`apisix.src.yaml` -> `apisix.yaml`, `#END` marker), ATS (`remap.spec` -> `remap.config`) run a `gen.py`
   before `up`. Commit the source, ignore the output, and write via tmp+rename for watched directories (Envoy reacts to
   `MOVED_TO`).
7. **Sidecars instead of custom builds** when a proxy lacks metrics: `nginx/nginx-prometheus-exporter`,
   `lusotycoon/apache-exporter`, `prometheus_varnish_exporter` on the shared VSM directory, `varnishncsa` for JSON logs.
8. **Build only when you must**: Caddy (`caddy:2-builder` + `xcaddy build --with ...`), OpenResty (`opm get`),
   Pingora (`rust:1-slim` -> `debian:trixie-slim`, PID 1 = `sh` so a socket-handoff upgrade does not kill the
   container), ATS (Ubuntu packages - there is no official image).
9. **Pull through a mirror.** Anonymous Docker Hub allows 100 manifest pulls / 6 h; `scripts/pull-images.sh` pulls
   `mirror.gcr.io/library/<image>` and re-tags it, so compose files keep canonical names.
10. **Pin CPUs when you measure.** `cpuset: "0-3"` on the proxy, other cpusets on backends and the load generator;
    read `/sys/fs/cgroup/system.slice/docker-<id>.scope/cpu.stat` for exact CPU seconds per container.
11. **ulimits** for c10k-style tests: `ulimits: { nofile: { soft: 1048576, hard: 1048576 } }` on the proxy **and** the
    load generator (`docker run --ulimit nofile=...`).
12. **Network aliases** make one stack answer for many hostnames on the compose network:
    `networks: { pxlab: { aliases: [proxy, app.lab, a.lab, b.lab, acme.lab] } }` - clients inside the network resolve them,
    ACME challengers reach the proxy by name, and no `/etc/hosts` editing is needed.

## Minimal skeleton (fill from the stack index)

```yaml
name: pxlab-<proxy>
services:
  proxy:
    image: <image from references/stack-index.md>
    container_name: pxlab-<proxy>
    cpuset: "0-3"
    command: [<see index>]
    volumes:
      - ./:/etc/<proxy>/lab:ro            # config DIRECTORY
      - ../../shared/certs:/certs:ro
      - ../../shared/static:/static:ro
    ports: ["18080:8080", "18443:8443", "18443:8443/udp", "18444:8444", "18445:8445", "18082:8082",
            "19000:9000", "19001:9001/udp", "19100:9100", "19101:9101"]
    ulimits: { nofile: { soft: 1048576, hard: 1048576 } }
    networks: { pxlab: { aliases: [proxy, app.lab, a.lab, b.lab, acme.lab, redirect.lab] } }
    healthcheck: { test: [<see index>], interval: 2s, timeout: 3s, retries: 30 }
networks:
  pxlab: { external: true, name: pxlab }
```

## Debugging order when a stack will not come up
1. `docker compose logs proxy` - config parse errors are printed once and the container restarts in a loop.
2. Validate the config with the proxy's own checker: `nginx -t`, `haproxy -c -f`, `caddy validate`,
   `envoy --mode validate -c`, `httpd -t`, `varnishd -C -f`, `kong config parse kong.yml`, `apisix test`,
   `traffic_server -Cverify_config` (ATS 9: `-Cverify_config` is unreliable; read the diags).
3. `docker inspect --format '{{json .State.Health}}'` - a stack marked "starting" forever usually has a healthcheck that
   needs a tool the image lacks.
4. `docker run --rm --network <net> curlimages/curl -sv -H 'Host: app.lab' http://proxy:8080/` from inside the network -
   host-side tests go through docker-proxy and show `10.77.0.1` as the client IP.

## Files
- `references/stack-index.md` - one section per proxy: image, entrypoint, mounts, ports, healthcheck, reload, env, gotchas.
- Full working stacks: `reverse-proxies/stacks/<proxy>/`, shared backends in `reverse-proxies/shared/compose.yaml`.
