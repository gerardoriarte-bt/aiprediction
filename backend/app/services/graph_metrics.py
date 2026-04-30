"""
Tool-level metrics collector (Phase 7).

In-process, thread-safe counters and latency aggregations for the
ZepToolsService and PostgresToolsService methods. Exposed by the admin
endpoints in api/admin.py and intentionally lightweight — no external
dependency, no metrics backend integration. The counters reset on
process restart.

Usage:
    from .graph_metrics import time_tool

    @time_tool("postgres", "search_graph")
    def search_graph(self, ...):
        ...
"""

from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable, Dict


_LOCK = threading.Lock()
_METRICS: Dict[str, Dict[str, Any]] = {}


def _key(backend: str, tool: str) -> str:
    return f"{backend}:{tool}"


def _record(backend: str, tool: str, duration_ms: float, ok: bool) -> None:
    k = _key(backend, tool)
    with _LOCK:
        bucket = _METRICS.get(k)
        if bucket is None:
            bucket = {
                "backend": backend,
                "tool": tool,
                "calls": 0,
                "errors": 0,
                "total_ms": 0.0,
                "min_ms": float("inf"),
                "max_ms": 0.0,
                "last_ms": 0.0,
            }
            _METRICS[k] = bucket
        bucket["calls"] += 1
        if not ok:
            bucket["errors"] += 1
        bucket["total_ms"] += duration_ms
        bucket["min_ms"] = min(bucket["min_ms"], duration_ms)
        bucket["max_ms"] = max(bucket["max_ms"], duration_ms)
        bucket["last_ms"] = duration_ms


def time_tool(backend: str, tool: str) -> Callable:
    """Decorator factory: time a tool method and record success/failure."""
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            ok = True
            try:
                return fn(*args, **kwargs)
            except Exception:
                ok = False
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000.0
                _record(backend, tool, duration_ms, ok)
        return wrapper
    return deco


def get_metrics_snapshot() -> Dict[str, Any]:
    """Return a JSON-serialisable copy of the metrics map.

    Adds an `avg_ms` field for convenience.
    """
    out: Dict[str, Any] = {}
    with _LOCK:
        for k, b in _METRICS.items():
            calls = b["calls"] or 1
            avg_ms = b["total_ms"] / calls
            out[k] = {
                **b,
                "avg_ms": round(avg_ms, 3),
                "min_ms": 0.0 if b["min_ms"] == float("inf") else round(b["min_ms"], 3),
                "max_ms": round(b["max_ms"], 3),
                "total_ms": round(b["total_ms"], 3),
                "last_ms": round(b["last_ms"], 3),
            }
    return out


def reset_metrics() -> None:
    with _LOCK:
        _METRICS.clear()
