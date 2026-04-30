"""
Postgres entity reader — paridad funcional con ZepEntityReader (Fase 3).

Reusa EntityNode/FilteredEntities del módulo zep_entity_reader para que
los call sites (api/simulation.py, oasis_profile_generator.py) sigan
viendo los mismos tipos. La forma del JSON serializado se mantiene
byte-identical, así el frontend no nota la diferencia.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from ..repositories.graph import connection
from ..repositories.graph.errors import GraphNotFoundError
from ..repositories.graph.repos import (
    EdgeRepository,
    GraphRepository,
    NodeRepository,
)
from ..utils.logger import get_logger
# Reuse the dataclasses so type identity holds across backends.
from .zep_entity_reader import EntityNode, FilteredEntities


logger = get_logger("mirofish.postgres_entity_reader")


def _node_row_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Project a NodeRepository row to the legacy wire-format dict."""
    return {
        "uuid": str(row["node_id"]),
        "name": row.get("name") or "",
        "labels": list(row.get("labels") or []),
        "summary": row.get("summary") or "",
        "attributes": row.get("attributes") or {},
    }


def _edge_row_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "uuid": str(row["edge_id"]),
        "name": row.get("relation_name") or "",
        "fact": row.get("fact_text") or "",
        "source_node_uuid": str(row["source_node_id"]),
        "target_node_uuid": str(row["target_node_id"]),
        "attributes": row.get("attributes") or {},
    }


class PostgresEntityReader:
    """Misma API pública que ZepEntityReader, contra Postgres."""

    def __init__(self) -> None:
        # Touch the pool eagerly so misconfiguration surfaces here, not deep
        # inside a request handler.
        connection.get_pool()

    # ---- Raw fetchers ----------------------------------------------------

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Postgres: fetching all nodes for {graph_id}")
        with connection.get_pool().connection() as conn:
            rows = NodeRepository.list_by_graph(conn, graph_id)
        out = [_node_row_to_dict(r) for r in rows]
        logger.info(f"Postgres: fetched {len(out)} nodes")
        return out

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Postgres: fetching all edges for {graph_id}")
        with connection.get_pool().connection() as conn:
            rows = EdgeRepository.list_by_graph(conn, graph_id)
        out = [_edge_row_to_dict(r) for r in rows]
        logger.info(f"Postgres: fetched {len(out)} edges")
        return out

    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        """Best-effort: list edges touching a node id within the only graph
        that contains it. Postgres edges already include FKs to nodes, so
        we don't need a separate API."""
        try:
            node_id = int(node_uuid)
        except (TypeError, ValueError):
            return []
        with connection.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT graph_id FROM graph_nodes WHERE node_id = %s LIMIT 1;
                    """,
                    (node_id,),
                )
                row = cur.fetchone()
                if not row:
                    return []
                graph_id = row[0]
                cur.execute(
                    """
                    SELECT e.edge_id, e.relation_name, e.fact_text,
                           e.source_node_id, e.target_node_id, e.attributes
                    FROM graph_edges e
                    WHERE e.graph_id = %s
                      AND (e.source_node_id = %s OR e.target_node_id = %s);
                    """,
                    (graph_id, node_id, node_id),
                )
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
        edges_data: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(zip(cols, row))
            edges_data.append(
                {
                    "uuid": str(data["edge_id"]),
                    "name": data.get("relation_name") or "",
                    "fact": data.get("fact_text") or "",
                    "source_node_uuid": str(data["source_node_id"]),
                    "target_node_uuid": str(data["target_node_id"]),
                    "attributes": data.get("attributes") or {},
                }
            )
        return edges_data

    # ---- Filtering -------------------------------------------------------

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        """Selection rule mirrors ZepEntityReader exactly:

        - drop nodes whose only labels are 'Entity'/'Node';
        - if `defined_entity_types` is given, keep only nodes that match;
        - optionally attach related edges + neighbour nodes.
        """
        logger.info(f"Postgres: filtering entities in {graph_id}")
        with connection.get_pool().connection() as conn:
            if not GraphRepository.exists(conn, graph_id):
                raise GraphNotFoundError(graph_id)
            node_rows = NodeRepository.list_by_graph(conn, graph_id)
            edge_rows = (
                EdgeRepository.list_by_graph(conn, graph_id) if enrich_with_edges else []
            )

        all_nodes = [_node_row_to_dict(r) for r in node_rows]
        total_count = len(all_nodes)

        node_map = {n["uuid"]: n for n in all_nodes}

        filtered_entities: List[EntityNode] = []
        entity_types_found: Set[str] = set()

        # Pre-index edges by endpoint to keep enrichment O(N+E).
        edges_by_node: Dict[str, List[Dict[str, Any]]] = {}
        if enrich_with_edges:
            for er in edge_rows:
                src_uuid = str(er["source_node_id"])
                tgt_uuid = str(er["target_node_id"])
                edge_dict_out = {
                    "name": er.get("relation_name") or "",
                    "fact": er.get("fact_text") or "",
                    "source_node_uuid": src_uuid,
                    "target_node_uuid": tgt_uuid,
                }
                edges_by_node.setdefault(src_uuid, []).append(
                    {"direction": "outgoing", **edge_dict_out}
                )
                edges_by_node.setdefault(tgt_uuid, []).append(
                    {"direction": "incoming", **edge_dict_out}
                )

        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [lbl for lbl in labels if lbl not in ("Entity", "Node")]
            if not custom_labels:
                continue

            if defined_entity_types:
                matching = [lbl for lbl in custom_labels if lbl in defined_entity_types]
                if not matching:
                    continue
                entity_type = matching[0]
            else:
                entity_type = custom_labels[0]
            entity_types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )

            if enrich_with_edges:
                related_edges_raw = edges_by_node.get(node["uuid"], [])
                # Reshape so the legacy wire format is preserved (incoming
                # carries `source_node_uuid`, outgoing carries
                # `target_node_uuid`; we keep both in the dict and let the
                # consumer pick).
                related_edges: List[Dict[str, Any]] = []
                related_node_uuids: Set[str] = set()
                for er in related_edges_raw:
                    if er["direction"] == "outgoing":
                        related_edges.append(
                            {
                                "direction": "outgoing",
                                "edge_name": er["name"],
                                "fact": er["fact"],
                                "target_node_uuid": er["target_node_uuid"],
                            }
                        )
                        related_node_uuids.add(er["target_node_uuid"])
                    else:
                        related_edges.append(
                            {
                                "direction": "incoming",
                                "edge_name": er["name"],
                                "fact": er["fact"],
                                "source_node_uuid": er["source_node_uuid"],
                            }
                        )
                        related_node_uuids.add(er["source_node_uuid"])
                entity.related_edges = related_edges

                related_nodes: List[Dict[str, Any]] = []
                for related_uuid in related_node_uuids:
                    rn = node_map.get(related_uuid)
                    if rn is not None:
                        related_nodes.append(
                            {
                                "uuid": rn["uuid"],
                                "name": rn["name"],
                                "labels": rn["labels"],
                                "summary": rn.get("summary", ""),
                            }
                        )
                entity.related_nodes = related_nodes

            filtered_entities.append(entity)

        logger.info(
            "Postgres: filtered %d/%d nodes, types=%s",
            len(filtered_entities),
            total_count,
            entity_types_found,
        )
        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    # ---- Single entity / by-type ----------------------------------------

    def get_entity_with_context(
        self, graph_id: str, entity_uuid: str
    ) -> Optional[EntityNode]:
        try:
            node_id = int(entity_uuid)
        except (TypeError, ValueError):
            return None

        with connection.get_pool().connection() as conn:
            if not GraphRepository.exists(conn, graph_id):
                return None
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, name, labels, summary, attributes
                    FROM graph_nodes
                    WHERE graph_id = %s AND node_id = %s;
                    """,
                    (graph_id, node_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                node = dict(zip(cols, row))

            edge_rows = EdgeRepository.list_by_graph(conn, graph_id)
            node_rows = NodeRepository.list_by_graph(conn, graph_id)

        node_map = {str(r["node_id"]): _node_row_to_dict(r) for r in node_rows}
        related_edges: List[Dict[str, Any]] = []
        related_node_uuids: Set[str] = set()
        target_uuid = str(node_id)

        for er in edge_rows:
            src_uuid = str(er["source_node_id"])
            tgt_uuid = str(er["target_node_id"])
            if src_uuid == target_uuid:
                related_edges.append(
                    {
                        "direction": "outgoing",
                        "edge_name": er.get("relation_name") or "",
                        "fact": er.get("fact_text") or "",
                        "target_node_uuid": tgt_uuid,
                    }
                )
                related_node_uuids.add(tgt_uuid)
            elif tgt_uuid == target_uuid:
                related_edges.append(
                    {
                        "direction": "incoming",
                        "edge_name": er.get("relation_name") or "",
                        "fact": er.get("fact_text") or "",
                        "source_node_uuid": src_uuid,
                    }
                )
                related_node_uuids.add(src_uuid)

        related_nodes = []
        for related_uuid in related_node_uuids:
            rn = node_map.get(related_uuid)
            if rn is not None:
                related_nodes.append(
                    {
                        "uuid": rn["uuid"],
                        "name": rn["name"],
                        "labels": rn["labels"],
                        "summary": rn.get("summary", ""),
                    }
                )

        return EntityNode(
            uuid=str(node["node_id"]),
            name=node.get("name") or "",
            labels=list(node.get("labels") or []),
            summary=node.get("summary") or "",
            attributes=node.get("attributes") or {},
            related_edges=related_edges,
            related_nodes=related_nodes,
        )

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = True,
    ) -> List[EntityNode]:
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges,
        )
        return result.entities
