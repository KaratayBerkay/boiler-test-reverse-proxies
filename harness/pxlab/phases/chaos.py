"""Phase: chaos under load - (1) a backend dies and comes back, (2) the proxy configuration is reloaded.

A fixed-rate fortio load (open loop) runs from the load-generator container while a Python "timeline" prober
(20 rps, keep-alive) records the status of every request with a timestamp, so we get both the aggregate error count
under load and the error window (first failure -> last failure) around each event.
"""
from __future__ import annotations

import threading
import time
from collections import Counter
from typing import Any

import httpx

from .. import dockerctl, loadgen
from ..config import StackConfig
from ..contract import PORTS
from ..probes import _reload
from ..util import short_err


class Timeline:
    def __init__(self, host: str = "app.lab", path: str = "/", rps: float = 20.0):
        self.url = f"http://127.0.0.1:{PORTS['http'][1]}{path}"
        self.host = host
        self.rps = rps
        self.samples: list[tuple[float, int | str, str]] = []   # (t, status|error, instance)
        self._stop = threading.Event()
        self.t0 = 0.0
        self.th = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        client = httpx.Client(timeout=5)
        self.t0 = time.time()
        i = 0
        while not self._stop.is_set():
            target = self.t0 + i / self.rps
            now = time.time()
            if target > now:
                time.sleep(target - now)
            try:
                r = client.get(self.url, headers={"Host": self.host})
                self.samples.append((time.time() - self.t0, r.status_code, r.headers.get("x-instance", "?")))
            except Exception as e:  # noqa: BLE001
                self.samples.append((time.time() - self.t0, short_err(e, 40), "-"))
            i += 1
        client.close()

    def start(self) -> "Timeline":
        self.th.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self.th.join(timeout=10)

    def summary(self) -> dict[str, Any]:
        bad = [(t, s) for t, s, _ in self.samples if not (isinstance(s, int) and s < 500)]
        codes = Counter(str(s) if isinstance(s, int) else "conn-error" for _, s, _ in self.samples)
        seen = Counter(i for _, _, i in self.samples)
        return {"requests": len(self.samples), "failed": len(bad), "codes": dict(codes), "instances": dict(seen),
                "first_fail_s": round(bad[0][0], 2) if bad else None, "last_fail_s": round(bad[-1][0], 2) if bad else None,
                "fail_window_s": round(bad[-1][0] - bad[0][0], 2) if bad else 0.0}


def _bg_load(cfg: StackConfig, seconds: int, name: str) -> tuple[list[str], dict]:
    cmd = ["fortio", "load", "-qps", "1000", "-c", "32", "-t", f"{seconds}s", "-nocatchup", "-uniform", "-H", "Host: app.lab", "-json", "-",
           "-p", "50,90,99,99.9", "-allow-initial-errors", "-timeout", "5s", "http://proxy:8080/small"]
    return cmd, {}


def run_chaos(cfg: StackConfig, *, log=print, only: set[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    # ---- 1. backend failover: kill app2 at t=6s, bring it back at t=14s, load runs 0..24s
    if not only or "failover" in only:
        log("  failover: fortio 1000 rps + timeline; docker stop pxlab-app2 @6s, start @14s")
        tl = Timeline().start()
        name = f"pxlab-chaos-{cfg.key}"
        res: dict[str, Any] = {}
        th = threading.Thread(target=lambda: res.update(loadgen.run(_bg_load(cfg, 24, name)[0], tool="fortio", cfg_containers=cfg.containers, seconds_hint=24,
                                                                       parse=loadgen.parse_fortio, name=name, timeout=300)), daemon=True)
        th.start()
        time.sleep(6)
        t_stop = time.time() - tl.t0
        dockerctl.container_action("pxlab-app2", "stop")
        time.sleep(8)
        t_start = time.time() - tl.t0
        dockerctl.container_action("pxlab-app2", "start")
        th.join(timeout=300)
        time.sleep(3)
        tl.stop()
        s = tl.summary()
        # when did app2 come back into rotation? (first timeline sample served by app2 after `docker start`)
        back = next((round(t - t_start, 1) for t, _, inst in tl.samples if t > t_start and inst == "app2"), None)
        if back is None:
            for _ in range(30):
                cnt = Counter(httpx.get(f"http://127.0.0.1:{PORTS['http'][1]}/", headers={"Host": "app.lab"}, timeout=5).headers.get("x-instance") for _ in range(12))
                if cnt.get("app2"):
                    back = round(time.time() - tl.t0 - t_start, 1)
                    break
                time.sleep(1)
        gone = next((round(t - t_stop, 1) for t, _, inst in tl.samples if t > t_stop and inst == "app2"), None)
        s["app2_last_seen_after_stop_s"] = gone
        out["failover"] = {"status": "ok" if res.get("rps") else "error", "stop_at_s": round(t_stop, 1), "start_at_s": round(t_start, 1),
                           "load": {k: res.get(k) for k in ("rps", "requests", "errors", "non2xx", "status", "p50", "p99", "p999", "max")},
                           "timeline": s, "app2_back_after_s": back,
                           "detail": f"load errors={res.get('errors')}/{res.get('requests')} ({res.get('status')}); timeline failed={s['failed']}/{s['requests']} "
                                     f"window={s['fail_window_s']}s (first={s['first_fail_s']}s after stop@{t_stop:.1f}s); app2 back after {back}s"}
        log(f"    {out['failover']['detail']}")
    # ---- 2. reload under load
    if not only or "reload" in only:
        if not cfg.reload_cmd or cfg.reload_kind == "none":
            out["reload"] = {"status": "unsupported", "detail": cfg.unsupported_reason("hot_reload") or "no reload command"}
            log(f"  reload: {out['reload']['detail']}")
        else:
            log(f"  reload: oha 64 conns for 15 s; reload @5s ({cfg.reload_kind})")
            tl = Timeline().start()
            name = f"pxlab-chaos-{cfg.key}"
            res = {}
            cmd = ["oha", "--no-tui", "--output-format", "json", "-w", "-z", "15s", "-c", "64", "-H", "Host: app.lab", "http://proxy:8080/small"]
            th = threading.Thread(target=lambda: res.update(loadgen.run(cmd, tool="oha", cfg_containers=cfg.containers, seconds_hint=15, parse=loadgen.parse_oha, name=name, timeout=200)), daemon=True)
            th.start()
            time.sleep(5)
            t_reload = time.time() - tl.t0
            rc, rout = _reload(cfg)
            reload_s = time.time() - tl.t0 - t_reload
            th.join(timeout=200)
            tl.stop()
            s = tl.summary()
            out["reload"] = {"status": "ok" if res.get("rps") and rc == 0 else "error", "reload_rc": rc, "reload_seconds": round(reload_s, 2), "reload_output": rout[:200],
                             "load": {k: res.get(k) for k in ("rps", "requests", "errors", "non2xx", "status", "p50", "p99", "max", "error_samples")}, "timeline": s,
                             "detail": f"reload rc={rc} in {reload_s:.2f}s; load errors={res.get('errors')} non2xx={res.get('non2xx')} of {res.get('requests')}; timeline failed={s['failed']}/{s['requests']}"}
            log(f"    {out['reload']['detail']}")
    return out
