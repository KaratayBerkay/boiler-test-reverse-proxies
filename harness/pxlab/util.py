"""Shared helpers: paths, JSON, percentiles."""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]          # reverse-proxies/
STACKS = ROOT / "stacks"
RESULTS = ROOT / "results"
SHARED = ROOT / "shared"
DOCS = ROOT / "docs"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def to_jsonable(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat()
    if isinstance(o, bytes):
        return o.decode("utf-8", "replace")
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, BaseException):
        return f"{type(o).__name__}: {o}"[:300]
    if hasattr(o, "__dataclass_fields__"):
        return {k: to_jsonable(getattr(o, k)) for k in o.__dataclass_fields__}
    return o


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(to_jsonable(obj), indent=2, default=str))
    os.replace(tmp, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def summarize(samples_ms: list[float]) -> dict[str, float | int]:
    s = sorted(samples_ms)
    if not s:
        return {"n": 0}
    return {"n": len(s), "min": round(s[0], 3), "p50": round(percentile(s, 0.5), 3), "p90": round(percentile(s, 0.9), 3),
            "p99": round(percentile(s, 0.99), 3), "max": round(s[-1], 3), "mean": round(statistics.fmean(s), 3)}


def short_err(e: BaseException, limit: int = 300) -> str:
    s = " ".join(f"{type(e).__name__}: {e}".split())
    return s[:limit]


def env_flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in {"1", "true", "yes", "on"}
