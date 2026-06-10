"""
Graph memory manager — Postgres-only implementation.

Public API (used by simulation_runner.py):
  - create_updater(simulation_id, graph_id) -> updater instance
  - get_updater(simulation_id) -> updater | None
  - stop_updater(simulation_id)
  - stop_all()
  - get_all_stats() -> dict[sim_id, stats]
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from ..utils.logger import get_logger

__all__ = ["GraphMemoryManager"]


_logger = get_logger("mirofish.graph_memory.manager")


class GraphMemoryManager:
    """Postgres-only graph memory manager."""

    _pg_updaters: Dict[str, "PostgresGraphMemoryUpdater"] = {}  # type: ignore[name-defined]
    _pg_lock = threading.Lock()
    _stop_all_done = False

    # ---- Public API -----------------------------------------------------

    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str):
        from .postgres_graph_memory_updater import PostgresGraphMemoryUpdater

        with cls._pg_lock:
            existing = cls._pg_updaters.get(simulation_id)
            if existing is not None:
                try:
                    existing.stop()
                except Exception:
                    _logger.exception("error stopping existing pg updater")
            updater = PostgresGraphMemoryUpdater(graph_id)
            updater.start()
            cls._pg_updaters[simulation_id] = updater
            _logger.info(
                "created postgres memory updater: simulation_id=%s graph_id=%s",
                simulation_id, graph_id,
            )
            return updater

    @classmethod
    def get_updater(cls, simulation_id: str):
        return cls._pg_updaters.get(simulation_id)

    @classmethod
    def stop_updater(cls, simulation_id: str) -> None:
        with cls._pg_lock:
            updater = cls._pg_updaters.pop(simulation_id, None)
        if updater is not None:
            try:
                updater.stop()
            except Exception:
                _logger.exception("error stopping postgres updater")
            _logger.info("stopped postgres memory updater: simulation_id=%s", simulation_id)

    @classmethod
    def stop_all(cls) -> None:
        if cls._stop_all_done:
            return
        cls._stop_all_done = True

        with cls._pg_lock:
            for sim_id, updater in list(cls._pg_updaters.items()):
                try:
                    updater.stop()
                except Exception:
                    _logger.exception(
                        "error stopping postgres updater simulation_id=%s", sim_id
                    )
            cls._pg_updaters.clear()
        _logger.info("all graph memory updaters stopped")

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        return {sid: u.get_stats() for sid, u in cls._pg_updaters.items()}
