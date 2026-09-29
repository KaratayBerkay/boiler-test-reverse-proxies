# pxlab reference configuration for Varnish Cache 8 (official image) with hitch in front for TLS.
# Implements the lab contract (docs/contract.md); annotated walkthrough: docs/configs/varnish.md.
vcl 4.1;

import directors;
import std;
import proxy;          # PROXY-protocol TLVs from hitch (proxy.is_ssl())
import vsthrottle;     # request rate limiting
import digest;         # HMAC / base64 -> JWT verification in VCL
import reqwest;        # HTTP client (forward auth) and HTTPS/HTTP-2 backends
import saintmode;      # passive per-object backend blacklisting (outlier ejection)
import fileserver;     # serve files from disk as a backend
import uuid;           # request ids
import cookie;

probe hc {
    .url = "/healthz";
    .interval = 1s;
    .timeout = 1s;
    .window = 3;
    .threshold = 2;
    .initial = 3;
}

backend app1   { .host = "app1";   .port = "8080"; .probe = hc; .max_connections = 4000; .connect_timeout = 3s; .first_byte_timeout = 30s; }
backend app2   { .host = "app2";   .port = "8080"; .probe = hc; .max_connections = 4000; .connect_timeout = 3s; .first_byte_timeout = 30s; }
backend app3   { .host = "app3";   .port = "8080"; .probe = hc; .max_connections = 4000; .connect_timeout = 3s; .first_byte_timeout = 30s; }
backend flaky  { .host = "flaky";  .port = "8080"; .probe = hc; }
backend canary { .host = "canary"; .port = "8080"; .probe = hc; }
backend b1     { .host = "b1";     .port = "8080"; .probe = hc; }
backend dead   { .host = "app3";   .port = "8099"; }                          # nothing listens here (retry demo)
backend app1_pp { .host = "app1";  .port = "8081"; .proxy_header = 2; }      # PROXY protocol v2 towards the upstream
backend app1_t2 { .host = "app1";  .port = "8080"; .first_byte_timeout = 2s; .connect_timeout = 3s; }   # /timeout

acl lab_net   { "10.77.0.0"/24; }
acl host_only { "10.77.0.1"; }

sub vcl_init {
    new rr = directors.round_robin();
    rr.add_backend(app1); rr.add_backend(app2); rr.add_backend(app3);

    new weighted = directors.random();                      # random director = weighted
    weighted.add_backend(app1, 3.0); weighted.add_backend(app2, 1.0);

    new hash = directors.shard();                           # consistent hashing on a key (X-User)
    hash.add_backend(app1); hash.add_backend(app2); hash.add_backend(app3);
    hash.reconfigure();

    new retry = directors.round_robin();
    retry.add_backend(app1); retry.add_backend(app2); retry.add_backend(dead);

    new sm_app1 = saintmode.saintmode(app1, 5);             # saintmode: per-object denylist after 5xx (outlier ejection)
    new sm_app2 = saintmode.saintmode(app2, 5);
    new sm_flaky = saintmode.saintmode(flaky, 5);
    new cb = directors.round_robin();
    cb.add_backend(sm_app1.backend()); cb.add_backend(sm_app2.backend()); cb.add_backend(sm_flaky.backend());

    new canary_split = directors.random();                  # 90 / 10
    canary_split.add_backend(app1, 30.0); canary_split.add_backend(app2, 30.0); canary_split.add_backend(app3, 30.0);
    canary_split.add_backend(canary, 10.0);

    new fs = fileserver.root("/static");                    # static files as a backend

    new authsvc = reqwest.client(timeout = 2s, connect_timeout = 1s);      # forward-auth HTTP client
    # HTTPS (and HTTP/2 via ALPN) backend through vmod_reqwest; the lab CA is not in the system store -> no verification here
    new tlsbe = reqwest.client(base_url = "https://app1:8443", accept_invalid_certs = true, accept_invalid_hostnames = true, timeout = 30s);
}

sub vcl_recv {
    # --- headers every upstream sees
    set req.http.X-Lab-Proxy = "varnish";
    if (!req.http.X-Request-ID) { set req.http.X-Request-ID = uuid.uuid_v4(); }
    if (proxy.is_ssl()) { set req.http.X-Forwarded-Proto = "https"; } else { set req.http.X-Forwarded-Proto = "http"; }
    set req.http.X-Forwarded-Host = req.http.host;
    set req.http.X-Real-IP = client.ip;
    set req.http.Forwarded = "for=" + client.ip + ";proto=" + req.http.X-Forwarded-Proto + ";host=" + req.http.host;
    set req.http.X-Host = regsub(req.http.host, ":[0-9]+$", "");
    unset req.http.X-Route;

    if (req.method == "PURGE") {
        if (req.url ~ "^/cacheable") { return (purge); }
        return (synth(405));
    }
    if (req.http.Upgrade ~ "(?i)websocket") { return (pipe); }

    # --- host-based behaviour
    if (req.http.X-Host == "redirect.lab" && !proxy.is_ssl()) { return (synth(750)); }
    if (req.http.X-Host == "a.lab")        { set req.http.X-Route = "a"; set req.backend_hint = rr.backend(); }
    elsif (req.http.X-Host == "b.lab")     { set req.http.X-Route = "b"; set req.backend_hint = b1; }
    elsif (req.http.X-Host == "weighted.lab")  { set req.backend_hint = weighted.backend(); }
    elsif (req.http.X-Host == "hash.lab")      { set req.backend_hint = hash.backend(by = KEY, key = hash.key(req.http.X-User)); }
    elsif (req.http.X-Host == "sticky.lab") {                              # cookie -> exact backend; first visit gets the cookie
        cookie.parse(req.http.Cookie);
        if (cookie.get("lab_sticky") == "app1")      { set req.backend_hint = app1; }
        elsif (cookie.get("lab_sticky") == "app2")   { set req.backend_hint = app2; }
        elsif (cookie.get("lab_sticky") == "app3")   { set req.backend_hint = app3; }
        else { set req.backend_hint = rr.backend(); set req.http.X-Sticky-New = "1"; }
    }
    elsif (req.http.X-Host == "retry.lab")     { set req.backend_hint = retry.backend(); set req.http.X-Retry = "1"; }
    elsif (req.http.X-Host == "cb.lab")        { set req.backend_hint = cb.backend(); set req.http.X-CB = "1"; }
    elsif (req.http.X-Host == "canary.lab")    { set req.backend_hint = canary_split.backend(); }
    elsif (req.http.X-Host == "pp.lab")        { set req.backend_hint = app1_pp; }
    elsif (req.http.X-Host == "tls.lab" || req.http.X-Host == "h2.lab") { set req.backend_hint = tlsbe.backend(); }
    elsif (req.http.X-Host == "auth.lab") {                                # forward auth with vmod_reqwest
        authsvc.init("auth", "http://app1:8080/auth", "GET");
        if (req.http.X-Auth-Token) { authsvc.set_header("auth", "X-Auth-Token", req.http.X-Auth-Token); }
        if (req.http.Authorization) { authsvc.set_header("auth", "Authorization", req.http.Authorization); }
        authsvc.send("auth");
        if (authsvc.status("auth") != 200) { return (synth(401)); }
        set req.http.X-Auth-User = authsvc.header("auth", "X-Auth-User");
        set req.backend_hint = rr.backend();
    }
    elsif (req.http.X-Host == "jwt.lab") {                                 # HS256 JWT verified with vmod_digest
        if (req.http.Authorization !~ "^Bearer [A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$") { return (synth(401)); }
        set req.http.X-JWT = regsub(req.http.Authorization, "^Bearer ", "");
        set req.http.X-JWT-Body = regsub(req.http.X-JWT, "\.[^.]+$", "");
        set req.http.X-JWT-Sig = regsub(req.http.X-JWT, "^[^.]+\.[^.]+\.", "");
        if (digest.base64url_nopad_hex(digest.hmac_sha256("pxlab-jwt-secret-please-change-0123456789", req.http.X-JWT-Body)) != req.http.X-JWT-Sig) {
            return (synth(401));
        }
        set req.http.X-JWT-Payload = digest.base64url_decode(regsub(req.http.X-JWT-Body, "^[^.]+\.", ""));
        if (req.http.X-JWT-Payload ~ {""exp":[0-9]+"} && std.real(regsub(req.http.X-JWT-Payload, {"^.*"exp":([0-9]+).*$"}, "\1"), 0.0) < std.real(now, 0.0)) {
            return (synth(401));
        }
        set req.http.X-JWT-Sub = regsub(req.http.X-JWT-Payload, {"^.*"sub":"([^"]*)".*$"}, "\1");
        unset req.http.X-JWT; unset req.http.X-JWT-Body; unset req.http.X-JWT-Sig; unset req.http.X-JWT-Payload;
        set req.backend_hint = rr.backend();
    }
    else { set req.backend_hint = rr.backend(); }          # app.lab, leastconn/health/mirror/localhost/proxy/...

    # --- path-based behaviour (default vhost)
    if (req.method == "DELETE" && req.url ~ "^/api/") { return (synth(405)); }
    if (req.http.X-Canary == "1" || req.url ~ "(\?|&)beta=1(&|$)") { set req.backend_hint = canary; }
    if (req.url ~ "^/api/")       { set req.http.X-Route = "api"; set req.url = regsub(req.url, "^/api/", "/"); }
    if (req.url ~ "^/v[0-9]+/")   { set req.http.X-Route = "versioned"; }
    if (req.url ~ "^/old/")       { set req.http.X-Route = "rewritten"; set req.url = regsub(req.url, "^/old/", "/new/"); }
    if (req.url == "/redirect-me") { return (synth(751)); }
    if (req.url == "/limited" && vsthrottle.is_denied("" + client.ip, 10, 1s, 10s)) { return (synth(429)); }
    if (req.url == "/conn-limited") { set req.url = "/delay/1000"; }
    if (req.url == "/allowed" && client.ip !~ host_only) { return (synth(403)); }
    if (req.url == "/denied" && client.ip ~ lab_net)     { return (synth(403)); }
    if (req.url == "/basic" && req.http.Authorization != ("Basic " + digest.base64("lab:lab-pass"))) { return (synth(401)); }
    if (req.url == "/upload" && std.integer(req.http.Content-Length, 0) > 1048576) { return (synth(413)); }
    if (req.url == "/timeout")    { set req.url = "/delay/5000"; set req.backend_hint = app1_t2; }
    if (req.url == "/fault" && std.random(0, 100) < 20) { return (synth(503)); }
    if (req.url == "/bw")         { set req.url = "/bin/1048576"; }
    if (req.url ~ "^/static/")    { set req.url = regsub(req.url, "^/static/", "/"); set req.backend_hint = fs.backend(); return (pass); }
    if (req.url == "/error-page") { set req.url = "/status/503"; set req.http.X-Custom-Error = "1"; }
    if (req.url == "/cors" && req.method == "OPTIONS") { return (synth(752)); }
    if (req.url == "/compressible") { set req.url = "/size/65536"; }

    if (req.method != "GET" && req.method != "HEAD") { return (pass); }
    return (hash);                                          # the origin's Cache-Control decides what is cached
}

sub vcl_pipe {                                              # WebSocket: pass the upgrade through untouched
    if (req.http.upgrade) {
        set bereq.http.upgrade = req.http.upgrade;
        set bereq.http.connection = req.http.connection;
    }
}

sub vcl_backend_response {
    set beresp.grace = 300s;                                # serve stale while revalidating / on origin errors
    if (bereq.is_bgfetch && beresp.status >= 500) { return (abandon); }   # keep the stale copy, drop the failed refresh
    set beresp.do_stream = true;                            # stream as the origin sends (SSE, large bodies)
    if (beresp.http.Content-Type ~ "^(text/|application/json)" && beresp.http.Content-Type !~ "event-stream") { set beresp.do_gzip = true; }
    if (bereq.http.X-CB == "1" && beresp.status >= 500 && bereq.retries < 3) {
        saintmode.denylist(10s);                            # this (backend, object) pair is out for 10 s
        return (retry);
    }
    if (bereq.http.X-Custom-Error == "1" && beresp.status >= 500) { return (error(beresp.status)); }
    if (beresp.http.Cache-Control ~ "no-store") { set beresp.uncacheable = true; set beresp.ttl = 120s; }
}

sub vcl_backend_error {
    if (bereq.http.X-Retry == "1" && bereq.retries < 3) { return (retry); }    # connect failure -> next backend
    # production routes too: a stopped backend must cost a retry, not a 503 (idempotent methods only, never the timeout demo)
    if ((bereq.method == "GET" || bereq.method == "HEAD") && bereq.url !~ "^/delay/5000" && bereq.retries < 2) { return (retry); }
    if (bereq.http.X-Custom-Error == "1") {
        set beresp.http.Content-Type = "text/html; charset=utf-8";
        set beresp.http.X-Error-Page = "custom";
        set beresp.status = 503;
        synthetic(std.fileread("/static/error.html"));
        return (deliver);
    }
}

sub vcl_deliver {
    if (obj.hits > 0) { set resp.http.X-Cache = "HIT"; } else { set resp.http.X-Cache = "MISS"; }
    unset resp.http.X-Powered-By;
    unset resp.http.Via;
    set resp.http.Server = "varnish";
    if (req.http.X-Sticky-New == "1" && resp.http.X-Instance) {
        set resp.http.Set-Cookie = "lab_sticky=" + resp.http.X-Instance + "; Path=/; HttpOnly";
    }
    if (req.url == "/cors") { set resp.http.Access-Control-Allow-Origin = "*"; }
    if (req.url == "/secure") {
        set resp.http.Strict-Transport-Security = "max-age=31536000; includeSubDomains";
        set resp.http.X-Content-Type-Options = "nosniff";
        set resp.http.X-Frame-Options = "DENY";
        set resp.http.Referrer-Policy = "strict-origin-when-cross-origin";
    }
}

sub vcl_synth {
    set resp.http.Server = "varnish";
    if (resp.status == 750) { set resp.status = 301; set resp.http.Location = "https://" + req.http.X-Host + req.url; return (deliver); }
    if (resp.status == 751) { set resp.status = 301; set resp.http.Location = "/landing"; return (deliver); }
    if (resp.status == 752) {
        set resp.status = 204;
        set resp.http.Access-Control-Allow-Origin = req.http.Origin;
        set resp.http.Access-Control-Allow-Methods = "GET, POST, PUT, DELETE, OPTIONS";
        set resp.http.Access-Control-Allow-Headers = "Authorization, Content-Type";
        set resp.http.Access-Control-Max-Age = "600";
        return (deliver);
    }
    if (resp.status == 401) {
        if (req.url == "/basic") { set resp.http.WWW-Authenticate = {"Basic realm="pxlab""}; }
        else { set resp.http.WWW-Authenticate = {"Bearer realm="pxlab""}; }
    }
    set resp.http.Content-Type = "text/plain; charset=utf-8";
    synthetic(resp.status + " " + resp.reason + " (varnish)" + {"
"});
    return (deliver);
}
