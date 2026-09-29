"""Cross-proxy summary: results/SUMMARY.md + results/summary.json from results/<stack>/latest.json."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .probes import GROUPS, PROBES
from .util import RESULTS, dump_json, load_json, now_iso

ICON = {"ok": "✅", "fail": "❌", "error": "💥", "unsupported": "--"}


def load_all() -> dict[str, dict[str, Any]]:
    out = {}
    if not RESULTS.exists():
        return out
    for d in sorted(RESULTS.iterdir()):
        f = d / "latest.json"
        if f.exists():
            out[d.name] = load_json(f)
    return out


def _fmt_num(v: Any, digits: int = 0) -> str:
    if v is None:
        return "--"
    if isinstance(v, (int, float)):
        return f"{v:,.{digits}f}"
    return str(v)


def _fmt_ms(v: Any) -> str:
    if v is None:
        return "--"
    return f"{v:.2f}" if v < 100 else f"{v:,.0f}"


def _mb(v: Any) -> str:
    return "--" if v is None else (f"{v/1048576:.1f} MB/s" if v > 1048576 else f"{v/1024:.0f} KB/s")


def build_summary() -> tuple[Path, Path]:
    res = load_all()
    keys = sorted(res, key=lambda k: res[k].get("display", k).lower())
    lines: list[str] = []
    w = lines.append
    w("# reverse-proxies — cross-proxy results\n")
    w(f"Generated {now_iso()} from `results/<stack>/latest.json`. Every proxy runs on the same 4 pinned cores (cpuset 0-3) in front of the same "
      "backends (cpus 4-9) with the load generator on cpus 10-13; numbers are therefore comparable across proxies but bounded by this one host.\n")
    w("## Proxies\n")
    w("| stack | proxy | version | image | image size | startup s | capabilities ✅ | ❌ | 💥 | -- |")
    w("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
    for k in keys:
        r = res[k]
        s = (r.get("phases", {}).get("capabilities") or {}).get("summary") or {}
        w(f"| {k} | {r.get('display')} | {r.get('version') or '?'} | `{r.get('image')}` | {r.get('image_size') or '--'} | {r.get('startup_s') or '--'} | "
          f"{s.get('ok', '--')} | {s.get('fail', '--')} | {s.get('error', '--')} | {s.get('unsupported', '--')} |")
    w("")
    # ---- capability matrix
    w("## Capability matrix\n")
    w("✅ verified by the probe · ❌ configured/attempted but the probe failed · 💥 probe error · -- declared unsupported (reason in the stack's lab.yaml and docs/configs/<stack>.md)\n")
    w("| group | capability | " + " | ".join(res[k].get("display", k) for k in keys) + " |")
    w("|---|---|" + "|".join([":---:"] * len(keys)) + "|")
    for g in GROUPS:
        for p in [p for p in PROBES if p.group == g]:
            cells = []
            for k in keys:
                pr = ((res[k].get("phases", {}).get("capabilities") or {}).get("probes") or {}).get(p.id)
                cells.append(ICON.get(pr["status"], "?") if pr else "")
            w(f"| {g} | `{p.id}` {p.title} | " + " | ".join(cells) + " |")
    w("")
    # ---- load matrix
    from .phases.load import SCENARIOS
    w("## Load scenarios (requests/s unless noted; p99 in ms; proxy CPU = average cores used of the 4 allowed)\n")
    for sc in SCENARIOS:
        rows = []
        for k in keys:
            s = ((res[k].get("phases", {}).get("load") or {}).get("scenarios") or {}).get(sc.id)
            if not s:
                continue
            if s.get("status") != "ok":
                rows.append(f"| {res[k].get('display')} | {s.get('status')}: {str(s.get('detail', ''))[:60]} | | | | | | | |")
                continue
            px = s.get("proxy", {})
            head = _mb(s.get("bytes_per_s")) if sc.metric == "bytes_per_s" else (str(s.get("status")) if sc.metric == "status" else _fmt_num(s.get("rps")))
            rows.append(f"| {res[k].get('display')} | {head} | {_fmt_ms(s.get('p50'))} | {_fmt_ms(s.get('p99'))} | {_fmt_ms(s.get('max'))} | {s.get('errors', 0)}/{s.get('non2xx', 0)} | "
                        f"{px.get('cpu_cores_avg', 0):.2f} ({px.get('cpu_pct_of_limit', 0)}%) | {_fmt_num(px.get('cpu_us_per_request'), 1)} | {px.get('mem_end_mb', 0):.0f} |")
        if rows:
            w(f"### `{sc.id}` — {sc.title}\n")
            w("| proxy | " + ("MB/s" if sc.metric == "bytes_per_s" else ("status codes" if sc.metric == "status" else "rps")) + " | p50 ms | p99 ms | max ms | errors/non-2xx | proxy cores (% of 4) | proxy µs/req | proxy mem MB |")
            w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
            lines.extend(rows)
            w("")
    # ---- chaos
    w("## Chaos: backend failover and reload under load\n")
    w("| proxy | failover: load errors / requests | timeline failed (of ~480 @20 rps) | fail window s | app2 back after s | reload kind | reload: load errors / requests | reload timeline failed | reload s |")
    w("|---|---:|---:|---:|---:|---|---:|---:|---:|")
    for k in keys:
        ch = res[k].get("phases", {}).get("chaos") or {}
        f, rl = ch.get("failover") or {}, ch.get("reload") or {}
        fl, ft = f.get("load") or {}, f.get("timeline") or {}
        rlo, rt = rl.get("load") or {}, rl.get("timeline") or {}
        w(f"| {res[k].get('display')} | {fl.get('errors', '--')} / {fl.get('requests', '--')} | {ft.get('failed', '--')} / {ft.get('requests', '--')} | {ft.get('fail_window_s', '--')} | {f.get('app2_back_after_s', '--')} | "
          f"{res[k].get('reload_kind') or ''} | {rlo.get('errors', '--')} / {rlo.get('requests', '--')} | {rt.get('failed', '--')} / {rt.get('requests', '--')} | {rl.get('reload_seconds', '--')} |")
    w("")
    # ---- details per proxy
    w("## Probe details per proxy\n")
    for k in keys:
        r = res[k]
        pr = (r.get("phases", {}).get("capabilities") or {}).get("probes") or {}
        w(f"### {r.get('display')} (`{k}`)\n")
        if r.get("notes"):
            w(r["notes"].strip() + "\n")
        w("| capability | result | detail |")
        w("|---|:---:|---|")
        for p in PROBES:
            x = pr.get(p.id)
            if not x:
                continue
            w(f"| `{p.id}` | {ICON.get(x['status'], '?')} | {str(x.get('detail', '')).replace('|', '/')[:220]} |")
        w("")
    md = RESULTS / "SUMMARY.md"
    md.write_text("\n".join(lines))
    js = RESULTS / "summary.json"
    dump_json(js, {"generated": now_iso(), "stacks": {k: {"display": res[k].get("display"), "image": res[k].get("image"), "version": res[k].get("version"),
                                                          "capabilities": {pid: v.get("status") for pid, v in ((res[k].get("phases", {}).get("capabilities") or {}).get("probes") or {}).items()},
                                                          "load": {sid: {kk: v.get(kk) for kk in ("status", "rps", "p50", "p99", "errors", "non2xx", "bytes_per_s")} | {"proxy": v.get("proxy", {})}
                                                                   for sid, v in ((res[k].get("phases", {}).get("load") or {}).get("scenarios") or {}).items()},
                                                          "chaos": res[k].get("phases", {}).get("chaos")} for k in keys}})
    return md, js
