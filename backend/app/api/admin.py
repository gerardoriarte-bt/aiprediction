"""
Admin / observability endpoints (Phase 7).

These are read-only diagnostics for the Zep -> Postgres migration. They
let an operator verify which backend is active, whether the dependent
infrastructure (Postgres pool, embedding provider) is reachable, and
expose tool-level metrics collected during the lifetime of the process.

All endpoints under /api/admin/graph-backend/* return 200 with a
'success' flag so dashboards can poll without retry storms even when the
underlying service is degraded.
"""

from __future__ import annotations

import time
import traceback
from typing import Any, Dict
from urllib import error as urlerr
from urllib import request as urlreq

from flask import jsonify

from . import admin_bp
from ..config import Config
from ..utils.logger import get_logger


logger = get_logger("mirofish.api.admin")


def _ms() -> float:
    return time.perf_counter() * 1000.0


def _postgres_health() -> Dict[str, Any]:
    """Probe Postgres pool with a SELECT 1 round-trip."""
    info: Dict[str, Any] = {"reachable": False, "latency_ms": None, "error": None}
    try:
        from ..repositories.graph import connection
    except Exception as e:
        info["error"] = f"connection module unavailable: {e}"
        return info

    try:
        pool = connection.get_pool()
    except Exception as e:
        info["error"] = str(e)
        return info

    start = _ms()
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        info["reachable"] = True
        info["latency_ms"] = round(_ms() - start, 2)
    except Exception as e:
        info["error"] = str(e)
    return info


def _postgres_table_counts() -> Dict[str, Any]:
    """Cheap sanity check: COUNT(*) on every graph table."""
    counts: Dict[str, Any] = {}
    try:
        from ..repositories.graph import connection
    except Exception:
        return counts
    try:
        pool = connection.get_pool()
    except Exception:
        return counts

    tables = ("graphs", "graph_nodes", "graph_edges", "graph_episodes", "graph_chunks")
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                for t in tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {t};")
                        counts[t] = int(cur.fetchone()[0])
                    except Exception as e:
                        counts[t] = f"error: {e}"
    except Exception as e:
        counts["_error"] = str(e)
    return counts


def _embedding_health() -> Dict[str, Any]:
    """Probe the active embedding provider.

    For OpenAI we only check that an API key is present (no remote call,
    to avoid spending credits on every poll). For Ollama we issue a
    small GET to /api/tags which is free and fast.
    """
    info: Dict[str, Any] = {
        "provider": Config.EMBEDDING_PROVIDER,
        "model": Config.EMBEDDING_MODEL,
        "dim": Config.EMBEDDING_DIM,
        "reachable": False,
        "latency_ms": None,
        "error": None,
    }
    if Config.EMBEDDING_PROVIDER == "openai":
        info["reachable"] = bool(Config.LLM_API_KEY)
        if not info["reachable"]:
            info["error"] = "LLM_API_KEY (used as embedding key) is not set"
        return info

    if Config.EMBEDDING_PROVIDER == "ollama":
        url = (Config.OLLAMA_BASE_URL or "").rstrip("/") + "/api/tags"
        start = _ms()
        try:
            req = urlreq.Request(url, method="GET")
            with urlreq.urlopen(req, timeout=2.0) as resp:
                resp.read()
            info["reachable"] = True
            info["latency_ms"] = round(_ms() - start, 2)
        except urlerr.URLError as e:
            info["error"] = f"cannot reach ollama at {url}: {e.reason}"
        except Exception as e:
            info["error"] = str(e)
        return info

    info["error"] = f"unknown provider: {Config.EMBEDDING_PROVIDER!r}"
    return info


@admin_bp.route("/graph-backend/health", methods=["GET"])
def graph_backend_health():
    """One-stop health check for the graph backend stack."""
    try:
        backend = (Config.GRAPH_BACKEND or "zep").lower()
        payload: Dict[str, Any] = {
            "backend": backend,
            "embedding": _embedding_health(),
            "creative_testing_enabled": Config.CREATIVE_TESTING_ENABLED,
        }

        if backend == "postgres":
            payload["postgres"] = _postgres_health()
            if payload["postgres"].get("reachable"):
                payload["counts"] = _postgres_table_counts()
        else:
            payload["postgres"] = {
                "reachable": False,
                "skipped": "GRAPH_BACKEND != postgres",
            }
            payload["zep_api_key_present"] = bool(Config.ZEP_API_KEY)

        # Lazy import so this endpoint stays cheap.
        try:
            from ..services.graph_metrics import get_metrics_snapshot
            payload["tool_metrics"] = get_metrics_snapshot()
        except Exception:
            payload["tool_metrics"] = {}

        ok = (
            payload["embedding"].get("reachable", False)
            if backend == "postgres"
            else True
        )
        if backend == "postgres":
            ok = ok and payload["postgres"].get("reachable", False)

        return jsonify({"success": True, "ok": ok, "data": payload})
    except Exception as e:
        logger.exception("graph-backend health failed")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@admin_bp.route("/graph-backend/metrics", methods=["GET"])
def graph_backend_metrics():
    """Return the tool-level latency/error counters collected in-process."""
    try:
        from ..services.graph_metrics import get_metrics_snapshot

        return jsonify(
            {
                "success": True,
                "data": {
                    "backend": Config.GRAPH_BACKEND,
                    "tools": get_metrics_snapshot(),
                },
            }
        )
    except Exception as e:
        logger.exception("graph-backend metrics failed")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@admin_bp.route("/graph-backend/metrics/reset", methods=["POST"])
def graph_backend_metrics_reset():
    try:
        from ..services.graph_metrics import reset_metrics

        reset_metrics()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
