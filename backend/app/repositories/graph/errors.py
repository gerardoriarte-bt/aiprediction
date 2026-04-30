"""Domain errors for the graph repository layer."""

from __future__ import annotations


class RepositoryError(Exception):
    """Generic repository failure (unexpected SQL/connection error)."""


class GraphNotFoundError(RepositoryError):
    """Requested graph_id does not exist in the database."""

    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        super().__init__(f"Graph not found: {graph_id}")


class NodeNotFoundError(RepositoryError):
    """Requested node was not found in the given graph."""

    def __init__(self, graph_id: str, identifier):
        self.graph_id = graph_id
        self.identifier = identifier
        super().__init__(f"Node not found in {graph_id}: {identifier}")


class IntegrityError(RepositoryError):
    """Constraint violation (FK, UNIQUE, NOT NULL...)."""
