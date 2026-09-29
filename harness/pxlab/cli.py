"""pxlab command line."""
from __future__ import annotations

import subprocess
import time

import typer
from rich.console import Console

from . import dockerctl
from .config import list_stacks, load_stack
from .util import RESULTS, SHARED, dump_json, now_iso, run_id as new_run_id, short_err

app = typer.Typer(help="Reverse-proxy lab: capability probes, load scenarios and chaos for every proxy stack in stacks/.", no_args_is_help=True)
con = Console()
SHARED_COMPOSE = SHARED / "compose.yaml"


def log(msg: str) -> None:
    con.print(msg, highlight=False, markup=False)


@app.command("list")
def cmd_list():
    """List configured stacks."""
    for k in list_stacks():
        c = load_stack(k)
        log(f"{k:12s} {c.display:28s} image={c.image:40s} family={c.family:12s} unsupported={len(c.unsupported)}")


# ---------------------------------------------------------------------------------------------- shared stack
shared = typer.Typer(help="The shared backend stack (origins, Pebble ACME, Jaeger, whoami).", no_args_is_help=True)
app.add_typer(shared, name="shared")


@shared.command("up")
def shared_up(build: bool = False):
    """Start the shared backends (builds the backend image on first use)."""
    r = dockerctl.up(SHARED_COMPOSE, "pxlab-shared", build=build)
    log(f"shared up in {r['seconds']}s: {r['services']}")


@shared.command("down")
def shared_down():
    dockerctl.down(SHARED_COMPOSE, "pxlab-shared")
    log("shared down")


@shared.command("status")
def shared_status():
    for c in dockerctl.ps(SHARED_COMPOSE, "pxlab-shared"):
        log(f"{c.get('Name'):16s} {c.get('State'):10s} {c.get('Health') or ''}")


@app.command()
def build():
    """Build the lab images (backend, loadgen) and generate certificates."""
    for d in ("backend", "loadgen"):
        log(f"building pxlab-{d} ...")
        subprocess.run(["docker", "build", "-q", "-t", f"pxlab-{d}:latest", "."], cwd=SHARED / d, check=True)
    subprocess.run([str(SHARED / "certs" / "gen.sh")], check=True)


@app.command()
def certs(force: bool = False):
    """(Re)generate the lab PKI and auth material."""
    subprocess.run([str(SHARED / "certs" / "gen.sh"), *(["--force"] if force else [])], check=True)


# ---------------------------------------------------------------------------------------------- stacks
def _pre_up(cfg) -> None:
    for cmd in cfg.pre_up:
        log(f"[{cfg.key}] pre_up: {cmd}")
        subprocess.run(cmd, shell=True, check=True, cwd=cfg.stack_dir)


def _ensure_shared() -> None:
    running = {c.get("Name") for c in dockerctl.ps(SHARED_COMPOSE, "pxlab-shared") if (c.get("State") or "").lower() == "running"}
    if "pxlab-app1" not in running:
        log("shared stack not running: starting it")
        dockerctl.up(SHARED_COMPOSE, "pxlab-shared")


@app.command()
def up(stack: str, build: bool = typer.Option(False, help="docker compose up --build")):
    """Start a proxy stack and wait until healthy."""
    cfg = load_stack(stack)
    _ensure_shared()
    _pre_up(cfg)
    r = dockerctl.up(cfg.compose_file, cfg.project, build=build or cfg.build, recreate=True)
    log(f"[{stack}] up in {r['seconds']}s: {r['services']}")


@app.command()
def down(stack: str):
    """Stop a proxy stack."""
    cfg = load_stack(stack)
    dockerctl.down(cfg.compose_file, cfg.project)
    log(f"[{stack}] down")


def _version(cfg) -> str | None:
    if not cfg.version_cmd:
        return dockerctl.image_version_label(cfg.image)
    try:
        rc, out, err = dockerctl.exec_in(cfg.container, cfg.version_cmd, timeout=30)
        txt = (out or err).strip().splitlines()
        return txt[0][:120] if txt else None
    except Exception as e:  # noqa: BLE001
        return f"? ({short_err(e, 60)})"


ALL_PHASES = ["capabilities", "load", "chaos"]


def _run_phases(cfg, phases: list[str], only: set[str] | None, seconds: int | None, up_seconds: float | None, base: dict | None = None) -> dict:
    from .phases.capabilities import run_capabilities
    from .phases.chaos import run_chaos
    from .phases.load import run_load
    from .report import build_summary
    result = {"stack": cfg.key, "display": cfg.display, "image": cfg.image, "family": cfg.family, "category": cfg.category, "run_id": new_run_id(),
              "started": now_iso(), "notes": cfg.notes, "docs": cfg.docs, "image_size": dockerctl.image_size(cfg.image), "startup_s": up_seconds,
              "version": _version(cfg), "containers": cfg.containers, "unsupported": cfg.unsupported, "phases": {}}
    if base:                                     # `pxlab phase`: keep the other phases (and, with --only, the other entries) of the previous run
        result["phases"] = dict(base.get("phases") or {})
        result["startup_s"] = base.get("startup_s")
        result["started"] = base.get("started") or result["started"]
        result["previous_run_id"] = base.get("run_id")

    def merge(name: str, fresh: dict) -> dict:
        prev = result["phases"].get(name)
        if not only or not isinstance(prev, dict):
            return fresh
        coll = {"capabilities": "probes", "load": "scenarios"}.get(name)
        if not coll:                             # chaos: sub-results keyed by name
            merged = dict(prev); merged.update({k: v for k, v in fresh.items() if not k.startswith("_")}); return merged
        merged = dict(prev); merged[coll] = dict(prev.get(coll) or {}); merged[coll].update(fresh.get(coll) or {})
        if coll == "probes":
            from collections import Counter
            cnt = Counter(v["status"] for v in merged[coll].values())
            merged["summary"] = {k: cnt.get(k, 0) for k in ("ok", "fail", "error", "unsupported")}
        return merged
    save = lambda: dump_json(RESULTS / cfg.key / "latest.json", result) or dump_json(RESULTS / cfg.key / f"{result['run_id']}.json", result)  # noqa: E731
    for name, fn in (("capabilities", lambda: run_capabilities(cfg, log=log, only=only)),
                     ("load", lambda: run_load(cfg, log=log, only=only, seconds=seconds)),
                     ("chaos", lambda: run_chaos(cfg, log=log, only=only))):
        if name not in phases:
            continue
        log(f"[{cfg.key}] phase: {name}")
        t0 = time.time()
        try:
            fresh = fn()
            fresh["_seconds"] = round(time.time() - t0, 1)
            result["phases"][name] = merge(name, fresh)
        except Exception as e:  # noqa: BLE001
            result["phases"][name] = {"_error": short_err(e), "_seconds": round(time.time() - t0, 1)}
            log(f"  phase {name} FAILED: {short_err(e)}")
        save()
    result["finished"] = now_iso()
    save()
    log(f"saved {RESULTS / cfg.key / 'latest.json'}")
    try:
        build_summary()
    except Exception as e:  # noqa: BLE001
        log(f"summary failed: {short_err(e)}")
    return result


@app.command()
def run(stack: str, phases: str = typer.Option(",".join(ALL_PHASES), help="comma-separated: capabilities,load,chaos"),
        only: str = typer.Option(None, help="comma-separated probe / scenario ids to restrict to"),
        seconds: int = typer.Option(None, help="seconds per load scenario (default 15)"),
        no_up: bool = typer.Option(False, "--no-up", help="assume the stack is already running"),
        keep: bool = typer.Option(False, help="leave the stack running afterwards"),
        build: bool = typer.Option(False, help="docker compose up --build")):
    """Bring a stack up, run the selected phases, tear it down."""
    cfg = load_stack(stack)
    ph = [p.strip() for p in phases.split(",") if p.strip()]
    only_set = {x.strip() for x in only.split(",")} if only else None
    up_s = None
    if not no_up:
        _ensure_shared()
        _pre_up(cfg)
        log(f"[{stack}] starting stack ...")
        r = dockerctl.up(cfg.compose_file, cfg.project, build=build or cfg.build, recreate=True)
        up_s = r["seconds"]
        log(f"[{stack}] up in {up_s}s: {r['services']}")
        time.sleep(float(cfg.features.get("settle_seconds", 2)))
    try:
        _run_phases(cfg, ph, only_set, seconds, up_s)
    finally:
        if not keep and not no_up:
            log(f"[{stack}] tearing down ...")
            dockerctl.down(cfg.compose_file, cfg.project)


@app.command()
def phase(stack: str, name: str, only: str = typer.Option(None), seconds: int = typer.Option(None)):
    """Run a single phase against an already-running stack (results are merged into latest.json)."""
    from .util import load_json
    cfg = load_stack(stack)
    only_set = {x.strip() for x in only.split(",")} if only else None
    prev = RESULTS / cfg.key / "latest.json"
    base = load_json(prev) if prev.exists() else None
    return _run_phases(cfg, [name], only_set, seconds, None, base=base)


@app.command()
def probe(stack: str, probe_id: str):
    """Run one capability probe against a running stack and print the details."""
    from .phases.capabilities import run_capabilities
    cfg = load_stack(stack)
    r = run_capabilities(cfg, log=log, only={probe_id})
    log(str(r["probes"].get(probe_id)))


@app.command()
def load(stack: str, scenario: str = typer.Option(None, help="scenario id (default: all)"), seconds: int = typer.Option(None)):
    """Run load scenarios against a running stack (no result file)."""
    from .phases.load import run_load
    cfg = load_stack(stack)
    run_load(cfg, log=log, only={scenario} if scenario else None, seconds=seconds)


@app.command()
def report():
    """Rebuild results/SUMMARY.md and results/summary.json from every results/<stack>/latest.json."""
    from .report import build_summary
    md, js = build_summary()
    log(f"wrote {md} and {js}")


@app.command()
def info(stack: str):
    """Version / containers / unsupported list of a stack."""
    cfg = load_stack(stack)
    log(f"{cfg.display}: image={cfg.image} version={_version(cfg)} containers={cfg.containers}")
    for k, v in cfg.unsupported.items():
        log(f"  unsupported {k}: {v}")


@app.command()
def probes():
    """List every capability probe (id, group, what it proves)."""
    from .probes import PROBES
    for p in PROBES:
        log(f"{p.group:14s} {p.id:26s} {p.title:52s} {p.proves}")


@app.command()
def scenarios():
    """List every load scenario."""
    from .phases.load import SCENARIOS
    for s in SCENARIOS:
        log(f"{s.id:20s} {s.tool:7s} {s.title}")


if __name__ == "__main__":
    app()
