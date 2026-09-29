"""Thin wrappers around `docker` / `docker compose`: stack lifecycle, exec, chaos, cgroup v2 accounting, running load tools."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from .contract import LOADGEN_CPUSET, NETWORK
from .util import SHARED


class DockerError(RuntimeError):
    pass


def _run(cmd: list[str], *, check: bool = True, timeout: int = 600, cwd: Path | None = None, input: str | None = None) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd) if cwd else None, input=input)
    if check and p.returncode != 0:
        raise DockerError(f"{' '.join(cmd)}\nrc={p.returncode}\nstdout={p.stdout[-2000:]}\nstderr={p.stderr[-4000:]}")
    return p


def compose(compose_file: Path, project: str, *args: str, check: bool = True, timeout: int = 900) -> subprocess.CompletedProcess:
    return _run(["docker", "compose", "-f", str(compose_file), "-p", project, *args], check=check, timeout=timeout, cwd=compose_file.parent)


def ps(compose_file: Path, project: str) -> list[dict[str, Any]]:
    p = compose(compose_file, project, "ps", "-a", "--format", "json", check=False)
    out = p.stdout.strip()
    if not out:
        return []
    if out.startswith("["):
        return json.loads(out)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def up(compose_file: Path, project: str, *, timeout: int = 600, build: bool = False, oneshot: set[str] | None = None,
       recreate: bool = False) -> dict[str, Any]:
    """`docker compose up -d` and wait until every service is healthy (or running when it has no healthcheck).
    recreate=True forces new containers (compose does not restart a container whose mounted config file changed)."""
    oneshot = oneshot or set()
    t0 = time.time()
    args = ["up", "-d", "--remove-orphans"]
    if recreate:
        args.append("--force-recreate")
    if build:
        args.append("--build")
    compose(compose_file, project, *args, timeout=timeout)
    last: list[dict[str, Any]] = []
    while time.time() - t0 < timeout:
        last = ps(compose_file, project)
        pending, failed = [], []
        for c in last:
            svc = c.get("Service") or c.get("Name")
            state = (c.get("State") or "").lower()
            health = (c.get("Health") or "").lower()
            code = c.get("ExitCode", 0)
            if state == "exited":
                if svc in oneshot and code == 0:
                    continue
                failed.append(f"{svc} exited({code})")
            elif state == "running":
                if svc in oneshot:
                    pending.append(f"{svc}:running")
                    continue
                if not health:   # compose prints "" until the first check ran: ask the engine whether a healthcheck exists
                    health = _health_status(c.get("Name") or c.get("ID") or "") or ""
                if health not in ("", "healthy"):
                    pending.append(f"{svc}:{health}")
            else:
                pending.append(f"{svc}:{state}")
        if failed:
            raise DockerError(f"services failed: {failed}\n" + logs_all(compose_file, project, tail=80))
        if not pending:
            return {"seconds": round(time.time() - t0, 1), "services": [c.get("Service") for c in last]}
        time.sleep(1)
    raise DockerError(f"timeout waiting for {project}: {[(c.get('Service'), c.get('State'), c.get('Health')) for c in last]}\n" + logs_all(compose_file, project, tail=80))


def _health_status(container: str) -> str | None:
    p = _run(["docker", "inspect", container, "--format", "{{if .State.Health}}{{.State.Health.Status}}{{end}}"], check=False, timeout=30)
    return p.stdout.strip() or None


def down(compose_file: Path, project: str, *, volumes: bool = True) -> None:
    args = ["down", "--remove-orphans", "-t", "10"]
    if volumes:
        args.append("-v")
    compose(compose_file, project, *args, check=False, timeout=600)


def logs_all(compose_file: Path, project: str, tail: int = 100) -> str:
    p = compose(compose_file, project, "logs", "--no-color", "--tail", str(tail), check=False)
    return (p.stdout + p.stderr)[-12000:]


def logs(container: str, tail: int = 200, since: str | None = None, split: bool = False) -> str | tuple[str, str]:
    """Container logs; `docker logs` keeps the container's stdout and stderr apart, so split=True returns (stdout, stderr)."""
    args = ["docker", "logs", "--tail", str(tail)]
    if since:
        args += ["--since", since]
    p = _run([*args, container], check=False, timeout=60)
    return (p.stdout, p.stderr) if split else p.stdout + p.stderr


def exec_in(container: str, cmd: list[str], *, timeout: int = 120, user: str | None = None, check: bool = False, input: str | None = None) -> tuple[int, str, str]:
    full = ["docker", "exec"]
    if input is not None:
        full.append("-i")
    if user:
        full += ["-u", user]
    p = _run([*full, container, *cmd], check=check, timeout=timeout, input=input)
    return p.returncode, p.stdout, p.stderr


def container_action(container: str, action: str, *, timeout: int = 120) -> None:
    assert action in {"stop", "start", "kill", "restart", "pause", "unpause"}
    args = ["docker", action]
    if action in {"stop", "restart"}:
        args += ["-t", "5"]
    _run([*args, container], timeout=timeout)


def signal(container: str, sig: str) -> None:
    _run(["docker", "kill", "-s", sig, container], timeout=30)


def inspect(container: str) -> dict[str, Any]:
    p = _run(["docker", "inspect", container])
    return json.loads(p.stdout)[0]


def container_ip(container: str, network: str = NETWORK) -> str | None:
    try:
        d = inspect(container)
        return d["NetworkSettings"]["Networks"][network]["IPAddress"]
    except Exception:  # noqa: BLE001
        return None


def image_size(image: str) -> str | None:
    p = _run(["docker", "image", "inspect", image, "--format", "{{.Size}}"], check=False)
    if p.returncode != 0:
        return None
    b = int(p.stdout.strip())
    return f"{b/1e9:.2f} GB" if b > 1e9 else f"{b/1e6:.0f} MB"


def image_version_label(image: str) -> str | None:
    p = _run(["docker", "image", "inspect", image, "--format", '{{index .Config.Labels "org.opencontainers.image.version"}}'], check=False)
    v = p.stdout.strip()
    return v or None


def run_tool(args: list[str], *, name: str = "pxlab-loadgen-run", timeout: int = 600, image: str = "pxlab-loadgen:latest",
             cpuset: str = LOADGEN_CPUSET, nofile: int = 1048576, detach: bool = False, extra: list[str] | None = None) -> subprocess.CompletedProcess | str:
    """Run one load tool / client inside the pxlab network, pinned to the load-generator CPUs."""
    _run(["docker", "rm", "-f", name], check=False, timeout=30)
    base = ["docker", "run", "--name", name, "--network", NETWORK, "--cpuset-cpus", cpuset, f"--ulimit=nofile={nofile}:{nofile}",
            "-v", f"{SHARED / 'certs'}:/certs:ro", "-v", f"{SHARED / 'loadgen' / 'k6'}:/k6:ro", *(extra or [])]
    if detach:
        p = _run([*base, "-d", image, *args], timeout=60)
        return p.stdout.strip()
    return _run([*base, "--rm", image, *args], check=False, timeout=timeout)


def wait_container(name: str, timeout: int = 600) -> tuple[int, str, str]:
    """Wait for a detached tool container, return (exit code, stdout, stderr) and remove it."""
    p = _run(["docker", "wait", name], timeout=timeout)
    code = int(p.stdout.strip() or "1")
    out, err = logs(name, tail=100000, split=True)
    _run(["docker", "rm", "-f", name], check=False, timeout=30)
    return code, out, err


# ---------------------------------------------------------------------------------------------- cgroup v2 accounting
_CG_ROOT = Path("/sys/fs/cgroup/system.slice")


def cgroup_paths(containers: list[str]) -> dict[str, Path]:
    out = {}
    for name in containers:
        p = _run(["docker", "inspect", name, "--format", "{{.Id}}"], check=False)
        cid = p.stdout.strip()
        if cid and (_CG_ROOT / f"docker-{cid}.scope").exists():
            out[name] = _CG_ROOT / f"docker-{cid}.scope"
    return out


def cgroup_snapshot(paths: dict[str, Path]) -> dict[str, dict[str, float]]:
    snap = {}
    for name, d in paths.items():
        try:
            usage = 0.0
            for line in (d / "cpu.stat").read_text().splitlines():
                if line.startswith("usage_usec"):
                    usage = float(line.split()[1])
            quota = (d / "cpu.max").read_text().split()
            cpu_limit = float(quota[0]) / float(quota[1]) if quota[0] != "max" else None
            cpuset = (d / "cpuset.cpus.effective").read_text().strip() if (d / "cpuset.cpus.effective").exists() else ""
            mem_max = (d / "memory.max").read_text().strip()
            snap[name] = {"usage_usec": usage, "cpu_limit_cores": cpu_limit, "cpuset": cpuset,
                          "mem_current": float((d / "memory.current").read_text()),
                          "mem_peak": float((d / "memory.peak").read_text()) if (d / "memory.peak").exists() else None,
                          "mem_limit": float(mem_max) if mem_max != "max" else None, "t": time.time()}
        except Exception:  # noqa: BLE001
            pass
    return snap


def cgroup_delta(before: dict[str, dict[str, float]], after: dict[str, dict[str, float]]) -> dict[str, dict[str, Any]]:
    out = {}
    for name, a in after.items():
        b = before.get(name)
        if not b:
            continue
        el = a["t"] - b["t"]
        cores = (a["usage_usec"] - b["usage_usec"]) / 1e6 / el if el > 0 else 0.0
        out[name] = {"cpu_cores_avg": round(cores, 3), "cpu_seconds": round((a["usage_usec"] - b["usage_usec"]) / 1e6, 2), "cpuset": a.get("cpuset"),
                     "mem_end_mb": round(a["mem_current"] / 1048576, 1), "mem_start_mb": round(b["mem_current"] / 1048576, 1),
                     "mem_peak_mb": round(a["mem_peak"] / 1048576, 1) if a.get("mem_peak") else None, "window_s": round(el, 2)}
    return out


def cpuset_size(cpuset: str) -> int:
    n = 0
    for part in cpuset.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            n += int(b) - int(a) + 1
        else:
            n += 1
    return n
