"""
Backend-agnostic entity reader factory.

Exposes `get_entity_reader()` which returns a Zep- or Postgres-backed
reader depending on Config.GRAPH_BACKEND. Both readers expose the same
public surface (filter_defined_entities, get_entity_with_context, etc.)
so callers in api/simulation.py don't need to branch.

Also re-exports the EntityNode and FilteredEntities dataclasses so
downstream modules (e.g. oasis_profile_generator) can import their types
from a stable location during the migration window.
"""

from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable

from ..config import Config
from ..utils.logger import get_logger
# Re-export concrete dataclasses; they live in zep_entity_reader for now,
# but oasis_profile_generator and tests can import them from here so
# Phase 6 cleanup can move the file without breaking imports.
from .zep_entity_reader import EntityNode, FilteredEntities

__all__ = [
    "EntityNode",
    "FilteredEntities",
    "EntityReader",
    "get_entity_reader",
    "assert_graph_backend_ready",
]


_logger = get_logger("mirofish.entity_reader.factory")


@runtime_checkable
class EntityReader(Protocol):
    """Public surface used by api/simulation.py."""

    def get_all_nodes(self, graph_id: str) -> list:
        ...

    def get_all_edges(self, graph_id: str) -> list:
        ...

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        ...

    def get_entity_with_context(self, graph_id: str, entity_uuid: str) -> Optional[EntityNode]:
        ...

    def get_entities_by_type(
        self, graph_id: str, entity_type: str, enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        ...


def get_entity_reader() -> EntityReader:
    """Pick the reader for the active GRAPH_BACKEND.

    We do not cache the instance here: the readers are cheap to construct
    and we want test/runtime config changes to be reflected immediately.
    """
    backend = (Config.GRAPH_BACKEND or "zep").lower()
    if backend == "postgres":
        from .postgres_entity_reader import PostgresEntityReader
        _logger.debug("entity_reader factory -> PostgresEntityReader")
        return PostgresEntityReader()
    from .zep_entity_reader import ZepEntityReader
    _logger.debug("entity_reader factory -> ZepEntityReader")
    return ZepEntityReader()


def assert_graph_backend_ready() -> Optional[str]:
    """Return None if the active graph backend is fully configured, or a
    user-facing error string explaining what is missing.

    Replaces the old hard-coded check `if not Config.ZEP_API_KEY:` so the
    same call works for both backends. Callers in api/simulation.py use
    this to short-circuit with a 500 + i18n message before constructing
    the reader.
    """
    backend = (Config.GRAPH_BACKEND or "zep").lower()
    if backend == "zep":
        if not Config.ZEP_API_KEY:
            return "ZEP_API_KEY 未配置 (required when GRAPH_BACKEND=zep)"
        return None
    if backend == "postgres":
        if not Config.DATABASE_URL:
            return "DATABASE_URL 未配置 (required when GRAPH_BACKEND=postgres)"
        return None
    return f"GRAPH_BACKEND={backend!r} is invalid"
