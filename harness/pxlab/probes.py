"""Capability probes: one function per capability, all written against the contract (contract.py), so the same
code verifies every proxy. Each returns {"ok": bool, "detail": str, ...extras}; exceptions become status "error";
capabilities a stack declares in lab.yaml `unsupported:` are reported as "unsupported" with the reason.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import http.client
import json
import socket
import ssl
import subprocess
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from . import dockerctl, netfix
from .config import StackConfig
from .contract import AUTH_TOKEN, BACKENDS, BASIC_PASS, BASIC_USER, CLIENT_IP, JWT_SECRET, POOL_APP, PORTS
from .util import SHARED, short_err

netfix.install()
CA = str(SHARED / "certs" / "ca.crt")
CLIENT_CERT = (str(SHARED / "certs" / "client.crt"), str(SHARED / "certs" / "client.key"))


@dataclass
class Probe:
    id: str
    group: str
    title: str
    fn: Callable[["Ctx"], dict[str, Any]]
    proves: str = ""


PROBES: list[Probe] = []


def probe(id: str, group: str, title: str, proves: str = ""):  # noqa: A002
    def deco(fn):
        PROBES.append(Probe(id, group, title, fn, proves))
        return fn
    return deco


# ---------------------------------------------------------------------------------------------- context / helpers
@dataclass
class Ctx:
    cfg: StackConfig
    log: Callable[[str], None] = print
    run_tag: str = field(default_factory=lambda: hex(int(time.time()))[-6:])
    _h1: httpx.Client | None = None
    _h2: httpx.Client | None = None

    @property
    def h1(self) -> httpx.Client:
        if self._h1 is None:
            self._h1 = httpx.Client(verify=CA, timeout=10, follow_redirects=False)
        return self._h1

    @property
    def h2(self) -> httpx.Client:
        if self._h2 is None:
            self._h2 = httpx.Client(verify=CA, timeout=10, follow_redirects=False, http2=True)
        return self._h2

    def close(self) -> None:
        for c in (self._h1, self._h2):
            if c:
                c.close()

    def url(self, host: str, path: str = "/", port: str = "http") -> str:
        scheme = "http" if port in ("http", "pp", "tcp", "metrics", "admin") else "https"
        return f"{scheme}://{host}:{PORTS[port][1]}{path}"

    def get(self, host: str, path: str = "/", port: str = "http", **kw) -> httpx.Response:
        return self.h1.get(self.url(host, path, port), **kw)

    def echo(self, host: str, path: str = "/", port: str = "http", **kw) -> dict[str, Any]:
        r = self.get(host, path, port, **kw)
        if r.status_code != 200:
            raise RuntimeError(f"GET {host}{path} -> {r.status_code}: {r.text[:120]!r}")
        return r.json()

    def instances(self, host: str, path: str = "/", n: int = 30, **kw) -> Counter:
        c: Counter = Counter()
        for _ in range(n):
            r = self.get(host, path, **kw)
            c[r.headers.get("x-instance", f"status:{r.status_code}")] += 1
        return c

    def concurrent(self, host: str, path: str, n: int, conc: int, **kw) -> list[httpx.Response]:
        client = httpx.Client(verify=CA, timeout=20, follow_redirects=False, limits=httpx.Limits(max_connections=conc, max_keepalive_connections=conc))
        try:
            with ThreadPoolExecutor(max_workers=conc) as ex:
                return list(ex.map(lambda _: client.get(self.url(host, path), **kw), range(n)))
        finally:
            client.close()

    def backend(self, instance: str, path: str) -> Any:
        ip, port = BACKENDS[instance]
        r = httpx.get(f"http://127.0.0.1:{port}{path}", timeout=5)
        try:
            return r.json()
        except Exception:  # noqa: BLE001
            return r.text

    def reset_backends(self) -> None:
        for inst in BACKENDS:
            self.backend(inst, "/admin/health?state=up")
            self.backend(inst, "/admin/fail?rate=0")
            self.backend(inst, f"/admin/delay?ms={100 if inst == 'slow' else 0}")
            self.backend(inst, "/admin/reset")

    def tool(self, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
        return dockerctl.run_tool(args, name=f"pxlab-probe-{self.cfg.key}", timeout=timeout)

    def wait_ready(self, timeout: float = 60) -> float:
        t0 = time.time()
        last = ""
        while time.time() - t0 < timeout:
            try:
                r = self.get("app.lab", "/")
                if r.status_code == 200 and r.headers.get("x-instance"):
                    return round(time.time() - t0, 1)
                last = f"status {r.status_code}"
            except Exception as e:  # noqa: BLE001
                last = short_err(e, 80)
            time.sleep(0.5)
        raise RuntimeError(f"proxy not ready after {timeout}s: {last}")


def tls_connect(port: int, sni: str, *, verify: bool = True, min_ver=None, max_ver=None, client_cert: bool = False, seclevel0: bool = False):
    ctx = ssl.create_default_context(cafile=CA) if verify else ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    if min_ver:
        ctx.minimum_version = min_ver
    if max_ver:
        ctx.maximum_version = max_ver
    if seclevel0:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    if client_cert:
        ctx.load_cert_chain(*CLIENT_CERT)
    s = socket.create_connection(("127.0.0.1", port), timeout=8)
    return ctx.wrap_socket(s, server_hostname=sni)


def peer_cert(port: int, sni: str) -> dict[str, Any]:
    """Subject CN / issuer / SANs of the leaf certificate presented for `sni` (no verification)."""
    s = tls_connect(port, sni, verify=False)
    try:
        der = s.getpeercert(binary_form=True)
        ver = s.version()
    finally:
        s.close()
    p = subprocess.run(["openssl", "x509", "-inform", "DER", "-noout", "-subject", "-issuer", "-ext", "subjectAltName"],
                       input=der, capture_output=True, timeout=10)
    txt = p.stdout.decode()
    out = {"tls_version": ver, "subject": "", "issuer": "", "sans": ""}
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("subject="):
            out["subject"] = line[len("subject="):].strip()
        elif line.startswith("issuer="):
            out["issuer"] = line[len("issuer="):].strip()
        elif line.startswith("DNS:") or "DNS:" in line:
            out["sans"] = line
    return out


def raw_http(port: int, request: bytes, *, prefix: bytes = b"", timeout: float = 8) -> bytes:
    """Send a raw HTTP/1.1 request (optionally prefixed with a PROXY protocol line) and return head + decoded body
    (chunked transfer-encoding is decoded so the result can be parsed like a Content-Length response)."""
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    try:
        s.sendall(prefix + request)
        buf = b""
        while True:
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if b"\r\n\r\n" in buf:
                head, _, body = buf.partition(b"\r\n\r\n")
                hl = head.lower()
                m = [h for h in head.split(b"\r\n") if h.lower().startswith(b"content-length:")]
                if m and len(body) >= int(m[0].split(b":")[1]):
                    break
                if b"transfer-encoding: chunked" in hl and body.rstrip().endswith(b"0"):
                    break
        head, _, body = buf.partition(b"\r\n\r\n")
        if b"transfer-encoding: chunked" in head.lower():
            out, rest = b"", body
            while rest:
                line, _, rest = rest.partition(b"\r\n")
                try:
                    n = int(line.split(b";")[0].strip() or b"0", 16)
                except ValueError:
                    break
                if n == 0:
                    break
                out += rest[:n]
                rest = rest[n + 2:]
            return head + b"\r\n\r\n" + out
        return buf
    finally:
        s.close()


def jwt_hs256(payload: dict[str, Any], secret: str = JWT_SECRET) -> str:
    def b64(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    h = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": "pxlab"}, separators=(",", ":")).encode())
    p = b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64(sig)}"


def h2c_get(port: int, authority: str, path: str = "/") -> tuple[int | None, bytes]:
    """HTTP/2 with prior knowledge (no TLS, no Upgrade) over a raw socket."""
    import h2.config
    import h2.connection
    import h2.events
    s = socket.create_connection(("127.0.0.1", port), timeout=8)
    conn = h2.connection.H2Connection(config=h2.config.H2Configuration(client_side=True, header_encoding="utf-8"))
    conn.initiate_connection()
    s.sendall(conn.data_to_send())
    sid = conn.get_next_available_stream_id()
    conn.send_headers(sid, [(":method", "GET"), (":path", path), (":scheme", "http"), (":authority", authority)], end_stream=True)
    s.sendall(conn.data_to_send())
    status, body, done = None, b"", False
    t0 = time.time()
    try:
        while not done and time.time() - t0 < 8:
            data = s.recv(65536)
            if not data:
                break
            for ev in conn.receive_data(data):
                if isinstance(ev, h2.events.ResponseReceived):
                    status = int(dict(ev.headers)[":status"])
                elif isinstance(ev, h2.events.DataReceived):
                    body += ev.data
                    conn.acknowledge_received_data(ev.flow_controlled_length, ev.stream_id)
                elif isinstance(ev, (h2.events.StreamEnded, h2.events.StreamReset, h2.events.ConnectionTerminated)):
                    done = True
            out = conn.data_to_send()
            if out:
                s.sendall(out)
    finally:
        s.close()
    return status, body


# ---------------------------------------------------------------------------------------------- routing
@probe("route_host", "routing", "Host-based routing", "Host: a.lab -> pool app (+X-Route: a); Host: b.lab -> pool b")
def p_route_host(c: Ctx):
    a = c.echo("a.lab")
    b = c.echo("b.lab")
    ok = a["pool"] == "app" and a["headers"].get("X-Route") == "a" and b["instance"] == "b1"
    return {"ok": ok, "detail": f"a.lab -> {a['instance']} (X-Route={a['headers'].get('X-Route')}), b.lab -> {b['instance']}"}


@probe("route_path_prefix", "routing", "Path prefix route + strip prefix", "/api/hello -> upstream sees /hello, X-Route: api")
def p_route_prefix(c: Ctx):
    e = c.echo("app.lab", "/api/hello?x=1")
    ok = e["path"] == "/hello" and e["headers"].get("X-Route") == "api" and e["raw_query"] == "x=1"
    return {"ok": ok, "detail": f"upstream path={e['path']} query={e['raw_query']} X-Route={e['headers'].get('X-Route')}"}


@probe("route_path_regex", "routing", "Regex path route", "^/v[0-9]+/ -> X-Route: versioned, path untouched")
def p_route_regex(c: Ctx):
    e = c.echo("app.lab", "/v2/things")
    ok = e["path"] == "/v2/things" and e["headers"].get("X-Route") == "versioned"
    return {"ok": ok, "detail": f"path={e['path']} X-Route={e['headers'].get('X-Route')}"}


@probe("route_rewrite", "routing", "URL rewrite (regex capture)", "/old/<x> -> upstream sees /new/<x>")
def p_route_rewrite(c: Ctx):
    e = c.echo("app.lab", "/old/thing")
    ok = e["path"] == "/new/thing"
    return {"ok": ok, "detail": f"upstream path={e['path']} X-Route={e['headers'].get('X-Route')}"}


@probe("route_redirect", "routing", "Redirect issued by the proxy", "/redirect-me -> 301/302/308 Location /landing")
def p_route_redirect(c: Ctx):
    r = c.get("app.lab", "/redirect-me")
    loc = r.headers.get("location", "")
    return {"ok": r.status_code in (301, 302, 307, 308) and loc.rstrip("/").endswith("/landing"), "detail": f"{r.status_code} Location={loc}"}


@probe("route_header", "routing", "Header-based routing", "X-Canary: 1 -> canary instance")
def p_route_header(c: Ctx):
    e = c.echo("app.lab", "/", headers={"X-Canary": "1"})
    return {"ok": e["instance"] == "canary", "detail": f"instance={e['instance']}"}


@probe("route_query", "routing", "Query-parameter routing", "?beta=1 -> canary instance")
def p_route_query(c: Ctx):
    e = c.echo("app.lab", "/?beta=1")
    return {"ok": e["instance"] == "canary", "detail": f"instance={e['instance']}"}


@probe("route_method", "routing", "Method-based rule", "DELETE /api/x -> 405 from the proxy")
def p_route_method(c: Ctx):
    r = c.h1.delete(c.url("app.lab", "/api/x"))
    ok = r.status_code == 405 and r.headers.get("x-instance") is None
    return {"ok": ok, "detail": f"DELETE -> {r.status_code} (x-instance={r.headers.get('x-instance')})"}


@probe("redirect_https", "routing", "HTTP -> HTTPS redirect", "http://redirect.lab/x -> 301/308 https://redirect.lab/x")
def p_redirect_https(c: Ctx):
    r = c.get("redirect.lab", "/x?q=1")
    loc = r.headers.get("location", "")
    return {"ok": r.status_code in (301, 302, 307, 308) and loc.startswith("https://redirect.lab"), "detail": f"{r.status_code} Location={loc}"}


# ---------------------------------------------------------------------------------------------- load balancing
@probe("lb_round_robin", "load-balancing", "Round-robin over 3 backends", "30 requests -> each of app1..3 gets >= 5")
def p_lb_rr(c: Ctx):
    cnt = c.instances("app.lab", "/", 30)
    ok = set(cnt) <= POOL_APP and all(cnt[i] >= 5 for i in POOL_APP)
    return {"ok": ok, "detail": dict(cnt)}


@probe("lb_weighted", "load-balancing", "Weighted round-robin (3:1)", "weighted.lab -> app1 gets 60-90% of 100 requests")
def p_lb_weighted(c: Ctx):
    cnt = c.instances("weighted.lab", "/", 100)
    share = cnt["app1"] / 100
    return {"ok": 0.6 <= share <= 0.9 and set(cnt) <= {"app1", "app2"}, "detail": f"app1 share={share:.2f} {dict(cnt)}", "share": share}


@probe("lb_least_conn", "load-balancing", "Least-connections", "300 requests at concurrency 30: the 100 ms 'slow' backend gets < 20% (round-robin would give 33%)")
def p_lb_leastconn(c: Ctx):
    rs = c.concurrent("leastconn.lab", "/", 300, 30)
    cnt = Counter(r.headers.get("x-instance", f"status:{r.status_code}") for r in rs)
    share = cnt["slow"] / 300
    return {"ok": share < 0.2 and set(cnt) <= {"app1", "app2", "slow"}, "detail": f"slow share={share:.2f} {dict(cnt)}", "share": share}


@probe("lb_hash_header", "load-balancing", "Consistent hashing on a header", "same X-User -> same backend; 10 users -> >= 2 backends")
def p_lb_hash(c: Ctx):
    same = c.instances("hash.lab", "/", 20, headers={"X-User": "u1"})
    spread: Counter = Counter()
    for i in range(30):
        r = c.get("hash.lab", "/", headers={"X-User": f"user{i % 10}"})
        spread[r.headers.get("x-instance", "?")] += 1
    ok = len(same) == 1 and next(iter(same)) in POOL_APP and len(spread) >= 2
    return {"ok": ok, "detail": f"u1 -> {dict(same)}; 10 users -> {dict(spread)}"}


@probe("lb_sticky_cookie", "load-balancing", "Cookie stickiness", "first response sets lab_sticky; following requests land on the same backend")
def p_lb_sticky(c: Ctx):
    client = httpx.Client(verify=CA, timeout=10)
    try:
        r = client.get(c.url("sticky.lab"))
        cookie = r.headers.get("set-cookie", "")
        first = r.headers.get("x-instance")
        seen = Counter(client.get(c.url("sticky.lab")).headers.get("x-instance") for _ in range(12))
    finally:
        client.close()
    ok = "lab_sticky" in cookie and len(seen) == 1 and next(iter(seen)) == first
    return {"ok": ok, "detail": f"cookie={cookie[:60]!r} first={first} then={dict(seen)}"}


@probe("lb_retry_dead_member", "load-balancing", "Retry on connect failure", "retry.lab pool has a dead member: 30 requests must all be 200")
def p_lb_retry(c: Ctx):
    codes = Counter()
    lat = []
    for _ in range(30):
        t0 = time.perf_counter()
        r = c.get("retry.lab", "/")
        lat.append((time.perf_counter() - t0) * 1000)
        codes[r.status_code] += 1
    return {"ok": codes[200] == 30, "detail": f"codes={dict(codes)} max_ms={max(lat):.0f}", "max_ms": round(max(lat), 1)}


@probe("lb_outlier_ejection", "load-balancing", "Passive health / outlier ejection", "flaky returns 500s: after a few failures it must stop receiving traffic (last 20 of 60 requests)")
def p_lb_outlier(c: Ctx):
    c.backend("flaky", "/admin/fail?rate=1")
    c.backend("flaky", "/admin/reset")
    try:
        codes_first, codes_last = Counter(), Counter()
        for i in range(60):
            r = c.get("cb.lab", "/")
            (codes_first if i < 20 else codes_last)[r.status_code] += 1
            if i == 39:
                c1 = c.backend("flaky", "/admin/stats")["requests_total"]
            time.sleep(0.02)
        c2 = c.backend("flaky", "/admin/stats")["requests_total"]
        hits_last20 = c2 - c1
        ok = hits_last20 <= 2 and codes_last.get(200, 0) >= 18
        return {"ok": ok, "detail": f"first20={dict(codes_first)} last20={dict(codes_last)} flaky hits in last 20={hits_last20}",
                "errors_first20": 20 - codes_first.get(200, 0), "errors_last20": 20 - codes_last.get(200, 0), "flaky_hits_last20": hits_last20}
    finally:
        c.backend("flaky", "/admin/fail?rate=0")


@probe("lb_active_health", "load-balancing", "Active health checks", "app3 /healthz -> 503 (still serving /): with active checks app3 stops getting traffic within 20 s; then it is re-admitted")
def p_lb_active(c: Ctx):
    c.backend("app3", "/admin/health?state=down")
    t0 = time.time()
    eject = None
    try:
        while time.time() - t0 < float(c.cfg.features.get("health_max_wait_s", 20)):   # poll: when does app3 stop receiving traffic?
            if c.instances("health.lab", "/", 12).get("app3", 0) == 0:
                eject = round(time.time() - t0, 1)
                break
            time.sleep(1)
        c.backend("app3", "/admin/reset")
        cnt = c.instances("health.lab", "/", 30)
        hits = c.backend("app3", "/admin/stats")["requests_total"]
        ejected = hits == 0 and cnt.get("app3", 0) == 0 and sum(cnt[i] for i in ("app1", "app2")) == 30
    finally:
        c.backend("app3", "/admin/health?state=up")
    t1 = time.time()
    readmit = None
    while time.time() - t1 < 30:
        if c.instances("health.lab", "/", 12).get("app3", 0) > 0:
            readmit = round(time.time() - t1, 1)
            break
        time.sleep(0.5)
    return {"ok": ejected, "detail": f"ejected after {eject}s; while unhealthy: {dict(cnt)} app3 hits={hits}; re-admitted after {readmit}s", "eject_s": eject, "readmit_s": readmit}


@probe("lb_canary_split", "load-balancing", "Weighted traffic split (canary)", "canary.lab: 90% pool app / 10% canary over 200 requests")
def p_lb_canary(c: Ctx):
    cnt = c.instances("canary.lab", "/", 200)
    share = cnt["canary"] / 200
    return {"ok": 0.03 <= share <= 0.25 and (set(cnt) - {"canary"}) <= POOL_APP, "detail": f"canary share={share:.3f} {dict(cnt)}", "share": share}


@probe("lb_mirror", "load-balancing", "Request mirroring / shadowing", "mirror.lab: 20 requests -> shadow's request counter grows by >= 15")
def p_lb_mirror(c: Ctx):
    c.backend("shadow", "/admin/reset")
    for _ in range(20):
        c.get("mirror.lab", "/mirrored")
    time.sleep(1.0)
    n = c.backend("shadow", "/admin/stats")["requests_total"]
    return {"ok": n >= 15, "detail": f"shadow received {n}/20", "mirrored": n}


@probe("lb_upstream_keepalive", "load-balancing", "Upstream connection pooling", "60 sequential requests -> backends see <= 12 new TCP connections")
def p_lb_keepalive(c: Ctx):
    for i in POOL_APP:
        c.backend(i, "/admin/reset")
    for _ in range(60):
        c.get("app.lab", "/")
    conns = {i: c.backend(i, "/admin/stats")["connections_total"] for i in POOL_APP}
    total = sum(conns.values())
    return {"ok": total <= 12, "detail": f"new upstream connections for 60 requests: {conns}", "upstream_connections": total}


# ---------------------------------------------------------------------------------------------- protocols
@probe("http2_tls", "protocols", "HTTP/2 (TLS, ALPN)", "https://app.lab:8443 negotiates h2")
def p_http2(c: Ctx):
    r = c.h2.get(c.url("app.lab", "/", "https"))
    return {"ok": r.status_code == 200 and r.http_version == "HTTP/2", "detail": f"{r.http_version} {r.status_code} upstream proto={r.json().get('proto') if r.status_code == 200 else '?'}"}


@probe("h2c_frontend", "protocols", "HTTP/2 cleartext (prior knowledge) on :8080", "h2c preface on the plain listener is answered")
def p_h2c(c: Ctx):
    st, body = h2c_get(PORTS["http"][1], "app.lab", "/")
    return {"ok": st == 200, "detail": f"status={st} body={body[:40]!r}"}


@probe("http3", "protocols", "HTTP/3 (QUIC)", "https://proxy:8443 answers over QUIC (h3load, 1 connection)")
def p_http3(c: Ctx):
    p = c.tool(["h3load", "-url", "https://proxy:8443/small", "-host", "app.lab", "-conns", "1", "-streams", "1", "-d", "1s"], timeout=40)
    try:
        j = json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return {"ok": False, "detail": f"h3load rc={p.returncode} {p.stdout[-200:]!r} {p.stderr[-200:]!r}"}
    ok = j.get("protocol") == "HTTP/3.0" and j.get("status", {}).get("200", 0) > 0
    return {"ok": ok, "detail": f"proto={j.get('protocol')} status={j.get('status')} errors={j.get('errors')} {j.get('error_samples')}"}


@probe("websocket", "protocols", "WebSocket proxying", "ws://app.lab/ws echoes text and binary frames")
def p_ws(c: Ctx):
    from websockets.sync.client import connect
    with connect(f"ws://app.lab:{PORTS['http'][1]}/ws", open_timeout=8) as ws:
        ws.send("hello")
        a = ws.recv(timeout=8)
        ws.send(b"\x00" * 4096)
        b = ws.recv(timeout=8)
        inst = ws.response.headers.get("X-Instance")
    return {"ok": a == "hello" and b == b"\x00" * 4096, "detail": f"text echo={a!r} binary 4096={len(b)} instance={inst}"}


@probe("sse_streaming", "protocols", "Server-sent events (no response buffering)", "5 events 300 ms apart: first event must arrive < 0.9 s")
def p_sse(c: Ctx):
    t0 = time.perf_counter()
    first = None
    n = 0
    with c.h1.stream("GET", c.url("app.lab", "/sse?n=5&interval=300")) as r:
        for line in r.iter_lines():
            if line.startswith("data:"):
                n += 1
                if first is None:
                    first = time.perf_counter() - t0
    total = time.perf_counter() - t0
    return {"ok": n == 5 and first is not None and first < 0.9, "detail": f"events={n} first={first and round(first, 2)}s total={total:.2f}s"}


@probe("grpc", "protocols", "gRPC proxying (h2 -> upstream h2c :9090)", "grpc.health.v1.Health/Check through :8443 (TLS) or :8080 (h2c)")
def p_grpc(c: Ctx):
    import grpc
    from grpc_health.v1 import health_pb2, health_pb2_grpc
    tried = []
    creds = grpc.ssl_channel_credentials(root_certificates=open(CA, "rb").read())
    for name, ch in (("tls:8443", grpc.secure_channel(f"127.0.0.1:{PORTS['https'][1]}", creds, options=[("grpc.ssl_target_name_override", "app.lab")])),
                     ("h2c:8080", grpc.insecure_channel(f"127.0.0.1:{PORTS['http'][1]}", options=[("grpc.default_authority", "app.lab")]))):
        try:
            stub = health_pb2_grpc.HealthStub(ch)
            resp = stub.Check(health_pb2.HealthCheckRequest(service=""), timeout=8)
            tried.append(f"{name}: {health_pb2.HealthCheckResponse.ServingStatus.Name(resp.status)}")
            if resp.status == health_pb2.HealthCheckResponse.SERVING:
                return {"ok": True, "detail": "; ".join(tried), "via": name}
        except Exception as e:  # noqa: BLE001
            tried.append(f"{name}: {short_err(e, 100)}")
        finally:
            ch.close()
    return {"ok": False, "detail": "; ".join(tried)}


@probe("h2_upstream", "protocols", "HTTP/2 to the upstream (h2c)", "h2.lab -> the backend sees HTTP/2.0")
def p_h2_upstream(c: Ctx):
    e = c.echo("h2.lab")
    return {"ok": e["proto"] == "HTTP/2.0", "detail": f"upstream proto={e['proto']}"}


@probe("tls_upstream", "protocols", "TLS re-encryption to the upstream (verified)", "tls.lab -> backend TLS listener, SNI backend.lab")
def p_tls_upstream(c: Ctx):
    e = c.echo("tls.lab")
    ok = e["listener"] == "tls" and bool(e.get("tls"))
    return {"ok": ok, "detail": f"listener={e['listener']} tls={e.get('tls')}"}


@probe("proxy_protocol_upstream", "protocols", "PROXY protocol v2 to the upstream", "pp.lab -> app1:8081 sees the client IP in the PROXY header")
def p_pp_upstream(c: Ctx):
    e = c.echo("pp.lab")
    pp = e.get("proxy_protocol") or {}
    ok = e["listener"] == "pp" and pp.get("src_ip") == CLIENT_IP
    return {"ok": ok, "detail": f"listener={e['listener']} proxy_protocol={pp}"}


@probe("proxy_protocol_accept", "protocols", "Accept PROXY protocol from clients (:8082)", "PROXY v1 header with 203.0.113.9 -> X-Forwarded-For carries 203.0.113.9")
def p_pp_accept(c: Ctx):
    raw = raw_http(PORTS["pp"][1], b"GET / HTTP/1.1\r\nHost: app.lab\r\nConnection: close\r\n\r\n",
                   prefix=b"PROXY TCP4 203.0.113.9 10.77.0.2 40000 8082\r\n")
    head, _, body = raw.partition(b"\r\n\r\n")
    try:
        e = json.loads(body)
        xff = e["headers"].get("X-Forwarded-For", "")
    except Exception:  # noqa: BLE001
        return {"ok": False, "detail": f"response: {raw[:160]!r}"}
    return {"ok": "203.0.113.9" in xff, "detail": f"X-Forwarded-For={xff} remote_addr={e.get('remote_addr')}"}


@probe("tcp_l4", "protocols", "TCP (L4) proxying", ":9000 -> app1:8080 untouched (no X-Forwarded-For added)")
def p_tcp(c: Ctx):
    raw = raw_http(PORTS["tcp"][1], b"GET /l4 HTTP/1.1\r\nHost: app.lab\r\nConnection: close\r\n\r\n")
    head, _, body = raw.partition(b"\r\n\r\n")
    try:
        e = json.loads(body)
    except Exception:  # noqa: BLE001
        return {"ok": False, "detail": f"response: {raw[:160]!r}"}
    return {"ok": e.get("instance") == "app1" and "X-Forwarded-For" not in e["headers"], "detail": f"instance={e.get('instance')} remote_addr={e.get('remote_addr')} headers={sorted(e['headers'])}"}


@probe("udp_l4", "protocols", "UDP proxying", ":9001/udp -> app1:9002 echo")
def p_udp(c: Ctx):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(5)
    try:
        s.sendto(b"ping-" + c.run_tag.encode(), ("127.0.0.1", PORTS["udp"][1]))
        data, _ = s.recvfrom(65535)
    finally:
        s.close()
    return {"ok": data.startswith(b"echo:"), "detail": data[:60].decode(errors="replace")}


@probe("tls_passthrough_sni", "protocols", "TLS passthrough by SNI (L4)", ":8445 SNI passthrough.lab -> client sees the backend's certificate (CN=backend.lab)")
def p_passthrough(c: Ctx):
    pc = peer_cert(PORTS["passthrough"][1], "passthrough.lab")
    return {"ok": "backend.lab" in pc["subject"], "detail": f"subject={pc['subject']} {pc['tls_version']}"}


# ---------------------------------------------------------------------------------------------- tls
@probe("tls_termination", "tls", "TLS termination", "https://app.lab:8443 verified against the lab CA")
def p_tls(c: Ctx):
    r = c.get("app.lab", "/", "https")
    e = r.json() if r.status_code == 200 else {}
    pc = peer_cert(PORTS["https"][1], "app.lab")
    return {"ok": r.status_code == 200 and "app.lab" in pc["subject"], "detail": f"{r.status_code} cert={pc['subject']} {pc['tls_version']} X-Forwarded-Proto={e.get('headers', {}).get('X-Forwarded-Proto')}"}


@probe("tls13", "tls", "TLS 1.3 negotiated", "default handshake ends up on TLSv1.3")
def p_tls13(c: Ctx):
    s = tls_connect(PORTS["https"][1], "app.lab")
    try:
        v, cipher = s.version(), s.cipher()
    finally:
        s.close()
    return {"ok": v == "TLSv1.3", "detail": f"{v} {cipher[0] if cipher else ''}"}


@probe("tls_legacy_refused", "tls", "TLS 1.0/1.1 refused", "a TLS 1.1 client handshake must fail")
def p_tls_legacy(c: Ctx):
    p = c.tool(["sh", "-c", "echo | openssl s_client -tls1_1 -cipher 'DEFAULT:@SECLEVEL=0' -connect proxy:8443 -servername app.lab 2>&1 | grep -E 'Protocol|alert|error|handshake failure|no protocols' | head -3"], timeout=30)
    out = p.stdout.strip()
    ok = "TLSv1.1" not in out or "alert" in out or "error" in out
    return {"ok": ok, "detail": out[:200] or "(no output: handshake refused)"}


@probe("mtls_client_cert", "tls", "Mutual TLS (client certificate required)", ":8444 without a client cert fails, with lab-client cert -> 200")
def p_mtls(c: Ctx):
    without = "ok?"
    try:
        r = httpx.get(c.url("mtls.lab", "/", "mtls"), verify=CA, timeout=8)
        without = f"status {r.status_code}"
        rejected = r.status_code >= 400
    except Exception as e:  # noqa: BLE001
        without = short_err(e, 80)
        rejected = True
    sctx = ssl.create_default_context(cafile=CA)
    sctx.load_cert_chain(*CLIENT_CERT)
    with httpx.Client(verify=sctx, timeout=8) as cl:
        r = cl.get(c.url("mtls.lab", "/", "mtls"))
    e = r.json() if r.status_code == 200 else {}
    cn = {k: v for k, v in e.get("headers", {}).items() if "cert" in k.lower() or "ssl" in k.lower() or "client" in k.lower()}
    return {"ok": rejected and r.status_code == 200, "detail": f"without cert: {without}; with cert: {r.status_code}; forwarded: {cn}", "cert_headers": cn}


@probe("sni_multi_cert", "tls", "Multiple certificates selected by SNI", "SNI b.lab -> CN=b.lab, SNI app.lab -> CN=app.lab")
def p_sni(c: Ctx):
    a = peer_cert(PORTS["https"][1], "app.lab")
    b = peer_cert(PORTS["https"][1], "b.lab")
    return {"ok": "app.lab" in a["subject"] and "CN = b.lab" in b["subject"] or "CN=b.lab" in b["subject"], "detail": f"app.lab -> {a['subject']}; b.lab -> {b['subject']}"}


@probe("acme_auto_cert", "tls", "Automatic certificate via ACME (Pebble)", "SNI acme.lab presents a certificate issued by Pebble")
def p_acme(c: Ctx):
    deadline = time.time() + float(c.cfg.features.get("acme_wait_s", 90))
    last = ""
    while time.time() < deadline:
        try:
            pc = peer_cert(PORTS["https"][1], "acme.lab")
            last = f"subject={pc['subject']} issuer={pc['issuer']} sans={pc['sans']}"
            if "Pebble" in pc["issuer"] and "acme.lab" in (pc["sans"] + pc["subject"]):
                return {"ok": True, "detail": last}
        except Exception as e:  # noqa: BLE001
            last = short_err(e, 120)
        time.sleep(3)
    return {"ok": False, "detail": last}


# ---------------------------------------------------------------------------------------------- caching
def _origin_tag(r: httpx.Response) -> str:
    """(instance, per-instance counter) of the origin response - identical for a cache hit, different for any new fetch."""
    return f"{r.headers.get('x-instance')}#{r.headers.get('x-backend-counter')}"


@probe("cache_hit", "caching", "Response caching", "second GET /cacheable/<k> is served from cache (same origin instance+counter)")
def p_cache(c: Ctx):
    path = f"/cacheable/{c.run_tag}"
    r1 = c.get("app.lab", path)
    r2 = c.get("app.lab", path)
    h = c.cfg.cache_header.lower()
    t1, t2 = _origin_tag(r1), _origin_tag(r2)
    return {"ok": r1.status_code == 200 and r2.status_code == 200 and t1 == t2, "detail": f"origin {t1} -> {t2}; {c.cfg.cache_header}: {r1.headers.get(h)} -> {r2.headers.get(h)} age={r2.headers.get('age')}"}


@probe("cache_purge", "caching", "Cache purge", "PURGE (or the proxy's purge API) invalidates /cacheable/<k>")
def p_cache_purge(c: Ctx):
    path = f"/cacheable/purge-{c.run_tag}"
    c.get("app.lab", path)
    before = _origin_tag(c.get("app.lab", path))
    purge = c.cfg.features.get("purge") or {"method": "PURGE"}

    def do_purge(client: httpx.Client) -> httpx.Response:
        if purge.get("method") == "PURGE":
            return client.request("PURGE", c.url("app.lab", path))
        if purge.get("method") == "admin":
            return client.request(purge.get("verb", "DELETE"), f"http://127.0.0.1:{PORTS['admin'][1]}{purge['path']}".replace("{path}", path))
        raise RuntimeError(f"unknown purge method {purge}")

    pr = do_purge(c.h1)                                   # on the probe's keep-alive connection ...
    after = _origin_tag(c.get("app.lab", path))
    note = ""
    if after == before:                                   # ... a fresh connection may see the purge while the old one still serves the entry
        with httpx.Client(verify=CA, timeout=10) as fresh:
            after = _origin_tag(fresh.get(c.url("app.lab", path)))
            if after != before:
                note = "; NOTE: the keep-alive connection that sent PURGE kept getting the old entry, a fresh connection saw the purge"
            else:                                         # last resort: the whole sequence on one-request-per-connection clients
                path2 = f"/cacheable/purge2-{c.run_tag}"
                one = lambda m="GET": httpx.request(m, c.url("app.lab", path2), headers={"Host": "app.lab"}, timeout=10)  # noqa: E731
                one(); before = _origin_tag(one()); pr = one(purge.get("method", "PURGE") if purge.get("method") != "admin" else "GET")
                if purge.get("method") == "admin":
                    pr = do_purge(fresh)
                after = _origin_tag(one())
                note = "; NOTE: PURGE only took effect with one-request-per-connection clients (keep-alive connections kept the entry)" if after != before else ""
    return {"ok": after != before and pr.status_code < 400, "detail": f"purge -> {pr.status_code}; origin {before} -> {after}{note}", "keepalive_quirk": bool(note)}


@probe("cache_stale_on_error", "caching", "Serve stale on upstream error", "expired entry + origin 503 -> the stale copy is served (200)")
def p_cache_stale(c: Ctx):
    path = f"/cacheable-short/{c.run_tag}"
    r1 = c.get("app.lab", path)
    time.sleep(2.6)
    r2 = c.get("app.lab", path, headers={"X-Fail": "1"})
    return {"ok": r1.status_code == 200 and r2.status_code == 200 and _origin_tag(r2) == _origin_tag(r1),
            "detail": f"first {r1.status_code} origin={_origin_tag(r1)}; after expiry with origin 503: {r2.status_code} origin={_origin_tag(r2)} {c.cfg.cache_header}={r2.headers.get(c.cfg.cache_header.lower())}"}


# ---------------------------------------------------------------------------------------------- compression
def _compress(c: Ctx, enc: str) -> dict[str, Any]:
    conn = http.client.HTTPConnection("127.0.0.1", PORTS["http"][1], timeout=10)
    conn.request("GET", "/compressible", headers={"Host": "app.lab", "Accept-Encoding": enc})
    r = conn.getresponse()
    body = r.read()
    ce = r.getheader("Content-Encoding", "")
    conn.close()
    return {"ok": ce == enc and len(body) < 65536 / 3, "detail": f"Content-Encoding={ce or 'none'} {len(body)} bytes (65536 uncompressed)", "bytes": len(body)}


@probe("compress_gzip", "compression", "gzip compression", "Accept-Encoding: gzip on a 64 KiB text response")
def p_gzip(c: Ctx):
    return _compress(c, "gzip")


@probe("compress_brotli", "compression", "Brotli compression", "Accept-Encoding: br")
def p_br(c: Ctx):
    return _compress(c, "br")


@probe("compress_zstd", "compression", "Zstandard compression", "Accept-Encoding: zstd")
def p_zstd(c: Ctx):
    return _compress(c, "zstd")


# ---------------------------------------------------------------------------------------------- headers
@probe("xff_headers", "headers", "X-Forwarded-* headers", "X-Forwarded-For carries the client IP; -Proto/-Host/X-Real-IP recorded")
def p_xff(c: Ctx):
    e = c.echo("app.lab")
    h = e["headers"]
    xff = h.get("X-Forwarded-For", "")
    return {"ok": CLIENT_IP in xff, "detail": f"XFF={xff} Proto={h.get('X-Forwarded-Proto')} Host={h.get('X-Forwarded-Host')} X-Real-IP={h.get('X-Real-Ip')}"}


@probe("forwarded_rfc7239", "headers", "RFC 7239 Forwarded header", "Forwarded: for=...;proto=... reaches the upstream")
def p_forwarded(c: Ctx):
    e = c.echo("app.lab")
    f = e["headers"].get("Forwarded", "")
    return {"ok": "for=" in f, "detail": f"Forwarded={f!r}"}


@probe("header_add_remove", "headers", "Header manipulation", "request gets X-Lab-Proxy; response loses X-Powered-By (and the backend's Server header)")
def p_headers(c: Ctx):
    r = c.get("app.lab", "/")
    e = r.json()
    added = e["headers"].get("X-Lab-Proxy")
    return {"ok": bool(added) and "x-powered-by" not in r.headers, "detail": f"X-Lab-Proxy={added} X-Powered-By={'present' if 'x-powered-by' in r.headers else 'removed'} Server={r.headers.get('server')}"}


@probe("request_id", "headers", "Request ID generation", "X-Request-ID is generated per request when the client sends none")
def p_reqid(c: Ctx):
    a, b = c.echo("app.lab")["request_id"], c.echo("app.lab")["request_id"]
    return {"ok": bool(a) and a != b, "detail": f"{a!r} / {b!r}"}


# ---------------------------------------------------------------------------------------------- security
@probe("rate_limit", "security", "Request rate limiting", "/limited at 10 r/s: 40 back-to-back requests -> >= 10 rejected (429/503)")
def p_ratelimit(c: Ctx):
    codes = Counter(c.get("app.lab", "/limited").status_code for _ in range(40))
    rejected = sum(v for k, v in codes.items() if k in (429, 503))
    return {"ok": rejected >= 10, "detail": f"codes={dict(codes)}", "rejected": rejected}


@probe("connection_limit", "security", "Concurrent connection limit", "/conn-limited (max 3 per client): 12 concurrent -> some rejected")
def p_connlimit(c: Ctx):
    rs = c.concurrent("app.lab", "/conn-limited", 12, 12)
    codes = Counter(r.status_code for r in rs)
    rejected = sum(v for k, v in codes.items() if k in (429, 503))
    return {"ok": rejected >= 1 and codes.get(200, 0) >= 1, "detail": f"codes={dict(codes)}", "rejected": rejected}


@probe("ip_allow_deny", "security", "IP allow / deny lists", "/allowed (host allowed) -> 200; /denied (10.77.0.0/24 denied) -> 403")
def p_ip(c: Ctx):
    a, d = c.get("app.lab", "/allowed").status_code, c.get("app.lab", "/denied").status_code
    return {"ok": a == 200 and d == 403, "detail": f"/allowed={a} /denied={d}"}


@probe("basic_auth", "security", "HTTP basic authentication", "/basic -> 401 + WWW-Authenticate; lab:lab-pass -> 200")
def p_basic(c: Ctx):
    r1 = c.get("app.lab", "/basic")
    r2 = c.get("app.lab", "/basic", auth=(BASIC_USER, BASIC_PASS))
    return {"ok": r1.status_code == 401 and r2.status_code == 200, "detail": f"no creds={r1.status_code} ({r1.headers.get('www-authenticate')}) creds={r2.status_code}"}


@probe("jwt_auth", "security", "JWT validation (HS256)", "jwt.lab: no token -> 401; valid token -> 200; bad signature -> 401")
def p_jwt(c: Ctx):
    now = int(time.time())
    good = jwt_hs256({"sub": "alice", "iss": "pxlab", "aud": "pxlab", "iat": now, "exp": now + 600})
    bad = good[:-6] + "AAAAAA"
    r0 = c.get("jwt.lab", "/")
    r1 = c.get("jwt.lab", "/", headers={"Authorization": f"Bearer {good}"})
    r2 = c.get("jwt.lab", "/", headers={"Authorization": f"Bearer {bad}"})
    return {"ok": r0.status_code in (401, 403) and r1.status_code == 200 and r2.status_code in (401, 403), "detail": f"none={r0.status_code} valid={r1.status_code} bad-sig={r2.status_code}"}


@probe("forward_auth", "security", "External authorization (forward auth / auth_request / ext_authz)", "auth.lab: no token -> 401; X-Auth-Token -> 200 (+X-Auth-User copied from the auth service)")
def p_fwd_auth(c: Ctx):
    r0 = c.get("auth.lab", "/")
    r1 = c.get("auth.lab", "/", headers={"X-Auth-Token": AUTH_TOKEN})
    user = r1.json()["headers"].get("X-Auth-User") if r1.status_code == 200 else None
    return {"ok": r0.status_code in (401, 403) and r1.status_code == 200, "detail": f"none={r0.status_code} token={r1.status_code} X-Auth-User={user}"}


@probe("cors", "security", "CORS preflight answered by the proxy", "OPTIONS /cors -> Access-Control-Allow-Origin")
def p_cors(c: Ctx):
    r = c.h1.options(c.url("app.lab", "/cors"), headers={"Origin": "https://example.com", "Access-Control-Request-Method": "PUT"})
    acao = r.headers.get("access-control-allow-origin")
    return {"ok": r.status_code in (200, 204) and bool(acao), "detail": f"{r.status_code} ACAO={acao} methods={r.headers.get('access-control-allow-methods')}"}


@probe("security_headers", "security", "Security response headers", "/secure carries HSTS + X-Content-Type-Options (+ X-Frame-Options)")
def p_sec_headers(c: Ctx):
    r = c.get("app.lab", "/secure")
    h = {k: r.headers.get(k) for k in ("strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy")}
    return {"ok": bool(h["strict-transport-security"]) and bool(h["x-content-type-options"]), "detail": str(h)}


@probe("body_size_limit", "security", "Request body size limit", "POST 2 MiB to /upload -> 413; 100 KiB -> 200")
def p_body(c: Ctx):
    big = c.h1.post(c.url("app.lab", "/upload"), content=b"x" * (2 << 20))
    small = c.h1.post(c.url("app.lab", "/upload"), content=b"x" * (100 << 10))
    return {"ok": big.status_code == 413 and small.status_code == 200, "detail": f"2MiB={big.status_code} 100KiB={small.status_code}"}


@probe("upstream_timeout", "security", "Upstream read timeout", "/timeout (upstream sleeps 5 s, proxy timeout 2 s) -> 5xx after ~2 s")
def p_timeout(c: Ctx):
    t0 = time.perf_counter()
    r = c.h1.get(c.url("app.lab", "/timeout"), timeout=12)
    el = time.perf_counter() - t0
    return {"ok": r.status_code >= 500 and 1.5 <= el <= 4.5, "detail": f"{r.status_code} after {el:.2f}s", "seconds": round(el, 2)}


@probe("fault_injection", "security", "Fault injection", "/fault: ~20% of requests get a 503 from the proxy (100 requests)")
def p_fault(c: Ctx):
    codes = Counter(c.get("app.lab", "/fault").status_code for _ in range(100))
    share = codes.get(503, 0) / 100
    return {"ok": 0.05 <= share <= 0.4, "detail": f"503 share={share:.2f} codes={dict(codes)}", "share": share}


@probe("bandwidth_limit", "security", "Bandwidth limiting", "/bw: 1 MiB at 500 KB/s takes >= 1.5 s")
def p_bw(c: Ctx):
    t0 = time.perf_counter()
    r = c.h1.get(c.url("app.lab", "/bw"), timeout=30)
    el = time.perf_counter() - t0
    return {"ok": r.status_code == 200 and len(r.content) == 1048576 and el >= 1.5, "detail": f"{r.status_code} {len(r.content)} bytes in {el:.2f}s ({len(r.content)/el/1e3:.0f} KB/s)", "seconds": round(el, 2)}


# ---------------------------------------------------------------------------------------------- misc / operations
@probe("static_files", "operations", "Static file serving", "/static/index.html served from the proxy itself")
def p_static(c: Ctx):
    r = c.get("app.lab", "/static/index.html")
    return {"ok": r.status_code == 200 and "pxlab static" in r.text, "detail": f"{r.status_code} {r.text.strip()[:60]!r} x-instance={r.headers.get('x-instance')}"}


@probe("custom_error_page", "operations", "Custom error page", "/error-page (upstream 503) -> the proxy's own page (X-Error-Page: custom)")
def p_error_page(c: Ctx):
    r = c.get("app.lab", "/error-page")
    return {"ok": "custom error page" in r.text.lower(), "detail": f"{r.status_code} X-Error-Page={r.headers.get('x-error-page')} body={r.text.strip()[:60]!r}"}


@probe("hot_reload", "operations", "Configuration reload without restart", "reload command succeeds and the proxy keeps answering")
def p_reload(c: Ctx):
    if not c.cfg.reload_cmd:
        return {"ok": False, "detail": "no reload_cmd configured"}
    rc, out = _reload(c.cfg)
    r = c.get("app.lab", "/")
    return {"ok": rc == 0 and r.status_code == 200, "detail": f"reload rc={rc} {out[:120]!r}; then {r.status_code}"}


def _reload(cfg: StackConfig) -> tuple[int, str]:
    cmd = cfg.reload_cmd
    if cmd and cmd[0] == "shell":
        p = subprocess.run(cmd[1], shell=True, capture_output=True, text=True, timeout=120, cwd=cfg.stack_dir)
        return p.returncode, (p.stdout + p.stderr).strip()
    rc, out, err = dockerctl.exec_in(cfg.container, cmd, timeout=120)
    return rc, (out + err).strip()


@probe("access_log_json", "operations", "Structured (JSON) access log", "the last access-log lines parse as JSON with a status field")
def p_access_log(c: Ctx):
    c.get("app.lab", "/logged")
    time.sleep(float(c.cfg.features.get("log_flush_s", 1.5)))
    al = c.cfg.access_log
    if al.get("kind") == "file":
        _, txt, _ = dockerctl.exec_in(al.get("container", c.cfg.container), ["sh", "-c", f"tail -n 50 {al['path']}"])
    else:
        txt = dockerctl.logs(al.get("container", c.cfg.container), tail=80)
    found = None
    for line in reversed(txt.splitlines()):
        line = line.strip()
        i = line.find("{")
        if i < 0:
            continue
        try:
            j = json.loads(line[i:])
        except Exception:  # noqa: BLE001
            continue
        if isinstance(j, dict) and any(k in j for k in ("status", "code", "response_code", "sc", "RequestMethod", "resp_status", "http_status", "status_code")):
            found = j
            break
    keys = sorted(found)[:12] if found else []
    return {"ok": found is not None, "detail": f"json keys: {keys}" if found else f"no JSON access line in: {txt[-200:]!r}"}


@probe("metrics_prometheus", "operations", "Prometheus metrics", ":9100/metrics (native or exporter sidecar) exposes metrics")
def p_metrics(c: Ctx):
    r = httpx.get(f"http://127.0.0.1:{PORTS['metrics'][1]}{c.cfg.metrics_path}", timeout=10)
    lines = [l for l in r.text.splitlines() if l and not l.startswith("#")]
    return {"ok": r.status_code == 200 and ("# HELP" in r.text or "# TYPE" in r.text) and len(lines) > 5, "detail": f"{r.status_code} {len(lines)} samples e.g. {lines[0][:80] if lines else ''}"}


@probe("admin_api", "operations", "Admin / stats / runtime API", ":9101 (or runtime socket / CLI) answers")
def p_admin(c: Ctx):
    a = c.cfg.admin
    kind = a.get("kind", "http")
    if kind == "http":
        r = httpx.get(f"http://127.0.0.1:{PORTS['admin'][1]}{a.get('path', '/')}", timeout=10, headers=a.get("headers") or {})
        return {"ok": r.status_code == 200 and (a.get("expect", "") in r.text), "detail": f"GET {a.get('path', '/')} -> {r.status_code} {r.text.strip()[:80]!r}"}
    if kind == "tcp":
        s = socket.create_connection(("127.0.0.1", PORTS["admin"][1]), timeout=5)
        s.sendall(a.get("cmd", "show info\n").encode())
        time.sleep(0.5)
        out = s.recv(65535).decode(errors="replace")
        s.close()
        return {"ok": a.get("expect", "") in out, "detail": out.strip()[:80]}
    if kind == "exec":
        rc, out, err = dockerctl.exec_in(a.get("container", c.cfg.container), a["cmd"], timeout=30)
        return {"ok": rc == 0 and a.get("expect", "") in out, "detail": f"rc={rc} {(out or err).strip()[:80]!r}"}
    return {"ok": False, "detail": f"unknown admin kind {kind}"}


@probe("tracing_otel", "operations", "Distributed tracing (OpenTelemetry -> Jaeger)", "after a few requests Jaeger has traces for the proxy's service name")
def p_tracing(c: Ctx):
    svc = c.cfg.tracing_service
    if not svc:
        return {"ok": False, "detail": "no tracing_service configured"}
    import secrets
    for _ in range(3):   # parent-based sampling: the sampled flag (01) makes every proxy trace it, load tools send no traceparent
        c.get("app.lab", "/traced", headers={"traceparent": f"00-{secrets.token_hex(16)}-{secrets.token_hex(8)}-01"})
    deadline = time.time() + 20
    n = 0
    while time.time() < deadline:
        r = httpx.get("http://127.0.0.1:16686/api/traces", params={"service": svc, "limit": 5}, timeout=10)
        n = len((r.json() or {}).get("data") or []) if r.status_code == 200 else 0
        if n:
            break
        time.sleep(2)
    return {"ok": n > 0, "detail": f"jaeger traces for service {svc!r}: {n}"}


@probe("docker_label_discovery", "operations", "Service discovery from Docker labels", "whoami.lab routed to a container that is only declared through labels")
def p_labels(c: Ctx):
    r = c.get("whoami.lab", "/")
    return {"ok": r.status_code == 200 and "Hostname:" in r.text, "detail": f"{r.status_code} {r.text.strip()[:60]!r}"}


PROBE_IDS = [p.id for p in PROBES]
GROUPS = list(dict.fromkeys(p.group for p in PROBES))
