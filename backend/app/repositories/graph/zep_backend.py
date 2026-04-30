"""
Zep-backed GraphBackend implementation.

Thin wrapper that delegates to the existing services without changing
their behaviour. Used while GRAPH_BACKEND=zep (default) to keep the
current flow byte-identical (REGLAS_COMPLEMENTO §1).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ...services.graph_builder import GraphBuilderService
from ...services.zep_tools import ZepToolsService


ProgressCallback = Callable[[str, float], None]


class ZepGraphBackend:
    """Adapter over GraphBuilderService + ZepToolsService.

    Note: GraphBuilderService and ZepToolsService manage their own Zep
    clients today. This wrapper does not own a connection itself; it only
    forwards calls so existing semantics are preserved.
    """

    name = "zep"

    def __init__(self) -> None:
        self._builder: Optional[GraphBuilderService] = None
        self._tools: Optional[ZepToolsService] = None

    # Lazy accessors keep import cost low for callers who never use them.
    @property
    def builder(self) -> GraphBuilderService:
        if self._builder is None:
            self._builder = GraphBuilderService()
        return self._builder

    @property
    def tools(self) -> ZepToolsService:
        if self._tools is None:
            self._tools = ZepToolsService()
        return self._tools

    # ---- Build / ingest --------------------------------------------------

    def create_graph(self, name: str) -> str:
        return self.builder.create_graph(name)

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        self.builder.set_ontology(graph_id, ontology)

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[str]:
        return self.builder.add_text_batches(
            graph_id,
            chunks,
            batch_size=batch_size,
            progress_callback=progress_callback,
        )

    def wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        # The current implementation lives as a private helper on the
        # builder. We expose it here behind the protocol without renaming
        # the original method to avoid touching graph_builder.py.
        self.builder._wait_for_episodes(episode_uuids, progress_callback)

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        return self.builder.get_graph_data(graph_id)

    def delete_graph(self, graph_id: str) -> None:
        self.builder.delete_graph(graph_id)

    # ---- Retrieval -------------------------------------------------------

    def search_graph(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        result = self.tools.search_graph(graph_id=graph_id, query=query, limit=limit)
        return result.to_dict()

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        return self.tools.get_graph_statistics(graph_id)
