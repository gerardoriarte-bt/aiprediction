"""
Graph tools factory — always returns the Postgres-backed tools service.
"""

from __future__ import annotations

from ..utils.logger import get_logger

__all__ = ["get_graph_tools"]


_logger = get_logger("mirofish.graph_tools.factory")


def get_graph_tools():
    """Return the Postgres-backed tools service."""
    from .postgres_tools import PostgresToolsService
    _logger.debug("graph_tools factory -> PostgresToolsService")
    return PostgresToolsService()
