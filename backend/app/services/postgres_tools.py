"""
PostgresToolsService — Report Agent tools running against Postgres+pgvector.

Phase 4 of the Zep -> Postgres migration. Mirrors the public surface of
ZepToolsService so report_agent.py can swap implementations behind the
GRAPH_BACKEND flag without touching prompts or downstream parsing.

The dataclasses (SearchResult, NodeInfo, EdgeInfo, InsightForgeResult,
PanoramaResult) are imported from zep_tools and reused unchanged so
to_text() output stays byte-identical to the legacy flow.

Out of scope for this iteration:
- interview_agents: depends on OASIS profiles (Phase 6). Falls through to
  the legacy ZepToolsService when needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..repositories.graph import connection
from ..repositories.graph.errors import GraphNotFoundError
from ..repositories.graph.repos import (
    EdgeRepository,
    GraphRepository,
    NodeRepository,
)
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .embeddings import EmbeddingError, get_embedding_client
from .graph_metrics import time_tool
from .zep_tools import (
    EdgeInfo,
    InsightForgeResult,
    NodeInfo,
    PanoramaResult,
    SearchResult,
)


logger = get_logger("mirofish.postgres_tools")


# ---------------------------------------------------------------------------
# Mapping helpers (Postgres rows -> shared dataclasses)
# ---------------------------------------------------------------------------


def _node_row_to_info(row: Dict[str, Any]) -> NodeInfo:
    return NodeInfo(
        uuid=str(row["node_id"]),
        name=row.get("name") or "",
        labels=list(row.get("labels") or []),
        summary=row.get("summary") or "",
        attributes=row.get("attributes") or {},
    )


def _edge_row_to_info(row: Dict[str, Any]) -> EdgeInfo:
    def _fmt(value):
        if value is None:
            return None
        return str(value)

    return EdgeInfo(
        uuid=str(row["edge_id"]),
        name=row.get("relation_name") or "",
        fact=row.get("fact_text") or "",
        source_node_uuid=str(row["source_node_id"]),
        target_node_uuid=str(row["target_node_id"]),
        source_node_name=row.get("source_node_name"),
        target_node_name=row.get("target_node_name"),
        created_at=_fmt(row.get("created_at")),
        valid_at=_fmt(row.get("valid_at")),
        invalid_at=_fmt(row.get("invalid_at")),
        expired_at=_fmt(row.get("expired_at")),
    )


def _vec_literal(values: List[float]) -> str:
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PostgresToolsService:
    """Drop-in replacement for ZepToolsService when GRAPH_BACKEND=postgres."""

    def __init__(self) -> None:
        self._llm: Optional[LLMClient] = None
        self._embed = None
        connection.get_pool()  # surface misconfig early

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def _embedding_client(self):
        if self._embed is None:
            self._embed = get_embedding_client()
        return self._embed

    # ---- Search primitives ----------------------------------------------

    @time_tool("postgres", "search_graph")
    def search_graph(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
    ) -> SearchResult:
        """Top-k semantic search using pgvector cosine distance over edges
        (preferred, because Zep's facts come from edges) and chunks (fallback)."""
        logger.info(f"Postgres search_graph: graph={graph_id} q={query!r} limit={limit}")
        try:
            qvec = self._embedding_client().embed(query)
        except EmbeddingError as e:
            logger.warning(f"embedding failed for search query: {e}")
            return SearchResult(facts=[], edges=[], nodes=[], query=query, total_count=0)

        qvec_lit = _vec_literal(qvec)
        edges_rows: List[Dict[str, Any]] = []
        nodes_rows: List[Dict[str, Any]] = []

        with connection.get_pool().connection() as conn:
            with conn.cursor() as cur:
                # Edges first (facts live here). Use cosine distance (<=>).
                cur.execute(
                    """
                    SELECT e.edge_id, e.relation_name, e.fact_text,
                           e.source_node_id, e.target_node_id,
                           e.attributes, e.created_at, e.valid_at,
                           e.invalid_at, e.expired_at,
                           sn.name AS source_node_name,
                           tn.name AS target_node_name,
                           e.embedding <=> %s::vector AS distance
                    FROM graph_edges e
                    JOIN graph_nodes sn ON sn.node_id = e.source_node_id
                    JOIN graph_nodes tn ON tn.node_id = e.target_node_id
                    WHERE e.graph_id = %s AND e.embedding IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT %s;
                    """,
                    (qvec_lit, graph_id, limit),
                )
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    edges_rows = [dict(zip(cols, r)) for r in cur.fetchall()]

                # Nodes (semantic match by name/summary embedding).
                cur.execute(
                    """
                    SELECT node_id, name, labels, summary, attributes,
                           embedding <=> %s::vector AS distance
                    FROM graph_nodes
                    WHERE graph_id = %s AND embedding IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT %s;
                    """,
                    (qvec_lit, graph_id, limit),
                )
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    nodes_rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        edges_info = [_edge_row_to_info(r) for r in edges_rows]
        nodes_info = [_node_row_to_info(r) for r in nodes_rows]

        # Build the legacy fact list: prefer edge fact_text; if a node has no
        # adjacent fact, fall back to its summary so the LLM still sees signal.
        facts: List[str] = []
        for e in edges_info:
            if e.fact:
                facts.append(e.fact)
        if len(facts) < limit:
            for n in nodes_info:
                if n.summary and n.summary not in facts:
                    facts.append(n.summary)
                if len(facts) >= limit:
                    break

        return SearchResult(
            facts=facts[:limit],
            edges=[e.to_dict() for e in edges_info],
            nodes=[n.to_dict() for n in nodes_info],
            query=query,
            total_count=len(facts),
        )

    @time_tool("postgres", "quick_search")
    def quick_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 5,
    ) -> SearchResult:
        return self.search_graph(graph_id=graph_id, query=query, limit=limit)

    # ---- Listing / detail ------------------------------------------------

    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        with connection.get_pool().connection() as conn:
            rows = NodeRepository.list_by_graph(conn, graph_id)
        return [_node_row_to_info(r) for r in rows]

    def get_all_edges(
        self,
        graph_id: str,
        include_temporal: bool = True,
    ) -> List[EdgeInfo]:
        with connection.get_pool().connection() as conn:
            rows = EdgeRepository.list_by_graph(conn, graph_id)
        edges = [_edge_row_to_info(r) for r in rows]
        if not include_temporal:
            for e in edges:
                e.valid_at = None
                e.invalid_at = None
                e.expired_at = None
        return edges

    def get_node_detail(self, node_uuid: str) -> Optional[NodeInfo]:
        try:
            node_id = int(node_uuid)
        except (TypeError, ValueError):
            return None
        with connection.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, graph_id, name, labels, summary, attributes
                    FROM graph_nodes WHERE node_id = %s;
                    """,
                    (node_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                return _node_row_to_info(dict(zip(cols, row)))

    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[EdgeInfo]:
        try:
            node_id = int(node_uuid)
        except (TypeError, ValueError):
            return []
        with connection.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT e.edge_id, e.graph_id, e.source_node_id,
                           e.target_node_id, e.relation_name, e.fact_text,
                           e.attributes, e.created_at, e.valid_at,
                           e.invalid_at, e.expired_at,
                           sn.name AS source_node_name,
                           tn.name AS target_node_name
                    FROM graph_edges e
                    JOIN graph_nodes sn ON sn.node_id = e.source_node_id
                    JOIN graph_nodes tn ON tn.node_id = e.target_node_id
                    WHERE e.graph_id = %s
                      AND (e.source_node_id = %s OR e.target_node_id = %s)
                    ORDER BY e.edge_id;
                    """,
                    (graph_id, node_id, node_id),
                )
                cols = [d[0] for d in cur.description]
                return [_edge_row_to_info(dict(zip(cols, r))) for r in cur.fetchall()]

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        limit: int = 50,
    ) -> List[NodeInfo]:
        with connection.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, name, labels, summary, attributes
                    FROM graph_nodes
                    WHERE graph_id = %s AND %s = ANY(labels)
                    ORDER BY node_id
                    LIMIT %s;
                    """,
                    (graph_id, entity_type, limit),
                )
                cols = [d[0] for d in cur.description]
                return [_node_row_to_info(dict(zip(cols, r))) for r in cur.fetchall()]

    @time_tool("postgres", "get_entity_summary")
    def get_entity_summary(
        self,
        graph_id: str,
        entity_name: str,
    ) -> Dict[str, Any]:
        # Find the entity by exact (case-insensitive) name first.
        with connection.get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, name, labels, summary, attributes
                    FROM graph_nodes
                    WHERE graph_id = %s AND LOWER(name) = LOWER(%s)
                    LIMIT 1;
                    """,
                    (graph_id, entity_name),
                )
                row = cur.fetchone()
                cols = [d[0] for d in cur.description] if cur.description else []
                entity_node = (
                    _node_row_to_info(dict(zip(cols, row))) if row else None
                )

        related_edges: List[EdgeInfo] = []
        if entity_node is not None:
            related_edges = self.get_node_edges(graph_id, entity_node.uuid)

        # Always pair with semantic facts (paridad con Zep).
        search = self.search_graph(graph_id=graph_id, query=entity_name, limit=20)

        return {
            "entity_name": entity_name,
            "entity_info": entity_node.to_dict() if entity_node else None,
            "related_facts": search.facts,
            "related_edges": [e.to_dict() for e in related_edges],
            "total_relations": len(related_edges),
        }

    # ---- Stats / context -------------------------------------------------

    @time_tool("postgres", "get_graph_statistics")
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        # Mirrors PostgresGraphBackend.get_graph_statistics but kept self-
        # contained so the agent doesn't need a backend handle.
        with connection.get_pool().connection() as conn:
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

    @time_tool("postgres", "get_simulation_context")
    def get_simulation_context(
        self,
        graph_id: str,
        simulation_requirement: str,
        limit: int = 30,
    ) -> Dict[str, Any]:
        search = self.search_graph(
            graph_id=graph_id, query=simulation_requirement, limit=limit
        )
        stats = self.get_graph_statistics(graph_id)
        all_nodes = self.get_all_nodes(graph_id)

        entities: List[Dict[str, Any]] = []
        for n in all_nodes:
            custom_labels = [lbl for lbl in n.labels if lbl not in ("Entity", "Node")]
            if custom_labels:
                entities.append(
                    {"name": n.name, "type": custom_labels[0], "summary": n.summary}
                )

        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],
            "total_entities": len(entities),
        }

    # ---- Panorama (active vs historical) --------------------------------

    @time_tool("postgres", "panorama_search")
    def panorama_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 30,
    ) -> PanoramaResult:
        # Pull a wider semantic window, then split by validity timestamps.
        search = self.search_graph(graph_id=graph_id, query=query, limit=limit)
        all_nodes = self.get_all_nodes(graph_id)
        all_edges = self.get_all_edges(graph_id, include_temporal=True)

        now = datetime.now(timezone.utc).isoformat()
        active_facts: List[str] = []
        historical_facts: List[str] = []
        for e in all_edges:
            if e.is_expired or e.is_invalid:
                if e.fact:
                    historical_facts.append(e.fact)
            else:
                if e.fact:
                    active_facts.append(e.fact)

        return PanoramaResult(
            query=query,
            all_nodes=all_nodes,
            all_edges=all_edges,
            active_facts=active_facts,
            historical_facts=historical_facts,
            total_nodes=len(all_nodes),
            total_edges=len(all_edges),
            active_count=len(active_facts),
            historical_count=len(historical_facts),
        )

    # ---- InsightForge (decompose -> search -> aggregate) ---------------

    @time_tool("postgres", "insight_forge")
    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5,
    ) -> InsightForgeResult:
        sub_queries = self._generate_sub_queries(
            query, simulation_requirement, report_context, max_sub_queries
        )

        # Each sub-query: semantic search, dedupe facts.
        all_facts: List[str] = []
        seen_facts = set()
        entity_insights: Dict[str, Dict[str, Any]] = {}
        relationship_chains: List[str] = []

        # Always include the main query.
        queries_to_run = [query] + [q for q in sub_queries if q and q != query]
        for q in queries_to_run[: max_sub_queries + 1]:
            try:
                sr = self.search_graph(graph_id=graph_id, query=q, limit=12)
            except Exception as e:
                logger.warning(f"insight_forge sub-search failed q={q!r}: {e}")
                continue
            for f in sr.facts:
                if f not in seen_facts:
                    seen_facts.add(f)
                    all_facts.append(f)

            for n_dict in sr.nodes:
                key = n_dict.get("name") or n_dict.get("uuid")
                if not key:
                    continue
                if key not in entity_insights:
                    custom_labels = [
                        lbl for lbl in (n_dict.get("labels") or [])
                        if lbl not in ("Entity", "Node")
                    ]
                    entity_insights[key] = {
                        "name": n_dict.get("name"),
                        "type": custom_labels[0] if custom_labels else "Entity",
                        "summary": n_dict.get("summary", ""),
                        "related_facts": [],
                    }
            for e_dict in sr.edges:
                src = e_dict.get("source_node_name") or e_dict.get("source_node_uuid")
                tgt = e_dict.get("target_node_name") or e_dict.get("target_node_uuid")
                rel = e_dict.get("name") or "?"
                fact = e_dict.get("fact") or ""
                if src and tgt:
                    chain = f"{src} --[{rel}]--> {tgt}"
                    if fact:
                        chain += f" :: {fact}"
                    if chain not in relationship_chains:
                        relationship_chains.append(chain)

        return InsightForgeResult(
            query=query,
            simulation_requirement=simulation_requirement,
            sub_queries=sub_queries,
            semantic_facts=all_facts,
            entity_insights=list(entity_insights.values()),
            relationship_chains=relationship_chains,
            total_facts=len(all_facts),
            total_entities=len(entity_insights),
            total_relationships=len(relationship_chains),
        )

    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str,
        max_sub_queries: int,
    ) -> List[str]:
        """Ask the LLM to break the main question into focused sub-questions."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You decompose an analytical question into focused sub-questions "
                        "so a knowledge-graph search engine can retrieve relevant facts. "
                        "Output JSON only: {\"sub_queries\": [\"...\", ...]}."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Main question: {query}\n"
                        f"Simulation context: {simulation_requirement}\n"
                        f"Report context: {report_context[:500]}\n"
                        f"Generate up to {max_sub_queries} sub-queries. JSON only."
                    ),
                },
            ]
            payload = self.llm.chat_json(messages=messages, temperature=0.3, max_tokens=600)
            raw = payload.get("sub_queries")
            if isinstance(raw, list):
                return [str(s).strip() for s in raw if str(s).strip()][:max_sub_queries]
        except Exception as e:
            logger.warning(f"insight_forge sub-query generation failed: {e}")
        # Fallback: split on punctuation if LLM didn't help.
        return [query]

    # ---- Phase 6: interview_agents -------------------------------------

    @time_tool("postgres", "interview_agents")
    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: Optional[List[str]] = None,
    ):
        """Run the OASIS interview pipeline. The flow itself does not depend
        on Zep, so we delegate to the shared interview_runner module."""
        from .interview_runner import run_interview_agents

        return run_interview_agents(
            llm=self.llm,
            simulation_id=simulation_id,
            interview_requirement=interview_requirement,
            simulation_requirement=simulation_requirement,
            max_agents=max_agents,
            custom_questions=custom_questions,
        )
