"""Phase: load scenarios. Every scenario hits `proxy:<port>` from a load-generator container pinned to its own CPUs;
the proxy is pinned to 4 cores (compose `cpuset: "0-3"`), so rps and CPU-per-request are comparable across proxies.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .. import loadgen
from ..config import StackConfig
from ..contract import PORTS
from ..util import short_err


@dataclass
class Scenario:
    id: str
    title: str
    tool: str
    build: Callable[[int, str], list[str]]      # (seconds, tag) -> command inside the loadgen container
    parse: Callable[[str], dict[str, Any]]
    needs: str | None = None                    # capability probe id that must not be unsupported
    k6: bool = False
    seconds: int | None = None
    prime: str | None = None                    # URL path to request once before the run (cache priming)
    metric: str = "rps"                         # headline metric for the summary table


def _oha(*args: str) -> list[str]:
    # -w: let in-flight requests finish at the deadline instead of counting them as errors
    return ["oha", "--no-tui", "--output-format", "json", "-w", "-H", "Host: app.lab", *args]


def _oha_h2(*args: str) -> list[str]:
    # HTTP/2: no Host header (nginx & co. reject Host != :authority); `proxy` is served by the default vhost
    return ["oha", "--no-tui", "--output-format", "json", "-w", "--http2", *args]


SCENARIOS: list[Scenario] = [
    Scenario("h1_keepalive", "HTTP/1.1 keep-alive, 64 connections, /small", "oha",
             lambda s, t: _oha("-z", f"{s}s", "-c", "64", "http://proxy:8080/small"), loadgen.parse_oha),
    Scenario("h1_no_keepalive", "HTTP/1.1 new connection per request, 64 in flight", "oha",
             lambda s, t: _oha("-z", f"{s}s", "-c", "64", "--disable-keepalive", "http://proxy:8080/small"), loadgen.parse_oha),
    Scenario("wrk_h1", "wrk reference: 8 threads, 64 connections, /small", "wrk",
             lambda s, t: ["wrk", "-t8", "-c64", f"-d{s}s", "--latency", "-H", "Host: app.lab", "http://proxy:8080/small"], loadgen.parse_wrk),
    Scenario("tls_h1", "HTTPS HTTP/1.1 keep-alive, 64 connections", "oha",
             lambda s, t: _oha("-z", f"{s}s", "-c", "64", "--insecure", "https://proxy:8443/small"), loadgen.parse_oha, needs="tls_termination"),
    Scenario("tls_h2", "HTTPS HTTP/2: 16 connections x 8 streams", "oha",
             lambda s, t: _oha_h2("-z", f"{s}s", "-c", "16", "-p", "8", "--insecure", "https://proxy:8443/small"), loadgen.parse_oha, needs="http2_tls"),
    Scenario("h3", "HTTP/3 (QUIC): 16 connections x 8 streams", "h3load",
             lambda s, t: ["h3load", "-url", "https://proxy:8443/small", "-host", "app.lab", "-conns", "16", "-streams", "8", "-d", f"{s}s"], loadgen.parse_h3load, needs="http3"),
    Scenario("large_1mb", "1 MiB responses, 32 connections (throughput MB/s)", "oha",
             lambda s, t: _oha("-z", f"{s}s", "-c", "32", "http://proxy:8080/bin/1048576"), loadgen.parse_oha, metric="bytes_per_s"),
    Scenario("gzip_64k", "64 KiB text compressed by the proxy (gzip), 64 connections", "oha",
             lambda s, t: _oha("-z", f"{s}s", "-c", "64", "-H", "Accept-Encoding: gzip", "http://proxy:8080/compressible"), loadgen.parse_oha, needs="compress_gzip"),
    Scenario("cache_hit", "served from the proxy cache, 64 connections", "oha",
             lambda s, t: _oha("-z", f"{s}s", "-c", "64", f"http://proxy:8080/cacheable/load-{t}"), loadgen.parse_oha, needs="cache_hit", prime="/cacheable/load-{tag}"),
    Scenario("ws_echo", "WebSocket echo: 64 VUs x 500 messages (k6)", "k6",
             lambda s, t: ["sh", "-c", f"k6 run --quiet --vus 64 --duration {s}s -e URL=ws://proxy:8080/ws -e HOST=app.lab -e MSGS=500 "
                                      f"--summary-trend-stats 'avg,med,p(90),p(99),max' --summary-export=/tmp/k6.json /k6/ws.js >/dev/null 2>&1; echo __K6SUMMARY__; cat /tmp/k6.json"],
             loadgen.parse_k6, needs="websocket", k6=True),
    Scenario("grpc_health", "gRPC Health/Check over TLS: 16 connections x 8 streams (fortio)", "fortio",
             lambda s, t: ["fortio", "load", "-grpc", "-health", "-cacert", "/certs/ca.crt", "-c", "16", "-s", "8", "-qps", "0", "-t", f"{s}s", "-json", "-", "-p", "50,90,99,99.9", "https://proxy:8443"],
             loadgen.parse_fortio, needs="grpc"),
    Scenario("open_loop_5k", "open loop at exactly 5000 rps (64 conns): latency without coordinated omission", "fortio",
             lambda s, t: ["fortio", "load", "-qps", "5000", "-c", "64", "-t", f"{s}s", "-nocatchup", "-uniform", "-H", "Host: app.lab", "-json", "-", "-p", "50,90,99,99.9", "http://proxy:8080/small"],
             loadgen.parse_fortio, metric="p99"),
    Scenario("ratelimit_accuracy", "/limited (10 r/s) hammered at 200 rps for 10 s: how many get through", "oha",
             lambda s, t: _oha("-z", "10s", "-c", "8", "-q", "200", "http://proxy:8080/limited"), loadgen.parse_oha, needs="rate_limit", seconds=10, metric="status"),
    Scenario("c10k", "10 000 concurrent connections holding /delay/500 for 20 s (memory per connection)", "oha",
             lambda s, t: _oha("-z", "20s", "-c", "10000", "http://proxy:8080/delay/500"), loadgen.parse_oha, seconds=20),
]


def run_load(cfg: StackConfig, *, log=print, only: set[str] | None = None, seconds: int | None = None) -> dict[str, Any]:
    secs = seconds or int(cfg.features.get("load_seconds", 15))
    tag = hex(int(time.time()))[-5:]
    out: dict[str, Any] = {"seconds_default": secs, "scenarios": {}}
    # warm-up: 3 s so the first scenario is not measuring cold caches / JIT / connection setup
    loadgen.run(_oha("-z", "3s", "-c", "32", "http://proxy:8080/small"), tool="oha", cfg_containers=cfg.containers, seconds_hint=3,
                parse=loadgen.parse_oha, name=f"pxlab-load-{cfg.key}", timeout=120)
    for sc in SCENARIOS:
        if only and sc.id not in only:
            continue
        reason = cfg.unsupported_reason(sc.id) or (cfg.unsupported_reason(sc.needs) if sc.needs else None)
        if reason:
            out["scenarios"][sc.id] = {"status": "unsupported", "detail": reason, "title": sc.title, "tool": sc.tool}
            log(f"  -- {sc.id:20s} unsupported: {reason[:90]}")
            continue
        s = sc.seconds or secs
        tls_host = str(cfg.features.get("tls_host") or "proxy")   # e.g. hitch in front of Varnish: TLS lives in a sidecar container
        cmd = [a.replace("https://proxy:", f"https://{tls_host}:") for a in sc.build(s, tag)]
        if sc.prime:
            try:
                httpx.get(f"http://127.0.0.1:{PORTS['http'][1]}{sc.prime.replace('{tag}', tag)}", headers={"Host": "app.lab"}, timeout=10)
            except Exception as e:  # noqa: BLE001
                log(f"  prime failed: {short_err(e)}")
        t0 = time.time()
        try:
            r = loadgen.run(cmd, tool=sc.tool, cfg_containers=cfg.containers, seconds_hint=s, parse=sc.parse,
                            name=f"pxlab-load-{cfg.key}", timeout=s + 240, k6_summary=sc.k6)
            if isinstance(r.get("status"), dict):        # the parsers return the status-code distribution under "status"
                r["status_codes"] = r["status"]
            failed_all = (r.get("requests") or 0) == 0 or (r.get("errors") or 0) > (r.get("requests") or 0)
            r["status"] = "ok" if r.get("rps") and not failed_all else "fail"
            if failed_all and not r.get("detail"):
                r["detail"] = "all requests failed: " + ", ".join(f"{k} x{v}" for k, v in (r.get("error_samples") or {}).items())[:160]
        except Exception as e:  # noqa: BLE001
            r = {"status": "error", "detail": short_err(e)}
        r.update(title=sc.title, metric=sc.metric, phase_seconds=round(time.time() - t0, 1))
        out["scenarios"][sc.id] = r
        if r["status"] == "ok":
            log(f"  {sc.id:20s} rps={r['rps']:>9,.0f} p50={r.get('p50') or 0:7.2f} p99={r.get('p99') or 0:8.2f} ms err={r.get('errors', 0)} non2xx={r.get('non2xx', 0)} "
                f"| proxy {r['proxy']['cpu_cores_avg']:.2f} cores ({r['proxy']['cpu_pct_of_limit']}%) {r['proxy']['cpu_us_per_request'] or 0:.0f} us/req mem={r['proxy']['mem_end_mb']} MB "
                f"| backends {r['backends']['cpu_cores_avg']:.1f} loadgen {r['loadgen']['cpu_cores_avg']:.1f} cores")
        else:
            log(f"  {sc.id:20s} {r['status']}: {str(r.get('detail') or r.get('parse_error') or r.get('output_tail', ''))[:160]}")
        time.sleep(2)   # let connections drain between scenarios
    return out
