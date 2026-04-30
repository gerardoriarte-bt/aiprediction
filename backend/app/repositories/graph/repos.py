"""
SQL repositories for the Postgres graph backend (Phase 1).

Each repository owns a single table. They expose typed Python methods and
hide all SQL details from the application layer (REGLAS_COMPLEMENTO §2 +
the project rule "no SQL in services" from IMPLEMENTATION_ZEP_TO_POSTGRES).

All methods accept a psycopg connection so the caller controls
transactions (begin/commit). The PostgresGraphBackend orchestrates them.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(cursor, row) -> Dict[str, Any]:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# graphs
# ---------------------------------------------------------------------------


class GraphRepository:
    @staticmethod
    def insert(conn, graph_id: str, name: str, description: Optional[str] = None) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO graphs (graph_id, name, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (graph_id) DO NOTHING;
                """,
                (graph_id, name, description),
            )

    @staticmethod
    def exists(conn, graph_id: str) -> bool:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM graphs WHERE graph_id = %s LIMIT 1;", (graph_id,))
            return cur.fetchone() is not None

    @staticmethod
    def get(conn, graph_id: str) -> Optional[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT graph_id, name, description, ontology_json, metadata,
                       created_at, updated_at
                FROM graphs WHERE graph_id = %s;
                """,
                (graph_id,),
            )
            row = cur.fetchone()
            return _row_to_dict(cur, row) if row else None

    @staticmethod
    def update_ontology(conn, graph_id: str, ontology: Dict[str, Any]) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE graphs
                SET ontology_json = %s::jsonb, updated_at = NOW()
                WHERE graph_id = %s;
                """,
                (json.dumps(ontology), graph_id),
            )
            return cur.rowcount

    @staticmethod
    def delete(conn, graph_id: str) -> int:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM graphs WHERE graph_id = %s;", (graph_id,))
            return cur.rowcount


# ---------------------------------------------------------------------------
# graph_nodes
# ---------------------------------------------------------------------------


class NodeRepository:
    @staticmethod
    def upsert(
        conn,
        graph_id: str,
        name: str,
        labels: Optional[List[str]] = None,
        summary: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        zep_uuid: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> int:
        """Insert or update a node by (graph_id, name). Returns node_id.

        `embedding` is optional; when provided it is stored alongside the
        node so semantic search can rank against entity-level vectors.
        """
        emb_lit = _format_vector(embedding) if embedding is not None else None
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO graph_nodes
                    (graph_id, name, labels, summary, attributes, zep_uuid, embedding)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s::vector)
                ON CONFLICT (graph_id, name) DO UPDATE SET
                    labels     = EXCLUDED.labels,
                    summary    = COALESCE(EXCLUDED.summary, graph_nodes.summary),
                    attributes = EXCLUDED.attributes,
                    zep_uuid   = COALESCE(EXCLUDED.zep_uuid, graph_nodes.zep_uuid),
                    embedding  = COALESCE(EXCLUDED.embedding, graph_nodes.embedding),
                    updated_at = NOW()
                RETURNING node_id;
                """,
                (
                    graph_id,
                    name,
                    labels or [],
                    summary,
                    json.dumps(attributes or {}),
                    zep_uuid,
                    emb_lit,
                ),
            )
            return cur.fetchone()[0]

    @staticmethod
    def list_by_graph(conn, graph_id: str) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT node_id, graph_id, name, labels, summary, attributes,
                       zep_uuid, created_at
                FROM graph_nodes
                WHERE graph_id = %s
                ORDER BY node_id;
                """,
                (graph_id,),
            )
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]

    @staticmethod
    def get_id_by_name(conn, graph_id: str, name: str) -> Optional[int]:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT node_id FROM graph_nodes WHERE graph_id = %s AND name = %s;",
                (graph_id, name),
            )
            row = cur.fetchone()
            return row[0] if row else None

    @staticmethod
    def count_by_graph(conn, graph_id: str) -> int:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM graph_nodes WHERE graph_id = %s;",
                (graph_id,),
            )
            return int(cur.fetchone()[0])

    @staticmethod
    def label_counts(conn, graph_id: str) -> Dict[str, int]:
        """Return label -> count, mirroring ZepToolsService.get_graph_statistics
        (excluding the structural labels 'Entity' and 'Node')."""
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT label, COUNT(*)::int
                FROM (
                    SELECT UNNEST(labels) AS label
                    FROM graph_nodes
                    WHERE graph_id = %s
                ) sub
                WHERE label NOT IN ('Entity', 'Node')
                GROUP BY label;
                """,
                (graph_id,),
            )
            return {row[0]: int(row[1]) for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# graph_edges
# ---------------------------------------------------------------------------


class EdgeRepository:
    @staticmethod
    def upsert(
        conn,
        graph_id: str,
        source_node_id: int,
        target_node_id: int,
        relation_name: str,
        fact_text: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        valid_at=None,
        invalid_at=None,
        expired_at=None,
        zep_uuid: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> int:
        """Insert a new edge (no de-dup constraint by design — multiple facts
        between the same pair of entities are valid).

        `embedding` is optional; when provided it powers semantic search
        over fact text. The migration creates the column either way.
        """
        emb_lit = _format_vector(embedding) if embedding is not None else None
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO graph_edges
                    (graph_id, source_node_id, target_node_id, relation_name,
                     fact_text, attributes, valid_at, invalid_at, expired_at,
                     zep_uuid, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::vector)
                RETURNING edge_id;
                """,
                (
                    graph_id,
                    source_node_id,
                    target_node_id,
                    relation_name,
                    fact_text,
                    json.dumps(attributes or {}),
                    valid_at,
                    invalid_at,
                    expired_at,
                    zep_uuid,
                    emb_lit,
                ),
            )
            return cur.fetchone()[0]

    @staticmethod
    def list_by_graph(conn, graph_id: str) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.edge_id, e.graph_id, e.source_node_id, e.target_node_id,
                       e.relation_name, e.fact_text, e.attributes,
                       e.valid_at, e.invalid_at, e.expired_at, e.zep_uuid,
                       e.created_at,
                       sn.name AS source_node_name,
                       tn.name AS target_node_name
                FROM graph_edges e
                JOIN graph_nodes sn ON sn.node_id = e.source_node_id
                JOIN graph_nodes tn ON tn.node_id = e.target_node_id
                WHERE e.graph_id = %s
                ORDER BY e.edge_id;
                """,
                (graph_id,),
            )
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]

    @staticmethod
    def count_by_graph(conn, graph_id: str) -> int:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM graph_edges WHERE graph_id = %s;",
                (graph_id,),
            )
            return int(cur.fetchone()[0])

    @staticmethod
    def relation_counts(conn, graph_id: str) -> Dict[str, int]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT relation_name, COUNT(*)::int
                FROM graph_edges
                WHERE graph_id = %s
                GROUP BY relation_name;
                """,
                (graph_id,),
            )
            return {row[0]: int(row[1]) for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# graph_chunks
# ---------------------------------------------------------------------------


def _format_vector(values: List[float]) -> str:
    """Render a Python list as the pgvector textual literal '[v1,v2,...]'."""
    if values is None:
        return None  # type: ignore[return-value]
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


class ChunkRepository:
    @staticmethod
    def insert_batch(
        conn,
        graph_id: str,
        episode_id: Optional[int],
        items: Iterable[Dict[str, Any]],
    ) -> List[int]:
        """Insert a batch of chunks. Each item: {text, embedding, text_hash?, metadata?}.

        Returns the inserted chunk_ids in input order.
        """
        items = list(items)
        if not items:
            return []
        ids: List[int] = []
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
                    """
                    INSERT INTO graph_chunks
                        (graph_id, episode_id, text, text_hash, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s::vector, %s::jsonb)
                    RETURNING chunk_id;
                    """,
                    (
                        graph_id,
                        episode_id,
                        item["text"],
                        item.get("text_hash"),
                        _format_vector(item["embedding"]),
                        json.dumps(item.get("metadata") or {}),
                    ),
                )
                ids.append(cur.fetchone()[0])
        return ids

    @staticmethod
    def count_by_graph(conn, graph_id: str) -> int:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM graph_chunks WHERE graph_id = %s;",
                (graph_id,),
            )
            return int(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# graph_episodes
# ---------------------------------------------------------------------------


class EpisodeRepository:
    @staticmethod
    def insert(
        conn,
        graph_id: str,
        external_uuid: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "pending",
    ) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO graph_episodes
                    (graph_id, external_uuid, source, status, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING episode_id;
                """,
                (
                    graph_id,
                    external_uuid,
                    source,
                    status,
                    json.dumps(metadata or {}),
                ),
            )
            return cur.fetchone()[0]

    @staticmethod
    def mark_processed(conn, episode_id: int) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE graph_episodes
                SET status = 'processed', processed_at = NOW()
                WHERE episode_id = %s;
                """,
                (episode_id,),
            )
            return cur.rowcount

    @staticmethod
    def list_by_graph(conn, graph_id: str) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT episode_id, graph_id, external_uuid, source, status,
                       metadata, created_at, processed_at
                FROM graph_episodes
                WHERE graph_id = %s
                ORDER BY episode_id;
                """,
                (graph_id,),
            )
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]
