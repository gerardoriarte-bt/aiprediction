"""
Backend-agnostic graph memory manager (Phase 5).

Routes simulation_runner.py calls to either the legacy ZepGraphMemoryManager
or to a Postgres-backed equivalent depending on Config.GRAPH_BACKEND.

Public API matches the old ZepGraphMemoryManager classmethods:
  - create_updater(simulation_id, graph_id) -> updater instance
  - get_updater(simulation_id) -> updater | None
  - stop_updater(simulation_id)
  - stop_all()
  - get_all_stats() -> dict[sim_id, stats]

The two updater classes (ZepGraphMemoryUpdater, PostgresGraphMemoryUpdater)
expose the same instance API (start/stop/add_activity/...) so the runner
can hold either type without branching.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from ..config import Config
from ..utils.logger import get_logger
from .zep_graph_memory_updater import (
    ZepGraphMemoryManager,
    ZepGraphMemoryUpdater,
)

__all__ = ["GraphMemoryManager"]


_logger = get_logger("mirofish.graph_memory.manager")


class GraphMemoryManager:
    """Routes to the legacy Zep manager OR a parallel Postgres dict."""

    _pg_updaters: Dict[str, "PostgresGraphMemoryUpdater"] = {}  # type: ignore[name-defined]
    _pg_lock = threading.Lock()
    _stop_all_done = False

    # ---- Helpers --------------------------------------------------------

    @staticmethod
    def _backend() -> str:
        return (Config.GRAPH_BACKEND or "zep").lower()

    # ---- Public API -----------------------------------------------------

    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str):
        if cls._backend() == "postgres":
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
        # default: Zep
        return ZepGraphMemoryManager.create_updater(simulation_id, graph_id)

    @classmethod
    def get_updater(cls, simulation_id: str):
        if cls._backend() == "postgres":
            return cls._pg_updaters.get(simulation_id)
        return ZepGraphMemoryManager.get_updater(simulation_id)

    @classmethod
    def stop_updater(cls, simulation_id: str) -> None:
        if cls._backend() == "postgres":
            with cls._pg_lock:
                updater = cls._pg_updaters.pop(simulation_id, None)
            if updater is not None:
                try:
                    updater.stop()
                except Exception:
                    _logger.exception("error stopping postgres updater")
                _logger.info("stopped postgres memory updater: simulation_id=%s", simulation_id)
            return
        ZepGraphMemoryManager.stop_updater(simulation_id)

    @classmethod
    def stop_all(cls) -> None:
        if cls._stop_all_done:
            return
        cls._stop_all_done = True

        # Stop both pools regardless of current flag — when the process
        # shuts down we want a clean exit on whatever is alive.
        with cls._pg_lock:
            for sim_id, updater in list(cls._pg_updaters.items()):
                try:
                    updater.stop()
                except Exception:
                    _logger.exception(
                        "error stopping postgres updater simulation_id=%s", sim_id
                    )
            cls._pg_updaters.clear()
        try:
            ZepGraphMemoryManager.stop_all()
        except Exception:
            _logger.exception("error stopping zep memory manager")
        _logger.info("all graph memory updaters stopped")

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        if cls._backend() == "postgres":
            return {sid: u.get_stats() for sid, u in cls._pg_updaters.items()}
        return ZepGraphMemoryManager.get_all_stats()
