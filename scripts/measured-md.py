#!/usr/bin/env python3
"""Write skills/reverse-proxy-load-testing/references/measured.md from results/<stack>/latest.json.

The skill quotes the lab's numbers; regenerating them here keeps the skill honest after a re-run.
Run: uv run --project harness python scripts/measured-md.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
from pxlab.phases.load import SCENARIOS          # noqa: E402
from pxlab.report import load_all                # noqa: E402

OUT = ROOT / "skills" / "reverse-proxy-load-testing" / "references" / "measured.md"


def main() -> None:
    res = load_all()
    keys = sorted(res, key=lambda k: res[k].get("display", k).lower())
    lines = [
        "# Measured: 12 proxies x 14 scenarios",
        "",
        f"Generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')} from `reverse-proxies/results/<stack>/latest.json` "
        "(`scripts/measured-md.py`). Proxy pinned to 4 cores, backends 12, load generator 8, all on one 28-core host; "
        "15 s per scenario after a 3 s warm-up. `cores` = average proxy cores used (of 4); `µs/req` = proxy CPU per request; "
        "`err/non2xx` = transport errors / non-2xx responses. Numbers are comparable across proxies, not absolute.",
        "",
        "## Scenarios",
        "",
    ]
    for sc in SCENARIOS:
        unit = {"bytes_per_s": "MB/s", "p99": "p99 ms (open loop, lower is better)", "status": "2xx passed of 2 000 sent"}.get(sc.metric, "req/s")
        lines += [f"### `{sc.id}` - {sc.title}", "", f"| proxy | {unit} | p50 ms | p99 ms | max ms | err / non-2xx | cores | µs/req | mem MB (end / peak) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        rows = []
        for k in keys:
            s = ((res[k].get("phases", {}).get("load") or {}).get("scenarios") or {}).get(sc.id)
            if not s:
                continue
            if s.get("status") != "ok":
                rows.append((None, f"| {res[k]['display']} | {s.get('status')}: {str(s.get('detail', ''))[:70]} | | | | | | | |"))
                continue
            px = s.get("proxy") or {}
            if sc.metric == "bytes_per_s":
                head = (s.get("bytes_per_s") or 0) / 1048576
            elif sc.metric == "p99":
                head = s.get("p99") or 0
            elif sc.metric == "status":
                head = max(0, (s.get("requests") or 0) - (s.get("non2xx") or 0) - (s.get("errors") or 0))
            else:
                head = s.get("rps") or 0
            f = (lambda v: f"{v:,.1f}") if sc.metric in ("bytes_per_s", "p99") else (lambda v: f"{v:,.0f}")
            rows.append((head, f"| {res[k]['display']} | **{f(head)}** | {s.get('p50', 0):.2f} | {s.get('p99', 0):.2f} | {s.get('max', 0):,.0f} | {s.get('errors', 0)} / {s.get('non2xx', 0)} | "
                               f"{px.get('cpu_cores_avg', 0):.2f} | {px.get('cpu_us_per_request') or 0:,.0f} | {px.get('mem_end_mb', 0):,.0f} / {px.get('mem_peak_mb', 0):,.0f} |"))
        ok = [r for r in rows if r[0] is not None]
        ok.sort(key=lambda r: r[0], reverse=(sc.metric != "p99"))
        lines += [r[1] for r in ok] + [r[1] for r in rows if r[0] is None] + [""]
    lines += ["## Chaos", "", "| proxy | failover: errors / requests at 1 000 rps | timeline failed | app2 back after s | reload mechanism | reload: errors / requests |", "|---|---:|---:|---:|---|---:|"]
    for k in keys:
        ch = res[k].get("phases", {}).get("chaos") or {}
        f, rl = ch.get("failover") or {}, ch.get("reload") or {}
        if not f and not rl:
            continue
        fl, ft, rlo, rt = f.get("load") or {}, f.get("timeline") or {}, rl.get("load") or {}, rl.get("timeline") or {}
        lines.append(f"| {res[k]['display']} | {fl.get('errors', '-')} / {fl.get('requests', '-')} | {ft.get('failed', '-')} / {ft.get('requests', '-')} | {f.get('app2_back_after_s', '-')} | "
                     f"{(res[k].get('reload_kind') or '').split('(')[0].strip()} | {rlo.get('errors', '-')} / {rlo.get('requests', '-')} |")
    lines += ["", "See `reverse-proxies/docs/findings.md` for the commentary on these numbers."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
