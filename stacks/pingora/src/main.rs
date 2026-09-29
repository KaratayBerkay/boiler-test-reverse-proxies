//! pxlab reverse proxy built on Cloudflare's Pingora framework (the "build your own proxy" option of the lab).
//!
//! Everything the lab contract asks for is implemented in this one binary: host/path routing, several load-balancing
//! strategies (round-robin, weighted, consistent hashing, cookie stickiness), active health checks, retries and outlier
//! ejection, h2c/TLS upstreams, rate and concurrency limits, JWT / basic auth, IP lists, fault injection, timeouts,
//! response caching with PURGE, compression, mTLS, SNI certificate selection, a static file, a custom error page,
//! JSON access logs, Prometheus metrics and a tiny status API. Routing is code, not configuration - that is the point.
//!
//! Annotated walkthrough: docs/configs/pingora.md.
use std::collections::{BTreeSet, HashMap};
use std::net::IpAddr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use async_trait::async_trait;
use base64::Engine;
use bytes::Bytes;
use http::Method;
use jsonwebtoken::{Algorithm, DecodingKey, Validation};
use parking_lot::Mutex;
use pingora::apps::http_app::ServeHttp;
use pingora::apps::HttpServerOptions;
use pingora::cache::cache_control::CacheControl;
use pingora::cache::eviction::simple_lru::Manager as LruManager;
use pingora::cache::filters::resp_cacheable;
use pingora::cache::lock::CacheLock;
use pingora::cache::{CacheKey, CacheMetaDefaults, CachePhase, MemCache, NoCacheReason, RespCacheable};
use pingora::http::{RequestHeader, ResponseHeader};
use pingora::lb::health_check::HttpHealthCheck;
use pingora::lb::selection::{consistent::KetamaHashing, RoundRobin};
use pingora::lb::{Backend, Backends, LoadBalancer};
use pingora::listeners::tls::TlsSettings;
use pingora::listeners::TlsAccept;
use pingora::modules::http::compression::{ResponseCompression, ResponseCompressionBuilder};
use pingora::modules::http::HttpModules;
use pingora::prelude::*;
use pingora::protocols::http::ServerSession;
use pingora::protocols::ALPN;
use pingora::server::configuration::Opt;
use pingora::tls::pkey::PKey;
use pingora::tls::ssl::{NameType, SslRef, SslVerifyMode};
use pingora::tls::x509::X509;
use pingora::upstreams::peer::HttpPeer;
use pingora_limits::inflight::{Guard, Inflight};
use pingora_limits::rate::Rate;
use prometheus::{Encoder, HistogramVec, IntCounterVec, TextEncoder};
use serde::Deserialize;

// ---------------------------------------------------------------------------------------------------------- constants
const CERTS: &str = "/certs";
const AUTH_TOKEN_SECRET: &str = "pxlab-jwt-secret-please-change-0123456789";
const BASIC_CREDENTIALS: &str = "lab:lab-pass";
const CLIENT_HOST_IP: &str = "10.77.0.1";
const LAB_NET_PREFIX: &str = "10.77.0.";
const OUTLIER_FAILURES: u32 = 3;
const OUTLIER_EJECT_SECS: u64 = 10;

// ---------------------------------------------------------------------------------------------------------- shared state
static CACHE_STORAGE: LazyLock<MemCache> = LazyLock::new(MemCache::new);
static CACHE_EVICTION: LazyLock<LruManager> = LazyLock::new(|| LruManager::new(64 * 1024 * 1024));
static CACHE_LOCK: LazyLock<CacheLock> = LazyLock::new(|| CacheLock::new(Duration::from_secs(2)));
/// Status codes that are cacheable by default and their TTL when the origin sends no max-age (it always does here).
static CACHE_DEFAULTS: CacheMetaDefaults = CacheMetaDefaults::new(|_| Some(Duration::from_secs(60)), 30, 300);
static RATE: LazyLock<Rate> = LazyLock::new(|| Rate::new(Duration::from_secs(1)));
static INFLIGHT: LazyLock<Inflight> = LazyLock::new(Inflight::new);
static OUTLIERS: LazyLock<Mutex<HashMap<String, (u32, Option<Instant>)>>> = LazyLock::new(|| Mutex::new(HashMap::new()));
static STATIC_INDEX: LazyLock<String> =
    LazyLock::new(|| std::fs::read_to_string("/static/index.html").unwrap_or_else(|_| "pxlab static (file missing)\n".into()));
static ERROR_PAGE: LazyLock<String> = LazyLock::new(|| {
    std::fs::read_to_string("/static/error.html").unwrap_or_else(|_| "<h1>Custom error page</h1>".into())
});
static REQUESTS: LazyLock<IntCounterVec> = LazyLock::new(|| {
    prometheus::register_int_counter_vec!("pingora_http_requests_total", "Requests by host and status", &["host", "status"]).expect("metric")
});
static LATENCY: LazyLock<HistogramVec> = LazyLock::new(|| {
    prometheus::register_histogram_vec!("pingora_http_request_duration_seconds", "Request latency", &["host"]).expect("metric")
});
static CONNECTIONS_SEEN: AtomicU64 = AtomicU64::new(0);
static UPTIME: LazyLock<prometheus::IntGauge> =
    LazyLock::new(|| prometheus::register_int_gauge!("pingora_uptime_seconds", "Seconds since this process started").expect("metric"));
static REQUESTS_SEEN: LazyLock<prometheus::IntGauge> =
    LazyLock::new(|| prometheus::register_int_gauge!("pingora_requests_seen_total", "Requests routed since start").expect("metric"));
static STARTED: LazyLock<Instant> = LazyLock::new(Instant::now);

// ---------------------------------------------------------------------------------------------------------- pools
/// The load balancers the routes select from. Hostnames are resolved once at start-up (the lab's backends have static IPs).
struct Pools {
    app: Arc<LoadBalancer<RoundRobin>>,        // app1..3, active health checks every 2 s
    health: Arc<LoadBalancer<RoundRobin>>,     // same members, checks every second (health.lab)
    weighted: Arc<LoadBalancer<RoundRobin>>,   // app1 x3, app2 x1
    hash: Arc<LoadBalancer<KetamaHashing>>,    // consistent hashing on X-User
    retry: Arc<LoadBalancer<RoundRobin>>,      // includes a dead member
    cb: Arc<LoadBalancer<RoundRobin>>,         // app1, app2, flaky - outlier ejection in code
    canary: Arc<LoadBalancer<RoundRobin>>,     // app1..3 x30, canary x10
}

/// `Backend::new` wants an IP:port; the lab's members are docker names, resolved once here (their IPs are static).
fn resolve(addr: &str) -> String {
    use std::net::ToSocketAddrs;
    addr.to_socket_addrs()
        .ok()
        .and_then(|mut it| it.find(|a| a.is_ipv4()))
        .map(|a| a.to_string())
        .unwrap_or_else(|| panic!("cannot resolve {addr}"))
}

fn backends(members: &[(&str, usize)]) -> Backends {
    let set: BTreeSet<Backend> = members
        .iter()
        .map(|(addr, w)| Backend::new_with_weight(&resolve(addr), *w).unwrap_or_else(|e| panic!("bad backend {addr}: {e}")))
        .collect();
    Backends::new(pingora::lb::discovery::Static::new(set))
}

fn health_check(interval_secs: u64) -> Box<HttpHealthCheck> {
    let mut hc = HttpHealthCheck::new("app.lab", false);
    hc.req.set_uri("/healthz".parse().expect("uri")); // keep the Host header HttpHealthCheck::new added
    hc.consecutive_success = 2;
    hc.consecutive_failure = 2;
    hc.peer_template.options.connection_timeout = Some(Duration::from_secs(1));
    hc.peer_template.options.read_timeout = Some(Duration::from_secs(1));
    let _ = interval_secs; // the frequency lives on the LoadBalancer
    Box::new(hc)
}

fn lb_rr(members: &[(&str, usize)], hc_secs: Option<u64>) -> LoadBalancer<RoundRobin> {
    let mut lb = LoadBalancer::<RoundRobin>::from_backends(backends(members));
    if let Some(s) = hc_secs {
        lb.set_health_check(health_check(s));
        lb.health_check_frequency = Some(Duration::from_secs(s));
        lb.parallel_health_check = true;
    }
    lb
}

// ---------------------------------------------------------------------------------------------------------- routing
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Pool {
    App,
    Health,
    Weighted,
    Hash,
    Retry,
    Cb,
    Canary,
    Single(&'static str), // fixed address (b1, canary, dead-member-free pools)
    H2c(&'static str),    // HTTP/2 prior knowledge to the upstream
    Tls(&'static str),    // TLS re-encryption, verified against the lab CA
    Grpc,
}

struct Ctx {
    pool: Pool,
    tries: u32,
    upstream: String,
    start: Instant,
    host: String,
    inflight_guard: Option<Guard>,
    read_timeout: Option<Duration>,
    replace_error_body: bool,
    body_replaced: bool,
    sticky_new: bool,
    hash_key: String,
}

struct LabProxy {
    pools: Pools,
}

fn header_str<'h>(req: &'h RequestHeader, name: &str) -> Option<&'h str> {
    req.headers.get(name).and_then(|v| v.to_str().ok())
}

fn client_ip(session: &Session) -> IpAddr {
    session
        .client_addr()
        .and_then(|a| a.as_inet())
        .map(|a| a.ip())
        .unwrap_or(IpAddr::from([0, 0, 0, 0]))
}

fn now_secs() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

#[derive(Deserialize)]
struct Claims {
    sub: Option<String>,
    exp: Option<u64>,
    #[allow(dead_code)]
    iss: Option<String>,
}

/// Verifies `Authorization: Bearer <HS256 JWT>`; returns the subject when valid.
fn verify_jwt(authorization: Option<&str>) -> std::result::Result<String, &'static str> {
    let auth = authorization.ok_or("missing bearer token")?;
    let token = auth.strip_prefix("Bearer ").ok_or("missing bearer token")?;
    let mut validation = Validation::new(Algorithm::HS256);
    validation.set_audience(&["pxlab"]);
    validation.set_issuer(&["pxlab"]);
    let data = jsonwebtoken::decode::<Claims>(token, &DecodingKey::from_secret(AUTH_TOKEN_SECRET.as_bytes()), &validation)
        .map_err(|_| "invalid token")?;
    if data.claims.exp.is_some_and(|exp| exp < now_secs()) {
        return Err("expired");
    }
    Ok(data.claims.sub.unwrap_or_default())
}

fn outlier_marked(addr: &str) -> bool {
    let mut map = OUTLIERS.lock();
    match map.get(addr) {
        Some((_, Some(until))) if Instant::now() < *until => true,
        Some((_, Some(_))) => {
            map.remove(addr); // ejection expired: give it another chance
            false
        }
        _ => false,
    }
}

fn outlier_observe(addr: &str, failed: bool) {
    let mut map = OUTLIERS.lock();
    let entry = map.entry(addr.to_string()).or_insert((0, None));
    if failed {
        entry.0 += 1;
        if entry.0 >= OUTLIER_FAILURES {
            entry.1 = Some(Instant::now() + Duration::from_secs(OUTLIER_EJECT_SECS));
            entry.0 = 0;
        }
    } else {
        entry.0 = 0;
    }
}

impl LabProxy {
    async fn reply(session: &mut Session, status: u16, body: &str, headers: &[(&str, &str)]) -> Result<bool> {
        let mut resp = ResponseHeader::build(status, Some(4))?;
        resp.insert_header("Content-Type", "text/plain; charset=utf-8")?;
        resp.insert_header("Content-Length", body.len().to_string())?;
        for (k, v) in headers {
            resp.insert_header(k.to_string(), v.to_string())?;
        }
        session.write_response_header(Box::new(resp), false).await?;
        session.write_response_body(Some(Bytes::copy_from_slice(body.as_bytes())), true).await?;
        Ok(true)
    }

    fn select(&self, ctx: &mut Ctx) -> Option<String> {
        let lb_rr = |lb: &LoadBalancer<RoundRobin>| lb.select(b"", 256).map(|b| b.addr.to_string());
        match ctx.pool {
            Pool::App => lb_rr(&self.pools.app),
            Pool::Health => lb_rr(&self.pools.health),
            Pool::Weighted => lb_rr(&self.pools.weighted),
            Pool::Retry => lb_rr(&self.pools.retry),
            Pool::Canary => lb_rr(&self.pools.canary),
            Pool::Cb => self
                .pools
                .cb
                .select_with(b"", 16, |b, healthy| healthy && !outlier_marked(&b.addr.to_string()))
                .map(|b| b.addr.to_string()),
            Pool::Hash => self.pools.hash.select(ctx.hash_key.as_bytes(), 256).map(|b| b.addr.to_string()),
            Pool::Single(a) | Pool::H2c(a) | Pool::Tls(a) => Some(a.to_string()),
            Pool::Grpc => Some("app1:9090".to_string()),
        }
    }
}

#[async_trait]
impl ProxyHttp for LabProxy {
    type CTX = Ctx;

    fn new_ctx(&self) -> Ctx {
        Ctx {
            pool: Pool::App,
            tries: 0,
            upstream: String::new(),
            start: Instant::now(),
            host: String::new(),
            inflight_guard: None,
            read_timeout: None,
            replace_error_body: false,
            body_replaced: false,
            sticky_new: false,
            hash_key: String::new(),
        }
    }

    fn init_downstream_modules(&self, modules: &mut HttpModules) {
        modules.add_module(ResponseCompressionBuilder::enable(0)); // armed per request below, gated per response in response_filter()
    }

    async fn early_request_filter(&self, session: &mut Session, _ctx: &mut Ctx) -> Result<()> {
        // the module parses Accept-Encoding at request time only when a level > 0 is set here; the final decision
        // (text-like content type or not) is made in response_filter() once the upstream headers are known
        let streaming = session.req_header().uri.path() == "/sse";
        if let Some(c) = session.downstream_modules_ctx.get_mut::<ResponseCompression>() {
            c.adjust_level(if streaming { 0 } else { 5 });
        }
        Ok(())
    }

    /// Routing + everything that answers without an upstream (limits, auth, redirects, static content).
    async fn request_filter(&self, session: &mut Session, ctx: &mut Ctx) -> Result<bool> {
        // copy what the routing needs out of the request header first: mutating the session below ends the borrow
        let (host, path, query, method, path_and_query, x_canary, cookie, x_user, authorization, content_length, origin) = {
            let req = session.req_header();
            (
                header_str(req, "host").unwrap_or("").split(':').next().unwrap_or("").to_ascii_lowercase(),
                req.uri.path().to_string(),
                req.uri.query().unwrap_or("").to_string(),
                req.method.clone(),
                req.uri.path_and_query().map(|p| p.as_str().to_string()).unwrap_or_else(|| "/".into()),
                header_str(req, "x-canary").map(str::to_string),
                header_str(req, "cookie").unwrap_or("").to_string(),
                header_str(req, "x-user").map(str::to_string),
                header_str(req, "authorization").map(str::to_string),
                header_str(req, "content-length").and_then(|v| v.parse::<u64>().ok()).unwrap_or(0),
                header_str(req, "origin").unwrap_or("*").to_string(),
            )
        };
        let ip = client_ip(session);
        ctx.host = host.clone();
        CONNECTIONS_SEEN.fetch_add(1, Ordering::Relaxed);

        // --- host routing --------------------------------------------------------------------------------------
        match host.as_str() {
            "redirect.lab" => {
                let loc = format!("https://{host}{path_and_query}");
                return Self::reply(session, 301, "", &[("Location", &loc)]).await;
            }
            "b.lab" => ctx.pool = Pool::Single("b1:8080"),
            "weighted.lab" => ctx.pool = Pool::Weighted,
            "hash.lab" => {
                ctx.pool = Pool::Hash;
                ctx.hash_key = x_user.clone().unwrap_or_else(|| ip.to_string());
            }
            "sticky.lab" => {
                let stuck = cookie.split(';').map(str::trim).find_map(|c| c.strip_prefix("lab_sticky="));
                match stuck {
                    Some("app1") => ctx.pool = Pool::Single("app1:8080"),
                    Some("app2") => ctx.pool = Pool::Single("app2:8080"),
                    Some("app3") => ctx.pool = Pool::Single("app3:8080"),
                    _ => {
                        ctx.pool = Pool::App;
                        ctx.sticky_new = true;
                    }
                }
            }
            "retry.lab" => ctx.pool = Pool::Retry,
            "cb.lab" => ctx.pool = Pool::Cb,
            "health.lab" => ctx.pool = Pool::Health,
            "canary.lab" => ctx.pool = Pool::Canary,
            "h2.lab" => ctx.pool = Pool::H2c("app1:8080"),
            "tls.lab" => ctx.pool = Pool::Tls("app1:8443"),
            "jwt.lab" => {
                let verdict = verify_jwt(authorization.as_deref());
                match verdict {
                    Ok(sub) => session.req_header_mut().insert_header("X-JWT-Sub", sub)?,
                    Err(why) => return Self::reply(session, 401, why, &[("WWW-Authenticate", "Bearer realm=\"pxlab\"")]).await,
                }
            }
            _ => ctx.pool = Pool::App, // app.lab, a.lab, mirror/pp/auth/acme/mtls.lab, localhost, proxy ...
        }

        // --- path features (default vhost) ---------------------------------------------------------------------
        if path.starts_with("/api/") && method == Method::DELETE {
            return Self::reply(session, 405, "method not allowed\n", &[]).await;
        }
        if x_canary.as_deref() == Some("1") || query.split('&').any(|kv| kv == "beta=1") {
            ctx.pool = Pool::Single("canary:8080");
        }
        if path.starts_with("/grpc.health.v1.Health/") {
            ctx.pool = Pool::Grpc;
        }
        match path.as_str() {
            "/redirect-me" => return Self::reply(session, 301, "", &[("Location", "/landing")]).await,
            "/limited" => {
                if RATE.observe(&ip, 1) > 10 {
                    return Self::reply(session, 429, "rate limited\n", &[("Retry-After", "1")]).await;
                }
            }
            "/conn-limited" => {
                let (guard, n) = INFLIGHT.incr(ip, 1);
                if n > 3 {
                    return Self::reply(session, 429, "too many concurrent requests\n", &[]).await;
                }
                ctx.inflight_guard = Some(guard);
            }
            "/allowed" if ip.to_string() != CLIENT_HOST_IP => return Self::reply(session, 403, "forbidden\n", &[]).await,
            "/denied" if ip.to_string().starts_with(LAB_NET_PREFIX) => return Self::reply(session, 403, "forbidden\n", &[]).await,
            "/basic" => {
                let expected = format!("Basic {}", base64::engine::general_purpose::STANDARD.encode(BASIC_CREDENTIALS));
                if authorization.as_deref() != Some(expected.as_str()) {
                    return Self::reply(session, 401, "unauthorized\n", &[("WWW-Authenticate", "Basic realm=\"pxlab\"")]).await;
                }
            }
            "/upload" => {
                if content_length > 1_048_576 {
                    return Self::reply(session, 413, "body too large\n", &[]).await;
                }
            }
            "/fault" if rand::random::<f64>() < 0.2 => return Self::reply(session, 503, "injected fault\n", &[]).await,
            "/static/index.html" => {
                let body = STATIC_INDEX.clone();
                return Self::reply(session, 200, &body, &[("Content-Type", "text/html; charset=utf-8")]).await;
            }
            "/cors" if method == Method::OPTIONS => {
                return Self::reply(
                    session,
                    204,
                    "",
                    &[
                        ("Access-Control-Allow-Origin", &origin),
                        ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"),
                        ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
                        ("Access-Control-Max-Age", "600"),
                    ],
                )
                .await;
            }
            _ => {}
        }

        // --- rewrites: what the upstream sees ------------------------------------------------------------------
        let (new_path, route): (Option<String>, Option<&str>) = if let Some(rest) = path.strip_prefix("/api/") {
            (Some(format!("/{rest}")), Some("api"))
        } else if path.starts_with("/v") && path[2..].split('/').next().is_some_and(|v| !v.is_empty() && v.bytes().all(|b| b.is_ascii_digit())) && path[2..].contains('/') {
            (None, Some("versioned"))
        } else if let Some(rest) = path.strip_prefix("/old/") {
            (Some(format!("/new/{rest}")), Some("rewritten"))
        } else {
            match path.as_str() {
                "/conn-limited" => (Some("/delay/1000".into()), None),
                "/timeout" => {
                    ctx.read_timeout = Some(Duration::from_secs(2));
                    (Some("/delay/5000".into()), None)
                }
                "/bw" => (Some("/bin/1048576".into()), None),
                "/error-page" => {
                    ctx.replace_error_body = true;
                    (Some("/status/503".into()), None)
                }
                "/compressible" => (Some("/size/65536".into()), None),
                _ => (None, None),
            }
        };
        if let Some(p) = new_path {
            let uri = if query.is_empty() { p } else { format!("{p}?{query}") };
            session.req_header_mut().set_uri(uri.parse().map_err(|_| Error::new(ErrorType::InvalidHTTPHeader))?);
        }
        if let Some(r) = route {
            session.req_header_mut().insert_header("X-Route", r)?;
        }
        if host == "a.lab" {
            session.req_header_mut().insert_header("X-Route", "a")?;
        }
        if host == "b.lab" {
            session.req_header_mut().insert_header("X-Route", "b")?;
        }
        Ok(false)
    }

    // --- cache: only /cacheable*, key = host + path, PURGE handled by pingora-proxy when the cache is enabled -------
    fn request_cache_filter(&self, session: &mut Session, _ctx: &mut Ctx) -> Result<()> {
        if session.req_header().uri.path().starts_with("/cacheable") {
            session.cache.enable(&*CACHE_STORAGE, Some(&*CACHE_EVICTION), None, Some(&*CACHE_LOCK), None);
        }
        Ok(())
    }

    fn cache_key_callback(&self, session: &Session, ctx: &mut Ctx) -> Result<CacheKey> {
        Ok(CacheKey::new(format!("{}{}", ctx.host, session.req_header().uri.path()), "lab"))
    }

    fn response_cache_filter(&self, _session: &Session, resp: &ResponseHeader, _ctx: &mut Ctx) -> Result<RespCacheable> {
        let cc = CacheControl::from_resp_headers(resp);
        if cc.as_ref().is_some_and(|c| c.no_store()) {
            return Ok(RespCacheable::Uncacheable(NoCacheReason::OriginNotCache));
        }
        Ok(resp_cacheable(cc.as_ref(), resp.clone(), false, &CACHE_DEFAULTS))
    }

    fn should_serve_stale(&self, _session: &mut Session, _ctx: &mut Ctx, error: Option<&Error>) -> bool {
        error.is_some() // stale-if-error: serve the expired copy when the refresh fails
    }

    // --- upstream selection ----------------------------------------------------------------------------------------
    async fn upstream_peer(&self, _session: &mut Session, ctx: &mut Ctx) -> Result<Box<HttpPeer>> {
        ctx.tries += 1;
        let addr = self.select(ctx).ok_or_else(|| Error::new_str("no healthy upstream"))?;
        let addr = if addr.starts_with(|c: char| c.is_ascii_digit()) { addr } else { resolve(&addr) };
        ctx.upstream = addr.clone();
        let mut peer = match ctx.pool {
            Pool::Tls(_) => {
                let mut p = HttpPeer::new(addr.as_str(), true, "backend.lab".to_string());
                p.options.verify_cert = true;
                p.options.verify_hostname = true;
                p.options.ca = Some(Arc::new(load_ca()));
                p.options.alpn = ALPN::H1;
                p
            }
            Pool::H2c(_) | Pool::Grpc => {
                let mut p = HttpPeer::new(addr.as_str(), false, String::new());
                p.options.alpn = ALPN::H2; // prior-knowledge HTTP/2 on a plaintext connection (h2c)
                p
            }
            _ => HttpPeer::new(addr.as_str(), false, String::new()),
        };
        peer.options.connection_timeout = Some(Duration::from_secs(3));
        peer.options.read_timeout = ctx.read_timeout.or(Some(Duration::from_secs(30)));
        peer.options.idle_timeout = Some(Duration::from_secs(90));
        Ok(Box::new(peer))
    }

    fn fail_to_connect(&self, _session: &mut Session, _peer: &HttpPeer, ctx: &mut Ctx, mut e: Box<Error>) -> Box<Error> {
        if matches!(ctx.pool, Pool::App | Pool::Retry | Pool::Cb | Pool::Health | Pool::Canary) && ctx.tries < 3 {
            e.set_retry(true); // upstream_peer() runs again and round-robin moves on to the next member
        }
        e
    }

    // --- headers towards the upstream -----------------------------------------------------------------------------
    async fn upstream_request_filter(&self, session: &mut Session, upstream: &mut RequestHeader, ctx: &mut Ctx) -> Result<()> {
        let ip = client_ip(session).to_string();
        let scheme = if session.digest().and_then(|d| d.ssl_digest.as_ref()).is_some() { "https" } else { "http" };
        upstream.insert_header("X-Lab-Proxy", "pingora")?;
        upstream.insert_header("X-Real-IP", ip.as_str())?;
        upstream.insert_header("X-Forwarded-Proto", scheme)?;
        upstream.insert_header("X-Forwarded-Host", ctx.host.as_str())?;
        upstream.insert_header("Forwarded", format!("for={ip};proto={scheme};host={}", ctx.host))?;
        let xff = match header_str(session.req_header(), "x-forwarded-for") {
            Some(prev) => format!("{prev}, {ip}"),
            None => ip.clone(),
        };
        upstream.insert_header("X-Forwarded-For", xff)?;
        if header_str(session.req_header(), "x-request-id").is_none() {
            upstream.insert_header("X-Request-ID", uuid::Uuid::new_v4().to_string())?;
        }
        if ctx.pool == Pool::Grpc {
            upstream.insert_header("TE", "trailers")?;
        }
        if let Some(d) = session.digest().and_then(|d| d.ssl_digest.as_ref()) {
            if let Some(org) = &d.organization {
                upstream.insert_header("X-Client-Cert-Org", org.as_str())?; // the CN itself is not exposed by SslDigest
            }
        }
        Ok(())
    }

    // --- response path ----------------------------------------------------------------------------------------------
    async fn upstream_response_filter(&self, _session: &mut Session, upstream_response: &mut ResponseHeader, ctx: &mut Ctx) -> Result<()> {
        if ctx.pool == Pool::Cb {
            outlier_observe(&ctx.upstream, upstream_response.status.is_server_error());
        }
        Ok(())
    }

    async fn response_filter(&self, session: &mut Session, resp: &mut ResponseHeader, ctx: &mut Ctx) -> Result<()> {
        resp.remove_header("x-powered-by");
        resp.insert_header("Server", "pingora")?;
        // gzip / zstd chosen from Accept-Encoding by the compression module - but only for text-like bodies: the module's
        // own filter accepts any `application/*` type, so without this a 1 MiB random `/bin/` body was gzipped at level 5
        // (140 rps at 4 cores). Never for the event stream: compression would buffer it.
        let ctype = resp.headers.get("content-type").and_then(|v| v.to_str().ok()).unwrap_or("");
        let compressible = (ctype.starts_with("text/") || ctype.starts_with("application/json") || ctype.starts_with("application/javascript"))
            && !ctype.contains("event-stream");
        if let Some(c) = session.downstream_modules_ctx.get_mut::<ResponseCompression>() {
            c.adjust_level(if compressible { 5 } else { 0 });
        }
        if session.cache.enabled() {
            let status = match session.cache.phase() {
                CachePhase::Hit => "HIT",
                CachePhase::Stale | CachePhase::StaleUpdating => "STALE",
                CachePhase::Miss | CachePhase::Expired => "MISS",
                _ => "BYPASS",
            };
            resp.insert_header("X-Cache", status)?;
        }
        if ctx.sticky_new {
            if let Some(inst) = resp.headers.get("x-instance").and_then(|v| v.to_str().ok()) {
                resp.insert_header("Set-Cookie", format!("lab_sticky={inst}; Path=/; HttpOnly"))?;
            }
        }
        let path = session.req_header().uri.path();
        match path {
            "/cors" => resp.insert_header("Access-Control-Allow-Origin", "*")?,
            "/secure" => {
                resp.insert_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")?;
                resp.insert_header("X-Content-Type-Options", "nosniff")?;
                resp.insert_header("X-Frame-Options", "DENY")?;
                resp.insert_header("Referrer-Policy", "strict-origin-when-cross-origin")?;
            }
            _ => {}
        }
        if ctx.replace_error_body && resp.status.is_server_error() {
            resp.insert_header("X-Error-Page", "custom")?;
            resp.insert_header("Content-Type", "text/html; charset=utf-8")?;
            resp.remove_header("content-length"); // the body is replaced chunk by chunk below
            resp.remove_header("content-encoding");
        } else {
            ctx.replace_error_body = false;
        }
        Ok(())
    }

    fn response_body_filter(&self, _session: &mut Session, body: &mut Option<Bytes>, end_of_stream: bool, ctx: &mut Ctx) -> Result<Option<Duration>> {
        if ctx.replace_error_body {
            if !ctx.body_replaced {
                *body = Some(Bytes::from(ERROR_PAGE.clone()));
                ctx.body_replaced = true;
            } else if body.is_some() {
                *body = Some(Bytes::new());
            }
            let _ = end_of_stream;
        }
        Ok(None)
    }

    // --- JSON access log + metrics ---------------------------------------------------------------------------------
    async fn logging(&self, session: &mut Session, e: Option<&Error>, ctx: &mut Ctx) {
        let status = session.response_written().map(|r| r.status.as_u16()).unwrap_or(0);
        let ms = ctx.start.elapsed().as_secs_f64() * 1000.0;
        REQUESTS.with_label_values(&[ctx.host.as_str(), &status.to_string()]).inc();
        LATENCY.with_label_values(&[ctx.host.as_str()]).observe(ms / 1000.0);
        let req = session.req_header();
        let line = serde_json::json!({
            "time": now_secs(),
            "remote_addr": client_ip(session).to_string(),
            "method": req.method.as_str(),
            "uri": req.uri.to_string(),
            "host": ctx.host,
            "status": status,
            "duration_ms": (ms * 1000.0).round() / 1000.0,
            "upstream": ctx.upstream,
            "tries": ctx.tries,
            "cache": if session.cache.enabled() { format!("{:?}", session.cache.phase()) } else { String::new() },
            "error": e.map(|e| e.to_string()),
        });
        println!("{line}");
    }
}

fn load_ca() -> Box<[X509]> {
    let pem = std::fs::read(format!("{CERTS}/ca.crt")).expect("lab CA");
    X509::stack_from_pem(&pem).expect("parse CA").into_boxed_slice()
}

// ---------------------------------------------------------------------------------------------------------- TLS: SNI certificate selection
struct SniCerts {
    default: (X509, PKey<pingora::tls::pkey::Private>),
    b_lab: (X509, PKey<pingora::tls::pkey::Private>),
}

fn load_cert(name: &str) -> (X509, PKey<pingora::tls::pkey::Private>) {
    let cert = X509::from_pem(&std::fs::read(format!("{CERTS}/{name}.crt")).expect("cert")).expect("parse cert");
    let key = PKey::private_key_from_pem(&std::fs::read(format!("{CERTS}/{name}.key")).expect("key")).expect("parse key");
    (cert, key)
}

#[async_trait]
impl TlsAccept for SniCerts {
    async fn certificate_callback(&self, ssl: &mut SslRef) {
        let sni = ssl.servername(NameType::HOST_NAME).unwrap_or("");
        let (cert, key) = if sni == "b.lab" { &self.b_lab } else { &self.default };
        pingora::tls::ext::ssl_use_certificate(ssl, cert).expect("use cert");
        pingora::tls::ext::ssl_use_private_key(ssl, key).expect("use key");
    }
}

// ---------------------------------------------------------------------------------------------------------- metrics / status apps
struct MetricsApp;

#[async_trait]
impl ServeHttp for MetricsApp {
    async fn response(&self, session: &mut ServerSession) -> http::Response<Vec<u8>> {
        let path = session.req_header().uri.path().to_string();
        if path == "/healthz" {
            return http::Response::builder().status(200).header("Content-Type", "text/plain").body(b"ok\n".to_vec()).expect("resp");
        }
        UPTIME.set(STARTED.elapsed().as_secs() as i64);
        REQUESTS_SEEN.set(CONNECTIONS_SEEN.load(Ordering::Relaxed) as i64);
        let mut buf = Vec::new();
        TextEncoder::new().encode(&prometheus::gather(), &mut buf).expect("encode metrics");
        http::Response::builder().status(200).header("Content-Type", "text/plain; version=0.0.4").body(buf).expect("resp")
    }
}

struct StatusApp {
    started: Instant,
}

#[async_trait]
impl ServeHttp for StatusApp {
    async fn response(&self, _session: &mut ServerSession) -> http::Response<Vec<u8>> {
        let body = serde_json::json!({
            "proxy": "pingora-lab",
            "version": env!("CARGO_PKG_VERSION"),
            "uptime_s": self.started.elapsed().as_secs(),
            "requests_seen": CONNECTIONS_SEEN.load(Ordering::Relaxed),
            "outliers": OUTLIERS.lock().iter().filter(|(_, (_, until))| until.is_some_and(|u| Instant::now() < u)).map(|(k, _)| k.clone()).collect::<Vec<_>>(),
        });
        http::Response::builder().status(200).header("Content-Type", "application/json").body(body.to_string().into_bytes()).expect("resp")
    }
}

// ---------------------------------------------------------------------------------------------------------- L4 TCP proxy app
struct TcpProxyApp {
    target: &'static str,
}

#[async_trait]
impl pingora::apps::ServerApp for TcpProxyApp {
    async fn process_new(
        self: &Arc<Self>,
        mut io: pingora::protocols::Stream,
        _shutdown: &pingora::server::ShutdownWatch,
    ) -> Option<pingora::protocols::Stream> {
        match tokio::net::TcpStream::connect(self.target).await {
            Ok(mut upstream) => {
                let _ = tokio::io::copy_bidirectional(&mut *io, &mut upstream).await;
            }
            Err(e) => log::warn!("tcp proxy: cannot connect to {}: {e}", self.target),
        }
        None
    }
}

// ---------------------------------------------------------------------------------------------------------- main
fn main() {
    env_logger::init();
    let opt = Opt::parse_args();
    let mut server = Server::new(Some(opt)).expect("server");
    server.bootstrap();
    // register every metric family at start-up (label vecs stay empty until traffic, so a freshly upgraded process
    // would otherwise expose nothing on /metrics); the process collector adds cpu/rss/fds
    LazyLock::force(&STARTED);
    LazyLock::force(&REQUESTS);
    LazyLock::force(&LATENCY);
    LazyLock::force(&UPTIME);
    LazyLock::force(&REQUESTS_SEEN);
    let _ = prometheus::register(Box::new(prometheus::process_collector::ProcessCollector::for_self()));

    // pools + health checks (each LoadBalancer with a health check runs as a background service)
    let app = background_service("app health", lb_rr(&[("app1:8080", 1), ("app2:8080", 1), ("app3:8080", 1)], Some(2)));
    let health = background_service("health.lab checks", lb_rr(&[("app1:8080", 1), ("app2:8080", 1), ("app3:8080", 1)], Some(1)));
    let cb = background_service("cb.lab checks", lb_rr(&[("app1:8080", 1), ("app2:8080", 1), ("flaky:8080", 1)], Some(5)));
    // pools without health checks still need one discovery update to populate their backends: run them as
    // background services too (update once at start, no periodic checks)
    let weighted = background_service("weighted", lb_rr(&[("app1:8080", 3), ("app2:8080", 1)], None));
    let hash = background_service("hash", LoadBalancer::<KetamaHashing>::from_backends(backends(&[("app1:8080", 1), ("app2:8080", 1), ("app3:8080", 1)])));
    let retry = background_service("retry", lb_rr(&[("app1:8080", 1), ("app2:8080", 1), ("app3:8099", 1)], None));
    let canary = background_service("canary", lb_rr(&[("app1:8080", 30), ("app2:8080", 30), ("app3:8080", 30), ("canary:8080", 10)], None));
    let pools = Pools {
        app: app.task(),
        health: health.task(),
        cb: cb.task(),
        weighted: weighted.task(),
        hash: hash.task(),
        retry: retry.task(),
        canary: canary.task(),
    };
    for svc in [app, health, cb, weighted, retry, canary] {
        server.add_service(svc);
    }
    server.add_service(hash);

    let mut proxy = http_proxy_service(&server.configuration, LabProxy { pools });
    proxy.add_tcp("0.0.0.0:8080");
    proxy.add_tcp("0.0.0.0:80");
    if let Some(app_logic) = proxy.app_logic_mut() {
        let mut opts = HttpServerOptions::default();
        opts.h2c = true;
        app_logic.server_options = Some(opts);
    }
    // HTTPS: certificate picked by SNI (app.lab default, b.lab its own), h2 via ALPN
    let mut tls = TlsSettings::with_callbacks(Box::new(SniCerts { default: load_cert("app.lab"), b_lab: load_cert("b.lab") })).expect("tls");
    tls.enable_h2();
    proxy.add_tls_with_settings("0.0.0.0:8443", None, tls);
    // mTLS: client certificate required, verified against the lab CA
    let mut mtls = TlsSettings::intermediate(&format!("{CERTS}/app.lab.fullchain.crt"), &format!("{CERTS}/app.lab.key")).expect("mtls");
    mtls.enable_h2();
    mtls.set_ca_file(format!("{CERTS}/ca.crt")).expect("ca");
    mtls.set_verify(SslVerifyMode::PEER | SslVerifyMode::FAIL_IF_NO_PEER_CERT);
    proxy.add_tls_with_settings("0.0.0.0:8444", None, mtls);
    server.add_service(proxy);

    let mut metrics = pingora::services::listening::Service::new("metrics".into(), MetricsApp);
    metrics.add_tcp("0.0.0.0:9100");
    server.add_service(metrics);
    let mut status = pingora::services::listening::Service::new("status".into(), StatusApp { started: Instant::now() });
    status.add_tcp("0.0.0.0:9101");
    server.add_service(status);
    let mut tcp = pingora::services::listening::Service::new("tcp-proxy".into(), TcpProxyApp { target: "10.77.0.11:8080" });
    tcp.add_tcp("0.0.0.0:9000");
    server.add_service(tcp);

    server.run_forever();
}
