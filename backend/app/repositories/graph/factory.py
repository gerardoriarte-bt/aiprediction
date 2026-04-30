"""
GraphBackend factory: returns Zep or Postgres based on Config.GRAPH_BACKEND.

Safe to import even when only one backend is fully wired — implementations
are imported lazily so a missing optional dependency for the inactive
backend doesn't break boot.
"""

from __future__ import annotations

import threading

from ...config import Config
from ...utils.logger import get_logger
from .protocol import GraphBackend


_logger = get_logger("mirofish.graph.factory")
_lock = threading.Lock()
_instance: GraphBackend | None = None


def get_graph_backend() -> GraphBackend:
    """Return the singleton GraphBackend selected by Config.GRAPH_BACKEND."""
    global _instance
    if _instance is not None:
        return _instance

    with _lock:
        if _instance is None:
            backend_name = (Config.GRAPH_BACKEND or "zep").lower()
            if backend_name == "postgres":
                from .postgres_backend import PostgresGraphBackend
                _logger.info("Selecting PostgresGraphBackend (GRAPH_BACKEND=postgres)")
                _instance = PostgresGraphBackend()
            else:
                from .zep_backend import ZepGraphBackend
                _logger.info("Selecting ZepGraphBackend (GRAPH_BACKEND=zep)")
                _instance = ZepGraphBackend()

    return _instance


def reset_graph_backend() -> None:
    """Clear the cached instance. Mainly for tests / hot reload."""
    global _instance
    with _lock:
        _instance = None
