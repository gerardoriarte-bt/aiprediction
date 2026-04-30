"""
GraphBackend protocol — contract that both Zep and Postgres backends honour.

The shape mirrors the public surface that current services expose
(GraphBuilderService + ZepToolsService + ZepEntityReader). For Phase 0 we
declare the *minimum* set required to start porting features behind the
flag without breaking the existing flow.

We intentionally keep return types as plain dicts/lists so the wire format
stays identical regardless of backend (REGLAS_COMPLEMENTO §1, §3).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


ProgressCallback = Callable[[str, float], None]
"""Signature aligned with services/graph_builder.py: (message, ratio_0_to_1)."""


@runtime_checkable
class GraphBackend(Protocol):
    """Backend-agnostic API for graph build, ingest and retrieval.

    Phase 0: only declare. Implementations land in:
      - ZepGraphBackend: thin wrapper that delegates to existing services.
      - PostgresGraphBackend: filled in across Fases 1-4.
    """

    name: str  # 'zep' | 'postgres'

    # ---- Build / ingest --------------------------------------------------

    def create_graph(self, name: str) -> str:
        """Create a graph and return its graph_id."""
        ...

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        ...

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[str]:
        """Ingest text chunks. Returns episode identifiers."""
        ...

    def wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        ...

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Return {'nodes': [...], 'edges': [...], 'node_count': int, 'edge_count': int}."""
        ...

    def delete_graph(self, graph_id: str) -> None:
        ...

    # ---- Retrieval (Report Agent tools) ----------------------------------

    def search_graph(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Top-k semantic search. Wire format matches ZepToolsService.SearchResult.to_dict()."""
        ...

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        ...
