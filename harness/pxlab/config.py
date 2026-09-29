"""Load stack metadata (stacks/<key>/lab.yaml)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .util import STACKS


@dataclass
class StackConfig:
    key: str
    display: str
    stack_dir: Path
    project: str
    container: str                       # the proxy container (exec / cgroup / logs)
    image: str = ""
    family: str = ""                     # nginx | haproxy | envoy | go | rust | api-gateway | cache | c
    category: str = ""
    containers: list[str] = field(default_factory=list)   # every container to account (proxy + sidecars)
    version_cmd: list[str] = field(default_factory=list)  # docker exec <container> <cmd> -> version string
    reload_cmd: list[str] = field(default_factory=list)   # docker exec <container> <cmd> (or ["compose", "exec", ...])
    reload_kind: str = "signal"                           # signal | api | file | none (documentation only)
    admin: dict[str, Any] = field(default_factory=dict)   # {kind: http|tcp|exec, path: ..., cmd: ..., expect: ...}
    metrics_path: str = "/metrics"
    tracing_service: str = ""
    access_log: dict[str, Any] = field(default_factory=dict)   # {kind: docker|file, path: ...}
    cache_header: str = "X-Cache"
    unsupported: dict[str, str] = field(default_factory=dict)  # probe/scenario id -> reason
    features: dict[str, Any] = field(default_factory=dict)
    pre_up: list[str] = field(default_factory=list)       # shell command run in the stack dir before `compose up`
    build: bool = False
    notes: str = ""
    docs: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def compose_file(self) -> Path:
        for f in ("compose.yaml", "compose.yml"):
            if (self.stack_dir / f).exists():
                return self.stack_dir / f
        raise FileNotFoundError(f"no compose file in {self.stack_dir}")

    def unsupported_reason(self, pid: str) -> str | None:
        return self.unsupported.get(pid)


def load_stack(key: str) -> StackConfig:
    d = STACKS / key
    f = d / "lab.yaml"
    if not f.exists():
        raise FileNotFoundError(f"no lab.yaml for stack '{key}' ({f})")
    raw = yaml.safe_load(f.read_text()) or {}
    container = raw.get("container", f"pxlab-{key}")
    containers = raw.get("containers") or [container]
    if container not in containers:
        containers = [container, *containers]
    return StackConfig(
        key=key, display=raw.get("display", key), stack_dir=d, project=raw.get("project", f"pxlab-{key}"),
        container=container, image=raw.get("image", ""), family=raw.get("family", ""), category=raw.get("category", ""),
        containers=containers, version_cmd=raw.get("version_cmd") or [], reload_cmd=raw.get("reload_cmd") or [],
        reload_kind=raw.get("reload_kind", "signal"), admin=raw.get("admin") or {}, metrics_path=raw.get("metrics_path", "/metrics"),
        tracing_service=raw.get("tracing_service", ""), access_log=raw.get("access_log") or {}, cache_header=raw.get("cache_header", "X-Cache"),
        unsupported={k: str(v) for k, v in (raw.get("unsupported") or {}).items()}, features=raw.get("features") or {},
        pre_up=raw.get("pre_up") or [], build=bool(raw.get("build", False)), notes=raw.get("notes", "") or "", docs=raw.get("docs") or [], raw=raw,
    )


def list_stacks() -> list[str]:
    if not STACKS.exists():
        return []
    return sorted(p.name for p in STACKS.iterdir() if (p / "lab.yaml").exists())
