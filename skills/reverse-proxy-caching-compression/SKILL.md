---
name: reverse-proxy-caching-compression
description: Configure HTTP response caching and compression on a reverse proxy, CDN node or gateway - honouring Cache-Control (max-age, stale-while-revalidate, stale-if-error), cache keys and Vary, HIT/MISS headers, purge/invalidation, serving stale on upstream errors, cache locking (request coalescing), what must never be cached (Set-Cookie, streaming, authenticated), and gzip/brotli/zstd negotiation with the SSE/WebSocket exceptions - for NGINX, HAProxy, Caddy (Souin), Traefik, Envoy, Apache mod_cache, Varnish, OpenResty, Kong, APISIX, Pingora and ATS. Use whenever a task mentions caching at the edge, cache purge, stale content, CDN behaviour, X-Cache headers, gzip/brotli/zstd, or slow large responses through a proxy.
---

# Caching and compression at the proxy

Verified in the reverse-proxies lab (`cache_hit`, `cache_purge`, `cache_stale_on_error`, `compress_gzip/brotli/zstd`
probes; `cache_hit` and `gzip_64k` load scenarios). Per-proxy constructs:
`reverse-proxy-capability-mapping/references/caching-compression.md`.

## Caching: what a proxy cache must do (and which ones do)
| requirement | how the lab tested it | proxies that pass | who cannot |
|---|---|---|---|
| store by origin `Cache-Control` (`max-age=60`) and serve HITs | second GET returns the same origin instance + counter | nginx, OpenResty, HAProxy, Caddy+Souin, Apache, Varnish, Kong, APISIX, Pingora, ATS | Traefik (no cache in OSS), Envoy (alpha filter breaks routes) |
| invalidate on demand | `PURGE /path` or the admin API, then a MISS | OpenResty (deletes the file), Caddy+Souin, Varnish, Kong (`DELETE /proxy-cache`), APISIX (disk strategy), ATS | nginx OSS (Plus/ngx_cache_purge; the lab refreshes instead), HAProxy, Apache (htcacheclean offline), Pingora (not wired) |
| serve stale when the origin 5xxs | `max-age=2`, wait, origin forced to 503, expect the old body | nginx/OpenResty `proxy_cache_use_stale`, Caddy `stale`, Apache `CacheStaleOnError`, Varnish grace + `abandon` on bgfetch 5xx, ATS `negative_revalidating` | HAProxy, Kong, APISIX, Pingora (MemCache expiry) |

Rules that keep a cache correct:
- **Key** = scheme + host + path (+ query when it matters). Add `Vary` handling (nginx honours `Vary` by default,
  HAProxy `process-vary on`, Varnish always) or you will serve gzip to clients that cannot read it.
- **Never cache** responses with `Set-Cookie` (Apache `CacheIgnoreHeaders Set-Cookie`, Varnish built-in VCL passes
  them), `Authorization` requests (unless `public`), `no-store`, streaming (`text/event-stream`), WebSocket upgrades,
  non-GET/HEAD.
- **Lock / coalesce** concurrent misses (`proxy_cache_lock on`, Varnish request coalescing by default, Pingora
  `CacheLock`, Apache `CacheLock On`) so a stampede reaches the origin once.
- **Background refresh** (`proxy_cache_background_update`, `stale-while-revalidate`, Varnish grace) keeps p99 flat.
- Expose the decision: `X-Cache: HIT|MISS|STALE` (`$upstream_cache_status`, `res.cache_hit`, `Cache-Status` RFC 9211
  in Caddy, `obj.hits`, `X-Cache-Status`, `Apisix-Cache-Status`, `%{CACHE}`), and log it.
- Purge safely: restrict `PURGE` to internal IPs (`allow 10.77.0.0/24; deny all;`, ACLs, admin API on the management
  port). Multi-worker caches (Varnish, Kong memory strategy, APISIX) can answer a PURGE on one worker and a HIT on
  another over a keep-alive connection - purge over a fresh connection or use the shared/disk strategy.
- Measure it: the `cache_hit` load scenario is the proxy's cache path throughput; if it is *lower* than plain
  proxying, the cache is on disk without RAM in front (ATS `ram_cache.size`, nginx page cache), or locking is too coarse
  - Caddy's Souin handler served one hot key at **1 662 rps / 199 ms p99** with 64 connections, 7x slower than proxying;
  nginx 63k, HAProxy 56k, OpenResty 53k, ATS 53k, Varnish 34k rps on the same test.
- Hot keys that are *being fetched*: ATS readers wait `read_while_writer_retry.delay` (50 ms default) for the writer -
  2 000 rps on one hot URL until it is set to 1 ms (28 000 after). nginx `proxy_cache_lock_timeout`, Varnish's
  request coalescing and Apache `CacheLock` have the same shape with saner defaults; know the timer.

## Compression
- Compress text types >= 256 bytes only (`gzip_min_length`, `min_content_length`, `minResponseBodyBytes`): small
  bodies get bigger, and every compressed byte costs CPU - the `gzip_64k` scenario spends more proxy CPU compressing
  than proxying.
- Levels: gzip 4-5 / brotli 4 / zstd 3 are the knee; brotli 11 belongs to build pipelines, not proxies.
- Availability: gzip everywhere; brotli in Caddy (plugin), Traefik, Envoy, Apache mod_brotli, APISIX; zstd in Caddy,
  Traefik, Envoy, Pingora. nginx/OpenResty/HAProxy/Varnish/Kong/ATS-Ubuntu are gzip-only in the official images.
- Send `Vary: Accept-Encoding` (`gzip_vary on`, `vary: true`) so caches key on encoding.
- **Do not compress streams**: SSE (`text/event-stream`) was buffered to death by gzip in Varnish and by the
  compression module in Pingora; exclude the type or set level 0 on those routes. Keep compressors out of WebSocket
  upgrade chains (Envoy).
- Let the proxy compress instead of the origin when the proxy caches: cache the uncompressed body and compress per
  client encoding (`remove-accept-encoding true` in ATS, `gzip_proxied any` in nginx), or you cache one encoding.
- Verify: `curl -sH 'Accept-Encoding: br' -D- URL/compressible -o /dev/null | grep -i content-encoding` and compare
  `Content-Length`; then `Accept-Encoding: identity` must return the original.
