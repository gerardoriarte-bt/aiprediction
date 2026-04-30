"""
Postgres-backed GraphBackend implementation.

Phase 1: CRUD on graphs / nodes / edges / episodes with byte-identical
wire format to the legacy Zep flow (REGLAS_COMPLEMENTO §1).

Phase 2 (ingest pipeline) and Phase 4 (Report Agent tools) still raise
NotImplementedError; those land in dedicated PRs so the surface stays
small and reversible.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any, Callable, Dict, List, Optional

from ...utils.logger import get_logger
from . import connection
from .errors import GraphNotFoundError
from .repos import (
    EdgeRepository,
    EpisodeRepository,
    GraphRepository,
    NodeRepository,
)


_logger = get_logger("mirofish.graph.postgres")


ProgressCallback = Callable[[str, float], None]


# Graph IDs follow the same `mirofish_<hex16>` convention as the Zep flow
# so persisted project records stay valid when switching backends.
_GRAPH_ID_PREFIX = "mirofish_"


def _new_graph_id() -> str:
    return f"{_GRAPH_ID_PREFIX}{_uuid.uuid4().hex[:16]}"


def _format_dt(value) -> Optional[str]:
    if value is None:
        return None
    return str(value)


class PostgresGraphBackend:
    """Postgres + pgvector backend.

    For Phase 1 we cover graphs/nodes/edges CRUD and the read APIs that
    the frontend already calls (`get_graph_data`, `get_graph_statistics`).
    Ingest and search still raise NotImplementedError — see the relevant
    fases in docs/IMPLEMENTATION_ZEP_TO_POSTGRES.md.
    """

    name = "postgres"

    # ---- Connection helpers ---------------------------------------------

    def healthcheck(self) -> bool:
        return connection.healthcheck()

    def _conn(self):
        return connection.get_pool().connection()

    # ---- Build / CRUD ----------------------------------------------------

    def create_graph(self, name: str) -> str:
        graph_id = _new_graph_id()
        with self._conn() as conn:
            GraphRepository.insert(
                conn, graph_id, name=name, description="MiroFish Social Simulation Graph"
            )
            conn.commit()
        _logger.info("Postgres: created graph %s", graph_id)
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        with self._conn() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)
            updated = GraphRepository.update_ontology(conn, graph_id, ontology)
            conn.commit()
        _logger.info("Postgres: ontology set on %s (rows=%d)", graph_id, updated)

    def delete_graph(self, graph_id: str) -> None:
        with self._conn() as conn:
            removed = GraphRepository.delete(conn, graph_id)
            conn.commit()
        if removed == 0:
            raise GraphNotFoundError(graph_id)
        _logger.info("Postgres: deleted graph %s", graph_id)

    # ---- Read APIs (parity with frontend wire format) -------------------

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        with self._conn() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)
            nodes = NodeRepository.list_by_graph(conn, graph_id)
            edges = EdgeRepository.list_by_graph(conn, graph_id)

        nodes_data = [
            {
                # Wire format: keys & types must match the Zep flow so the
                # frontend (Step1GraphBuild.vue, etc.) doesn't need to know
                # which backend served the data.
                "uuid": str(n["node_id"]),
                "name": n["name"],
                "labels": list(n.get("labels") or []),
                "summary": n.get("summary") or "",
                "attributes": n.get("attributes") or {},
                "created_at": _format_dt(n.get("created_at")),
            }
            for n in nodes
        ]

        edges_data = [
            {
                "uuid": str(e["edge_id"]),
                "name": e.get("relation_name") or "",
                "fact": e.get("fact_text") or "",
                "fact_type": e.get("relation_name") or "",
                "source_node_uuid": str(e["source_node_id"]),
                "target_node_uuid": str(e["target_node_id"]),
                "source_node_name": e.get("source_node_name") or "",
                "target_node_name": e.get("target_node_name") or "",
                "attributes": e.get("attributes") or {},
                "created_at": _format_dt(e.get("created_at")),
                "valid_at": _format_dt(e.get("valid_at")),
                "invalid_at": _format_dt(e.get("invalid_at")),
                "expired_at": _format_dt(e.get("expired_at")),
                # Episode wiring lands in Phase 2; emit empty list to keep
                # the frontend contract intact.
                "episodes": [],
            }
            for e in edges
        ]

        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        with self._conn() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)
            total_nodes = NodeRepository.count_by_graph(conn, graph_id)
            total_edges = EdgeRepository.count_by_graph(conn, graph_id)
            entity_types = NodeRepository.label_counts(conn, graph_id)
            relation_types = EdgeRepository.relation_counts(conn, graph_id)

        return {
            "graph_id": graph_id,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "entity_types": entity_types,
            "relation_types": relation_types,
        }

    # ---- Phase 2: ingest pipeline (chunking + embeddings + materialise) -

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[str]:
        """Run the Postgres ingest pipeline (chunk + embed + LLM materialise).

        `batch_size` is accepted for protocol compatibility with the Zep
        flow; the actual embedding batch size is controlled inside the
        ingest service.
        """
        # Local import to keep boot-time cost low when running with Zep.
        from .repos import GraphRepository
        from ...services.graph_ingest import GraphIngestService

        with self._conn() as conn:
            row = GraphRepository.get(conn, graph_id)
        if not row:
            raise GraphNotFoundError(graph_id)

        ontology = row.get("ontology_json") or {}
        if isinstance(ontology, str):
            # Some psycopg config returns JSONB as text; tolerate it.
            import json as _json
            try:
                ontology = _json.loads(ontology)
            except Exception:
                ontology = {}

        service = GraphIngestService()
        result = service.ingest(
            conn_factory=self._conn,
            graph_id=graph_id,
            chunks=chunks,
            ontology=ontology,
            progress_callback=progress_callback,
        )
        _logger.info(
            "Postgres ingest done for %s: %s",
            graph_id,
            result.get("stats"),
        )
        return result.get("episode_uuids", [])

    def wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        # Postgres ingest is synchronous — episodes are already marked
        # 'processed' by the time add_text_batches returns. We keep this
        # method as a no-op so the protocol contract holds and callers
        # written for Zep don't deadlock.
        if progress_callback is not None:
            try:
                progress_callback("episodes already processed", 1.0)
            except Exception:
                _logger.exception("progress callback raised; continuing")
        return None

    # ---- Phase 4: Report Agent retrieval --------------------------------

    def search_graph(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Phase 4 — semantic search over graph_chunks/edges with pgvector "
            "lands when the Report Agent tools port to Postgres."
        )

    # ---- Convenience for tests / Phase 1 verification --------------------

    def upsert_node(
        self,
        graph_id: str,
        name: str,
        labels: Optional[List[str]] = None,
        summary: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Helper used by Phase 1 smoke tests and (later) the ingest pipeline."""
        with self._conn() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)
            node_id = NodeRepository.upsert(
                conn,
                graph_id=graph_id,
                name=name,
                labels=labels,
                summary=summary,
                attributes=attributes,
            )
            conn.commit()
            return node_id

    def upsert_edge(
        self,
        graph_id: str,
        source_name: str,
        target_name: str,
        relation_name: str,
        fact_text: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self._conn() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)
            src = NodeRepository.get_id_by_name(conn, graph_id, source_name)
            tgt = NodeRepository.get_id_by_name(conn, graph_id, target_name)
            if src is None or tgt is None:
                raise GraphNotFoundError(
                    f"Source/target node missing in {graph_id}: "
                    f"src={source_name!r}, tgt={target_name!r}"
                )
            edge_id = EdgeRepository.upsert(
                conn,
                graph_id=graph_id,
                source_node_id=src,
                target_node_id=tgt,
                relation_name=relation_name,
                fact_text=fact_text,
                attributes=attributes,
            )
            conn.commit()
            return edge_id

    def create_episode(
        self,
        graph_id: str,
        external_uuid: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self._conn() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)
            episode_id = EpisodeRepository.insert(
                conn,
                graph_id=graph_id,
                external_uuid=external_uuid,
                source=source,
                metadata=metadata,
            )
            conn.commit()
            return episode_id
