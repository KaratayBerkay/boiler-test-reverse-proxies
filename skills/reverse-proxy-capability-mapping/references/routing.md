# Routing - construct per proxy

Probe ids: `route_host`, `route_path_prefix`, `route_path_regex`, `route_rewrite`, `route_redirect`, `route_header`,
`route_query`, `route_method`, `redirect_https`. All twelve proxies pass all nine except ATS (header/query routing).

## Host-based routing (`route_host`)
- **nginx / OpenResty**: `server { server_name a.lab; }` blocks; the `default_server` listen flag picks the fallback.
- **HAProxy**: one frontend; `http-request set-var(txn.h) req.hdr(host),field(1,:),lower` then `use_backend be_x if { var(txn.h) -m str a.lab }`.
- **Caddy**: site address `http://a.lab:8080, http://a.lab:80 { ... }`; TLS sites are separate blocks (a site cannot mix `tls` with an HTTP port).
- **Traefik**: router `rule: "Host(`a.lab`)"` with `priority: 100` (path routers lower); duplicate the router with `tls:` for websecure.
- **Envoy**: `virtual_hosts: - domains: [a.lab]` in the RouteConfiguration; `strip_any_host_port: true` on the HCM so `a.lab:8080` matches.
- **Apache**: `<VirtualHost *:8080> ServerName a.lab`; `ServerAlias` for extra names.
- **Varnish**: `if (req.http.X-Host == "a.lab")` in `vcl_recv` after stripping the port with `regsub(req.http.host, ":[0-9]+$", "")`.
- **Kong**: route `expression: 'http.host == "a.lab"'` (expressions router) with `priority: 100`.
- **APISIX**: route `hosts: [a.lab]`, `uri: "/*"`, `priority: 100`.
- **Pingora**: `match host.as_str() { "a.lab" => ... }` in `request_filter` (host copied out of the header first).
- **ATS**: `map http://a.lab:8080/ http://app1:8080/` - and one rule per port clients use (`a.lab`, `a.lab:8080`, `a.lab:18080`) because the request port is part of the match.

## Path prefix with prefix stripping (`route_path_prefix`)
- **nginx / OpenResty**: `location /api/ { proxy_pass http://pool_app/; }` - the trailing `/` (URI part) on `proxy_pass` replaces the matched prefix.
- **HAProxy**: `http-request set-path %[path,regsub(^/api/,/)] if { path_beg /api/ }`.
- **Caddy**: `handle_path /api/* { reverse_proxy ... }` (`handle` keeps the prefix, `handle_path` strips it).
- **Traefik**: middleware `stripPrefix: { prefixes: [/api] }`.
- **Envoy**: `route: { cluster: app, prefix_rewrite: / }` on `match: { prefix: /api/ }`.
- **Apache**: `ProxyPass /api/ balancer://app/` (trailing slash strips) + `<Location /api/> RequestHeader set X-Route api`.
- **Varnish**: `set req.url = regsub(req.url, "^/api/", "/")`.
- **Kong**: `strip_path: true` + `path_handling: v1` on the route (note: `strip_path` defaults to **true** and strips exact paths to `/` - set `false` on every other route).
- **APISIX**: `proxy-rewrite: { regex_uri: ["^/api/(.*)", "/$1"] }`.
- **Pingora**: `path.strip_prefix("/api/")` -> `set_uri`.
- **ATS**: `map http://app.lab/api/ http://app1:8080/` (the to-URL path replaces the from path).

## Regex path route (`route_path_regex`)
- nginx: `location ~ ^/v[0-9]+/`; HAProxy: `{ path_reg ^/v[0-9]+/ }`; Caddy: `@versioned path_regexp ^/v[0-9]+/` + `handle @versioned`; Traefik: `PathRegexp(`^/v[0-9]+/`)`; Envoy: `match: { safe_regex: { regex: "^/v[0-9]+/.*" } }`; Apache: `<LocationMatch "^/v[0-9]+/">`; Varnish: `req.url ~ "^/v[0-9]+/"`; Kong: `http.path ~ r#"^/v[0-9]+/"#`; APISIX: `uri: "/v*"` + `vars: [["uri", "~~", "^/v[0-9]+/"]]`; Pingora: hand-written check; ATS: `header_rewrite` `cond %{CLIENT-URL:PATH} /^v[0-9]+\//` (remap itself has no regex conditions; `regex_map` exists for host/path rewriting).

## Rewrite with capture (`route_rewrite`: `/old/x` -> `/new/x`)
- nginx: `rewrite ^/old/(.*)$ /new/$1 break;`; HAProxy: `set-path %[path,regsub(^/old/,/new/)]`; Caddy: `uri replace /old/ /new/` (or `uri replace` regex form); Traefik: `replacePathRegex: { regex: "^/old/(.*)", replacement: "/new/$1" }`; Envoy: `regex_rewrite: { pattern: { regex: "^/old/(.*)$" }, substitution: "/new/\\1" }`; Apache: `RewriteRule ^/old/(.*)$ /new/$1 [PT]`; Varnish: `regsub`; Kong: expression capture `r#"^/old/(?<rest>.*)$"#` + `request-transformer replace.uri "/new/$(uri_captures.rest)"`; APISIX: `proxy-rewrite regex_uri`; Pingora: `strip_prefix` + `format!`; ATS: `map http://app.lab/old/ http://app1:8080/new/`.

## Redirect issued by the proxy (`route_redirect`, `redirect_https`)
- nginx: `return 301 /landing;` / `return 301 https://$host$request_uri;`; HAProxy: `http-request redirect location /landing code 301` / `redirect scheme https code 301 if !{ ssl_fc }`; Caddy: `redir /redirect-me /landing 301` / `redir https://{host}{uri} 301`; Traefik: `redirectRegex` / `redirectScheme: { scheme: https, permanent: true }`; Envoy: `redirect: { path_redirect: /landing, response_code: MOVED_PERMANENTLY }` / `redirect: { https_redirect: true, port_redirect: 8443 }`; Apache: `Redirect permanent /redirect-me /landing` **plus** `ProxyPass /redirect-me !` (ProxyPass would shadow it) / `RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]`; Varnish: `return (synth(751))` + `vcl_synth` sets `Location`; Kong: `pre-function` `kong.response.exit(301, "", { Location = ... })`; APISIX: `redirect: { uri: /landing, ret_code: 301 }` / `redirect: { http_to_https: true }`; Pingora: `reply(301, Location)`; ATS: `header_rewrite` `set-redirect 301 "http://app.lab/landing"` in `REMAP_PSEUDO_HOOK` / `redirect http://redirect.lab/ https://redirect.lab/` rule.

## Header / query / method routing (`route_header`, `route_query`, `route_method`)
- **nginx / OpenResty**: `map $http_x_canary $pool_by_header { default pool_app; "1" pool_canary; }`, `map $arg_beta $pool_default { default $pool_by_header; "1" pool_canary; }`, `proxy_pass http://$pool_default` (variable proxy_pass needs `resolver`); method: `if ($request_method = DELETE) { return 405; }`.
- **HAProxy**: `use_backend be_canary if { req.hdr(X-Canary) -m str 1 } || { urlp(beta) -m str 1 }`; `http-request deny deny_status 405 if { path_beg /api/ } METH_DELETE`.
- **Caddy**: named matchers `@canary { header X-Canary 1 }`, `@beta query beta=1`, `@del { method DELETE  path /api/* }` + `handle @del { respond 405 }` (must be a `handle`, see order trap).
- **Traefik**: rules `Header(`X-Canary`, `1`)`, `Query(`beta`, `1`)`, `Method(`DELETE`) && PathPrefix(`/api/`)` with priorities.
- **Envoy**: `match: { prefix: /, headers: [{ name: X-Canary, string_match: { exact: "1" } }] }`, `query_parameters`, `headers: [{ name: ":method", string_match: { exact: DELETE } }]` + `direct_response`.
- **Apache**: `RewriteCond %{HTTP:X-Canary} =1` / `RewriteCond %{QUERY_STRING} (^|&)beta=1(&|$)` + `RewriteRule ^/(.*)$ http://canary:8080/$1 [P,L]`; `RewriteCond %{REQUEST_METHOD} =DELETE` + `[R=405,L]`.
- **Varnish**: `if (req.http.X-Canary == "1" || req.url ~ "(\?|&)beta=1(&|$)") { set req.backend_hint = canary; }`; `if (req.method == "DELETE" && req.url ~ "^/api/") { return (synth(405)); }`.
- **Kong**: `http.headers.x_canary == "1"`, `http.queries.beta == "1"`, `http.method == "DELETE" && http.path ^= "/api/"` expressions.
- **APISIX**: `vars: [["http_x_canary", "==", "1"]]`, `[["arg_beta", "==", "1"]]`; `methods: [DELETE]` + `fault-injection abort 405`.
- **Pingora**: plain Rust on the copied header/query/method values.
- **ATS**: **unsupported** for header/query (remap has no conditions; `header_rewrite set-destination` is overridden by a NextHop strategy) - use `cookie_remap`/`header_rewrite` only when no strategy is attached, or a separate remap host; method: `cond %{METHOD} =DELETE` + `set-status 405` works.
