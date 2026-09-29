"""Run one load tool inside the pxlab network and normalise its output.

Every tool call returns the same shape:
  {tool, cmd, rps, p50, p90, p99, max (ms), requests, errors, non2xx, status: {code: n}, bytes_per_s, seconds, raw: {...}}
plus exact cgroup CPU / memory of the proxy containers, the load generator and the backends for the run window.
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

from . import dockerctl
from .contract import BACKEND_CPUSET, LOADGEN_CPUSET, PROXY_CPUSET
from .util import short_err

BACKEND_CONTAINERS = ["pxlab-app1", "pxlab-app2", "pxlab-app3", "pxlab-slow", "pxlab-flaky", "pxlab-canary", "pxlab-shadow", "pxlab-b1"]


def _ms(v: float | None, unit_scale: float = 1000.0) -> float | None:
    return None if v is None else round(v * unit_scale, 3)


# ---------------------------------------------------------------------------------------------- parsers
def parse_oha(out: str) -> dict[str, Any]:
    j = json.loads(out[out.index("{"):])
    s = j.get("summary", {})
    lp = j.get("latencyPercentiles", {})
    status = {k: v for k, v in j.get("statusCodeDistribution", {}).items()}
    errs = j.get("errorDistribution", {}) or {}
    requests = sum(status.values())
    non2xx = sum(v for k, v in status.items() if not str(k).startswith("2"))
    return {"rps": round(s.get("requestsPerSec", 0), 1), "p50": _ms(lp.get("p50")), "p90": _ms(lp.get("p90")), "p99": _ms(lp.get("p99")),
            "p999": _ms(lp.get("p99.9")), "max": _ms(s.get("slowest")), "mean": _ms(s.get("average")), "requests": requests,
            "errors": sum(errs.values()), "non2xx": non2xx, "status": status, "bytes_per_s": round(s.get("sizePerSec", 0)),
            "seconds": round(s.get("total", 0), 2), "error_samples": dict(list(errs.items())[:3]), "raw": {"summary": s, "latencyPercentiles": lp}}


_UNIT = {"us": 0.001, "ms": 1.0, "s": 1000.0, "m": 60000.0}


def _wrk_time(tok: str) -> float | None:
    m = re.match(r"([0-9.]+)(us|ms|s|m)", tok)
    return round(float(m.group(1)) * _UNIT[m.group(2)], 3) if m else None


def parse_wrk(out: str) -> dict[str, Any]:
    r: dict[str, Any] = {"rps": 0, "p50": None, "p90": None, "p99": None, "max": None, "requests": 0, "errors": 0, "non2xx": 0, "status": {}, "bytes_per_s": 0, "seconds": 0, "raw": {"text": out[-1500:]}}
    for line in out.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "Requests/sec:":
            r["rps"] = float(t[1])
        elif t[0] in ("50%", "90%", "99%"):
            r[{"50%": "p50", "90%": "p90", "99%": "p99"}[t[0]]] = _wrk_time(t[1])
        elif t[0] == "Latency" and len(t) >= 4:
            r["mean"], r["max"] = _wrk_time(t[1]), _wrk_time(t[3])
        elif len(t) >= 4 and t[1] == "requests" and t[2] == "in":
            r["requests"] = int(t[0])
            r["seconds"] = float(t[3].rstrip("s,"))
            m = re.search(r"([0-9.]+)(KB|MB|GB|B) read", line)
            if m:
                r["bytes_per_s"] = round(float(m.group(1)) * {"B": 1, "KB": 1024, "MB": 1048576, "GB": 1073741824}[m.group(2)] / max(r["seconds"], 0.001))
        elif line.strip().startswith("Socket errors:"):
            r["errors"] = sum(int(x) for x in re.findall(r"(\d+)", line))
        elif line.strip().startswith("Non-2xx or 3xx responses:"):
            r["non2xx"] = int(t[-1])
    r["status"] = {"2xx/3xx": r["requests"] - r["non2xx"], "other": r["non2xx"]} if r["requests"] else {}
    return r


def parse_fortio(out: str) -> dict[str, Any]:
    j = json.loads(out[out.index("{"):])
    h = j.get("DurationHistogram", {}) or {}
    pct = {f"p{str(p['Percentile']).replace('.', '')}": _ms(p["Value"]) for p in h.get("Percentiles", [])}
    codes = j.get("RetCodes", {}) or {}
    requests = h.get("Count", 0)
    ok = sum(v for k, v in codes.items() if str(k).startswith("2") or str(k) == "SERVING")
    return {"rps": round(j.get("ActualQPS", 0), 1), "p50": pct.get("p50"), "p90": pct.get("p90"), "p99": pct.get("p99"), "p999": pct.get("p999"),
            "max": _ms(h.get("Max")), "mean": _ms(h.get("Avg")), "requests": requests, "errors": requests - ok, "non2xx": requests - ok, "status": codes,
            "bytes_per_s": round((j.get("Sizes", {}) or {}).get("Sum", 0) / max(j.get("ActualDuration", 1) / 1e9, 0.001)), "seconds": round(j.get("ActualDuration", 0) / 1e9, 2),
            "requested_qps": j.get("RequestedQPS"), "raw": {"RetCodes": codes, "Percentiles": pct}}


def parse_h3load(out: str) -> dict[str, Any]:
    j = json.loads(out[out.index("{"):])
    lat = j.get("latency_ms", {})
    status = j.get("status", {})
    return {"rps": round(j.get("rps", 0), 1), "p50": lat.get("p50"), "p90": lat.get("p90"), "p99": lat.get("p99"), "max": lat.get("max"), "mean": lat.get("mean"),
            "requests": j.get("requests", 0), "errors": j.get("errors", 0), "non2xx": sum(v for k, v in status.items() if not k.startswith("2")), "status": status,
            "bytes_per_s": round(j.get("bytes", 0) / max(j.get("duration_s", 1), 0.001)), "seconds": round(j.get("duration_s", 0), 2), "protocol": j.get("protocol"),
            "error_samples": j.get("error_samples", [])[:3], "raw": {}}


def parse_k6(summary_json: str) -> dict[str, Any]:
    j = json.loads(summary_json)
    m = j.get("metrics", {})
    rtt = m.get("ws_echo_rtt_ms", {})
    msgs = m.get("ws_messages", {})
    sess = m.get("ws_sessions", {})
    checks = m.get("checks", {})
    return {"rps": round(msgs.get("rate", 0), 1), "p50": rtt.get("med"), "p90": rtt.get("p(90)"), "p99": rtt.get("p(99)"), "max": rtt.get("max"), "mean": rtt.get("avg"),
            "requests": int(msgs.get("count", 0)), "errors": int(checks.get("fails", 0)), "non2xx": int(checks.get("fails", 0)),
            "status": {"sessions": int(sess.get("count", 0)), "check_passes": int(checks.get("passes", 0)), "check_fails": int(checks.get("fails", 0))},
            "bytes_per_s": 0, "seconds": 0, "raw": {"ws_connecting": m.get("ws_connecting"), "ws_session_duration": m.get("ws_session_duration")}}


# ---------------------------------------------------------------------------------------------- runner
def run(cmd: list[str], *, tool: str, cfg_containers: list[str], seconds_hint: float, parse, name: str, timeout: int = 900,
        extra_docker: list[str] | None = None, k6_summary: bool = False) -> dict[str, Any]:
    """Start the tool detached (so its cgroup can be sampled), sample proxy/backend/loadgen usage, wait, parse."""
    accounted = list(dict.fromkeys(cfg_containers + BACKEND_CONTAINERS))
    paths = dockerctl.cgroup_paths(accounted)
    before = dockerctl.cgroup_snapshot(paths)
    t0 = time.time()
    cid = dockerctl.run_tool(cmd, name=name, detach=True, extra=extra_docker)
    lg_paths = {}
    for _ in range(20):
        lg_paths = dockerctl.cgroup_paths([name])
        if lg_paths:
            break
        time.sleep(0.1)
    lg_before = dockerctl.cgroup_snapshot(lg_paths)
    lg_last: dict[str, Any] = {"snap": lg_before}
    stop = threading.Event()

    def _sample():   # the tool's cgroup vanishes with the container: keep the last good sample
        while not stop.is_set():
            snap = dockerctl.cgroup_snapshot(lg_paths)
            if snap:
                lg_last["snap"] = snap
            stop.wait(0.5)
    th = threading.Thread(target=_sample, daemon=True)
    th.start()
    code, out, err = dockerctl.wait_container(name, timeout=timeout)
    stop.set()
    th.join(timeout=2)
    after = dockerctl.cgroup_snapshot(paths)
    lg_after = lg_last["snap"]
    wall = time.time() - t0
    res: dict[str, Any] = {"tool": tool, "cmd": " ".join(cmd), "exit_code": code, "wall_s": round(wall, 1), "stderr_tail": err[-400:]}
    try:
        if k6_summary:
            i = out.find("__K6SUMMARY__")
            res.update(parse(out[i + len("__K6SUMMARY__"):]))
        else:
            res.update(parse(out))
    except Exception as e:  # noqa: BLE001
        res.update({"rps": 0, "requests": 0, "errors": 1, "parse_error": short_err(e), "output_tail": out[-800:]})
    usage = dockerctl.cgroup_delta(before, after)
    lg = dockerctl.cgroup_delta(lg_before, lg_after).get(name, {})
    # CPU numbers are averaged over the whole window; scale to the tool's own measured duration when known
    dur = res.get("seconds") or seconds_hint or wall
    win = next(iter(usage.values()), {}).get("window_s") or wall
    scale = win / dur if dur else 1.0
    proxy_cores = sum(usage[c]["cpu_cores_avg"] for c in cfg_containers if c in usage) * scale
    backend_cores = sum(v["cpu_cores_avg"] for k, v in usage.items() if k in BACKEND_CONTAINERS) * scale
    res["proxy"] = {"cpu_cores_avg": round(proxy_cores, 3), "cpu_limit_cores": dockerctl.cpuset_size(PROXY_CPUSET),
                    "cpu_pct_of_limit": round(100 * proxy_cores / dockerctl.cpuset_size(PROXY_CPUSET), 1),
                    "mem_end_mb": round(sum(usage[c]["mem_end_mb"] for c in cfg_containers if c in usage), 1),
                    "mem_peak_mb": round(sum(usage[c]["mem_peak_mb"] or 0 for c in cfg_containers if c in usage), 1),
                    "per_container": {c: usage[c] for c in cfg_containers if c in usage}}
    res["backends"] = {"cpu_cores_avg": round(backend_cores, 3), "cpu_limit_cores": dockerctl.cpuset_size(BACKEND_CPUSET)}
    res["loadgen"] = {"cpu_cores_avg": round(lg.get("cpu_cores_avg", 0) * (lg.get("window_s", wall) / dur if dur else 1), 3), "cpu_limit_cores": dockerctl.cpuset_size(LOADGEN_CPUSET)}
    rps = res.get("rps") or 0
    res["proxy"]["cpu_us_per_request"] = round(1e6 * proxy_cores / rps, 1) if rps else None
    res["proxy"]["rps_per_core"] = round(rps / proxy_cores) if proxy_cores > 0.05 else None
    return res
