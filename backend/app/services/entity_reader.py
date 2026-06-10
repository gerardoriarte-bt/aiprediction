"""
Backend-agnostic entity reader factory.

Exposes `get_entity_reader()` which returns a Postgres-backed reader.
Also re-exports the EntityNode and FilteredEntities dataclasses from
graph_domain so downstream modules have a stable import location.
"""

from __future__ import annotations

from typing import Any, List, Optional, Protocol, runtime_checkable

from ..utils.logger import get_logger
from .graph_domain import EntityNode, FilteredEntities

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
    """Return the Postgres-backed entity reader."""
    from .postgres_entity_reader import PostgresEntityReader
    _logger.debug("entity_reader factory -> PostgresEntityReader")
    return PostgresEntityReader()


def assert_graph_backend_ready() -> Optional[str]:
    """Return None if the graph backend is fully configured, or a
    user-facing error string explaining what is missing.
    """
    from ..config import Config
    if not Config.DATABASE_URL:
        return "DATABASE_URL 未配置 (required for the Postgres graph backend)"
    return None
