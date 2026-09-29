# Caching and compression - construct per proxy

Probe ids: `cache_hit`, `cache_purge`, `cache_stale_on_error`, `compress_gzip`, `compress_brotli`, `compress_zstd`.
Contract: the origin sends `Cache-Control: public, max-age=60, stale-while-revalidate=30, stale-if-error=300`; the
proxy must honour it, expose HIT/MISS, invalidate on `PURGE` (or its own API) and serve stale when the origin 503s.

## Cache
| proxy | enable | hit indicator | purge | stale on error |
|---|---|---|---|---|
| nginx | `proxy_cache_path ... keys_zone=lab:16m; proxy_cache lab; proxy_cache_key $scheme$host$uri; proxy_cache_lock on; proxy_cache_background_update on` | `add_header X-Cache $upstream_cache_status always` | OSS has no purge: `proxy_cache_purge` is Plus / ngx_cache_purge; the lab loops `PURGE` back as `GET` + `proxy_cache_bypass $http_x_refresh` (a refresh, not a delete) | `proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504` |
| OpenResty | same as nginx | same | real: `content_by_lua_block` computes the cache file path (`md5(key)`, `levels=1:2`) and `os.remove`s it | same |
| HAProxy | `cache lab { total-max-size 256; max-object-size 262144; max-age 60 }` + `filter cache lab` + `http-request cache-use lab` / `http-response cache-store lab` | `http-response set-header X-Cache HIT if { res.cache_hit }` | **unsupported** (small-object accelerator, entries expire) | **unsupported** |
| Caddy (Souin cache-handler) | global `cache { ttl 60s  stale 300s  default_cache_control public }` + `order cache before rewrite` + `cache` directive in the handle | `Cache-Status` header (RFC 9211) | `PURGE /path` (also Souin's API) | stale served (`stale 300s`) |
| Traefik | **unsupported** (no cache in OSS) | | | |
| Envoy | **unsupported** in the lab: the alpha `envoy.filters.http.cache` makes an internal request that bypasses route behaviour for every route | | | |
| Apache | `CacheEnable disk "/cacheable/"`, `CacheRoot`, `CacheLock On`, `CacheQuickHandler Off` (so headers modules run on hits) | `CacheHeader On` -> `X-Cache: HIT/MISS`, `CacheDetailHeader On` | **unsupported** (htcacheclean offline) | `CacheStaleOnError On` |
| Varnish | default `vcl_recv` -> `hash`; the origin's Cache-Control sets the TTL | `X-Cache` from `obj.hits` in `vcl_deliver` | `return (purge)` on `req.method == "PURGE"` | `beresp.grace = 300s` + `if (bereq.is_bgfetch && beresp.status >= 500) { return (abandon); }` |
| Kong | `proxy-cache { strategy: memory, cache_control: true, cache_ttl: 60, content_type: [...] }` | `X-Cache-Status` | admin API `DELETE /proxy-cache` (or `/proxy-cache/<key>`) | **unsupported** |
| APISIX | `proxy-cache { cache_strategy: disk, cache_zone: disk_cache_one, cache_key: [$host, $request_uri], cache_control: true }` | `Apisix-Cache-Status` | `PURGE` on the URL (disk strategy only; use a fresh connection) | **unsupported** |
| Pingora | `session.cache.enable(MemCache, LRU, CacheLock)` in `request_cache_filter`, `cache_key_callback`, `response_cache_filter` -> `resp_cacheable(CacheControl, CacheMetaDefaults)` | `X-Cache` from `session.cache.phase()` | PURGE handled by pingora-proxy when the storage implements purge (left out) | `should_serve_stale` hook (MemCache expired objects before the 2 s test window) |
| ATS | `proxy.config.http.cache.http INT 1`, `cache.required_headers INT 2`, `ram_cache.size`, `storage.config`; set `read_while_writer_retry.delay 1` + `open_read_retry_time 1` (defaults 50/10 ms) or concurrent requests for one in-flight URL wait on the writer (2k rps instead of 28k) | `header_rewrite` `set-header X-Cache %{CACHE}` (or `xdebug.so`) | `PURGE` method (enable per remap / `proxy.config.http.push_method_enabled` for PUSH) | `negative_revalidating_enabled INT 1` |

Lab rules that keep cache probes honest: compare `(instance, X-Backend-Counter)` of the origin, not bodies; Varnish and
Kong serve HIT from a different worker than the one that stored it; `PURGE` on a keep-alive connection sometimes hits the
wrong worker (APISIX) - retry on a fresh connection.

## Compression
| proxy | gzip | brotli | zstd | notes |
|---|---|---|---|---|
| nginx / OpenResty | `gzip on; gzip_types ...; gzip_min_length 256; gzip_proxied any; gzip_vary on` | third-party `ngx_brotli` (not in official image) | third-party | SSE must not be compressed (`gzip` skips `text/event-stream` unless listed) |
| HAProxy | `compression algo-res gzip` + `compression type ...` (libslz) | **no** | **no** | `filter compression` when other filters are declared |
| Caddy | `encode zstd br gzip` | via `caddy-brotli` plugin | built in | order in the directive = preference |
| Traefik | `compress: { encodings: [zstd, br, gzip], minResponseBodyBytes: 256 }` | built in | built in | |
| Envoy | `envoy.filters.http.compressor` x3 with `compressor_library` gzip / brotli / zstd; `min_content_length`, `content_type` | built in | built in | keep compressors out of the WebSocket upgrade chain |
| Apache | `AddOutputFilterByType DEFLATE ...` (mod_deflate) | `AddOutputFilterByType BROTLI_COMPRESS ...` (mod_brotli) | **no** | |
| Varnish | `-p http_gzip_support=on` + `set beresp.do_gzip = true` for text (not `event-stream`) | **no** | **no** | gzip buffers SSE - exclude it |
| Kong | nginx gzip injected: `KONG_NGINX_PROXY_GZIP=on`, `..._GZIP_TYPES`, `..._GZIP_MIN_LENGTH` | **no** | **no** | no compression plugin in OSS |
| APISIX | `gzip` plugin (`min_length`, `comp_level`, `types`, `vary`) | `brotli` plugin | **no** | both as global rules |
| Pingora | `ResponseCompressionBuilder::enable(0)` module + `adjust_level(5)` per request | feature-gated (not in this build) | built in | level 0 for streaming responses |
| ATS | `compress.so compress.config` (`supported-algorithms gzip,br`) | only if the build has brotli (Ubuntu's does not) | **no** | `remove-accept-encoding true` so the origin does not compress |
