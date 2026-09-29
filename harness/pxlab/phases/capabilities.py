"""Phase: run every capability probe against a running stack."""
from __future__ import annotations

import time
from typing import Any

from ..config import StackConfig
from ..probes import PROBES, Ctx
from ..util import short_err

ICON = {"ok": "✅", "fail": "❌", "error": "💥", "unsupported": "--"}


def run_capabilities(cfg: StackConfig, *, log=print, only: set[str] | None = None) -> dict[str, Any]:
    ctx = Ctx(cfg, log)
    out: dict[str, Any] = {"ready_s": ctx.wait_ready(), "probes": {}}
    ctx.reset_backends()
    try:
        for p in PROBES:
            if only and p.id not in only:
                continue
            reason = cfg.unsupported_reason(p.id)
            if reason:
                out["probes"][p.id] = {"status": "unsupported", "detail": reason, "group": p.group, "title": p.title, "seconds": 0}
                log(f"  {ICON['unsupported']} {p.id:26s} unsupported: {reason[:100]}")
                continue
            t0 = time.time()
            try:
                r = p.fn(ctx)
                status = "ok" if r.get("ok") else "fail"
            except Exception as e:  # noqa: BLE001
                r, status = {"detail": short_err(e)}, "error"
            r.pop("ok", None)
            r.update(status=status, group=p.group, title=p.title, seconds=round(time.time() - t0, 2))
            out["probes"][p.id] = r
            log(f"  {ICON[status]} {p.id:26s} {str(r.get('detail', ''))[:120]}")
    finally:
        try:
            ctx.reset_backends()
        finally:
            ctx.close()
    counts = {s: sum(1 for v in out["probes"].values() if v["status"] == s) for s in ICON}
    out["summary"] = counts
    log(f"  capabilities: {counts}")
    return out
