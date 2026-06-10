"""
GraphBackend factory — always returns the Postgres backend.
"""

from __future__ import annotations

import threading

from ...utils.logger import get_logger
from .protocol import GraphBackend


_logger = get_logger("mirofish.graph.factory")
_lock = threading.Lock()
_instance: GraphBackend | None = None


def get_graph_backend() -> GraphBackend:
    """Return the singleton PostgresGraphBackend."""
    global _instance
    if _instance is not None:
        return _instance

    with _lock:
        if _instance is None:
            from .postgres_backend import PostgresGraphBackend
            _logger.info("Selecting PostgresGraphBackend")
            _instance = PostgresGraphBackend()

    return _instance


def reset_graph_backend() -> None:
    """Clear the cached instance. Mainly for tests / hot reload."""
    global _instance
    with _lock:
        _instance = None
