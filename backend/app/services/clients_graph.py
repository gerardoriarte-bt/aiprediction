"""
ClientGraphService — Entrega 3.

Bridges the multi-client model with the graph stack: each client gets
its own graph_id, and uploaded context (briefs, studies, metrics) is
ingested into that graph using the Phase 2 pipeline. Subsequent
features (Creative Testing, Report Agent, Simulation) can read this
graph to know the client's history without the planner re-feeding it.

Lives on top of PostgresGraphBackend + GraphIngestService — no Zep
fallback, since clients are always Postgres-backed.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..repositories.clients import ClientNotFoundError
from ..repositories.graph import connection
from ..repositories.graph.errors import GraphNotFoundError
from ..repositories.graph.repos import (
    EpisodeRepository,
    GraphRepository,
)
from ..utils.logger import get_logger
from .clients import ClientService
from .text_processor import TextProcessor


logger = get_logger("mirofish.clients_graph.service")


# Default brand-analysis ontology applied to every client graph at
# bootstrap. Specialised projects can override it via the regular
# ontology endpoints once we surface them per-client. Keeps the
# extraction prompt focused on what the agency actually cares about.
_DEFAULT_ONTOLOGY: Dict[str, Any] = {
    "entity_types": [
        {"name": "Brand", "description": "A brand or sub-brand owned by the client."},
        {"name": "Product", "description": "A product or product line."},
        {"name": "Audience", "description": "A target audience segment or persona."},
        {"name": "Channel", "description": "Marketing or distribution channel."},
        {"name": "Claim", "description": "A claim, message or value proposition."},
        {"name": "Competitor", "description": "A competing brand, product or actor."},
        {"name": "Study", "description": "A piece of research, survey or report."},
        {"name": "Metric", "description": "A KPI or measurement."},
        {"name": "Risk", "description": "A reputational, legal or compliance risk."},
        {"name": "Person", "description": "A relevant individual."},
        {"name": "Organization", "description": "An organization, regulator or partner."},
    ],
    "edge_types": [
        {
            "name": "MENTIONS",
            "description": "Generic citation between two entities.",
            "source_targets": [],
        },
        {
            "name": "TARGETS",
            "description": "A claim or campaign targets an audience.",
            "source_targets": [
                {"source": "Claim", "target": "Audience"},
                {"source": "Brand", "target": "Audience"},
                {"source": "Product", "target": "Audience"},
            ],
        },
        {
            "name": "COMPETES_WITH",
            "description": "Brand or product competes with another.",
            "source_targets": [{"source": "Brand", "target": "Competitor"}],
        },
        {
            "name": "SUPPORTS",
            "description": "A study or metric supports a claim or position.",
            "source_targets": [
                {"source": "Study", "target": "Claim"},
                {"source": "Metric", "target": "Claim"},
            ],
        },
        {
            "name": "CONTRADICTS",
            "description": "A study or claim contradicts another claim.",
            "source_targets": [
                {"source": "Study", "target": "Claim"},
                {"source": "Claim", "target": "Claim"},
            ],
        },
        {
            "name": "MEASURED_BY",
            "description": "A campaign or claim is measured by a metric.",
            "source_targets": [{"source": "Claim", "target": "Metric"}],
        },
        {
            "name": "FLAGS",
            "description": "An entity flags a risk.",
            "source_targets": [
                {"source": "Claim", "target": "Risk"},
                {"source": "Brand", "target": "Risk"},
            ],
        },
    ],
}


def _serialise_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if record is None:
        return None  # type: ignore[return-value]
    out: Dict[str, Any] = {}
    for k, v in record.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


class ClientGraphService:
    """Stateless façade — graph operations scoped to a single client."""

    @staticmethod
    def _require_client(client_id: str) -> Dict[str, Any]:
        return ClientService.get_client(client_id)

    # ---- Graph bootstrap -------------------------------------------------

    @staticmethod
    def bootstrap_graph(client_id: str) -> Dict[str, Any]:
        """Create a Postgres graph for the client if it doesn't have one yet,
        attach the default ontology and persist the graph_id back on
        the clients row. Idempotent: returns the existing client otherwise."""
        client = ClientGraphService._require_client(client_id)
        if client.get("graph_id"):
            return client

        # Local imports keep boot-time cost low for callers that don't
        # touch the graph backend.
        from ..repositories.graph.postgres_backend import PostgresGraphBackend

        backend = PostgresGraphBackend()
        graph_id = backend.create_graph(name=f"client:{client.get('slug') or client_id}")
        backend.set_ontology(graph_id, _DEFAULT_ONTOLOGY)

        updated = ClientService.update_client(client_id, {"graph_id": graph_id})
        logger.info(
            "Client %s bootstrapped graph %s with default ontology",
            client_id,
            graph_id,
        )
        return updated

    # ---- Ingest ----------------------------------------------------------

    @staticmethod
    def ingest_text(
        client_id: str,
        text: str,
        source: Optional[str] = None,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
    ) -> Dict[str, Any]:
        """Chunk the text, embed, run the LLM extractor and upsert
        nodes/edges. Returns ingest stats and the new episode id.
        Synchronous on purpose — keep it simple until the volume warrants
        async (then we reuse TaskManager)."""
        client = ClientGraphService._require_client(client_id)
        graph_id = client.get("graph_id")
        if not graph_id:
            # Auto-bootstrap so the planner doesn't have to remember to do it.
            client = ClientGraphService.bootstrap_graph(client_id)
            graph_id = client["graph_id"]

        text = (text or "").strip()
        if not text:
            raise ValueError("text is required")

        chunks = TextProcessor.split_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        if not chunks:
            raise ValueError("text produced no chunks (probably whitespace-only)")

        # Pull ontology (was set at bootstrap, kept idempotent).
        with connection.get_pool().connection() as conn:
            graph_row = GraphRepository.get(conn, graph_id)
        ontology = (graph_row or {}).get("ontology_json") or _DEFAULT_ONTOLOGY
        if isinstance(ontology, str):
            import json as _json
            try:
                ontology = _json.loads(ontology)
            except Exception:
                ontology = _DEFAULT_ONTOLOGY

        from .graph_ingest import GraphIngestService

        ingest = GraphIngestService()
        result = ingest.ingest(
            conn_factory=connection.get_pool().connection,
            graph_id=graph_id,
            chunks=chunks,
            ontology=ontology,
            progress_callback=None,
        )

        return {
            "client_id": client_id,
            "graph_id": graph_id,
            "chunk_count": len(chunks),
            "source": source,
            "episode_uuids": result.get("episode_uuids", []),
            "stats": result.get("stats", {}),
        }

    # ---- Read APIs -------------------------------------------------------

    @staticmethod
    def list_context(client_id: str) -> Dict[str, Any]:
        client = ClientGraphService._require_client(client_id)
        graph_id = client.get("graph_id")
        if not graph_id:
            return {
                "client_id": client_id,
                "graph_id": None,
                "episodes": [],
                "totals": {"episodes": 0, "chunks": 0, "nodes": 0, "edges": 0},
            }

        with connection.get_pool().connection() as conn:
            episodes = EpisodeRepository.list_by_graph(conn, graph_id)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM graph_chunks WHERE graph_id = %s;",
                    (graph_id,),
                )
                chunk_total = int(cur.fetchone()[0])
                cur.execute(
                    "SELECT COUNT(*) FROM graph_nodes WHERE graph_id = %s;",
                    (graph_id,),
                )
                node_total = int(cur.fetchone()[0])
                cur.execute(
                    "SELECT COUNT(*) FROM graph_edges WHERE graph_id = %s;",
                    (graph_id,),
                )
                edge_total = int(cur.fetchone()[0])

        return {
            "client_id": client_id,
            "graph_id": graph_id,
            "episodes": [_serialise_record(e) for e in episodes],
            "totals": {
                "episodes": len(episodes),
                "chunks": chunk_total,
                "nodes": node_total,
                "edges": edge_total,
            },
        }

    @staticmethod
    def graph_data(client_id: str) -> Dict[str, Any]:
        """Return the client graph as {nodes, edges} ready for D3.

        Node `type` is derived from the first non-structural label (Brand,
        Audience, Channel, …). Node `weight` is the degree (incoming +
        outgoing edge count) — we use it to size circles in the canvas.
        Edges are ungrouped: source/target reference node ids as strings.
        """
        client = ClientGraphService._require_client(client_id)
        graph_id = client.get("graph_id")
        if not graph_id:
            return {
                "client_id": client_id,
                "graph_id": None,
                "nodes": [],
                "edges": [],
                "type_counts": {},
                "totals": {"nodes": 0, "edges": 0},
            }

        from ..repositories.graph.repos import (
            EdgeRepository,
            NodeRepository,
        )

        with connection.get_pool().connection() as conn:
            node_rows = NodeRepository.list_by_graph(conn, graph_id)
            edge_rows = EdgeRepository.list_by_graph(conn, graph_id)

        # Pre-compute degree.
        degree: Dict[str, int] = {}
        for e in edge_rows:
            for key in (e.get("source_node_id"), e.get("target_node_id")):
                k = str(key)
                degree[k] = degree.get(k, 0) + 1

        nodes_out: List[Dict[str, Any]] = []
        type_counts: Dict[str, int] = {}
        for n in node_rows:
            nid = str(n["node_id"])
            labels = list(n.get("labels") or [])
            t = next((l for l in labels if l not in ("Entity", "Node")), "Entity")
            d = degree.get(nid, 0)
            nodes_out.append(
                {
                    "id": nid,
                    "label": n.get("name") or "?",
                    "type": t,
                    "weight": d,
                    "summary": n.get("summary") or "",
                }
            )
            type_counts[t] = type_counts.get(t, 0) + 1

        edges_out: List[Dict[str, Any]] = []
        for e in edge_rows:
            invalid = e.get("invalid_at")
            expired = e.get("expired_at")
            edges_out.append(
                {
                    "id": str(e["edge_id"]),
                    "source": str(e["source_node_id"]),
                    "target": str(e["target_node_id"]),
                    "kind": "factual",
                    "name": e.get("relation_name") or "",
                    "fact": e.get("fact_text") or "",
                    "active": expired is None and invalid is None,
                }
            )

        return {
            "client_id": client_id,
            "graph_id": graph_id,
            "nodes": nodes_out,
            "edges": edges_out,
            "type_counts": type_counts,
            "totals": {"nodes": len(nodes_out), "edges": len(edges_out)},
        }

    @staticmethod
    def predict(
        client_id: str,
        question: str,
        limit_facts: int = 12,
    ) -> Dict[str, Any]:
        """Answer an open question about the client using its graph as ground truth.

        Pipeline: search the graph for relevant facts → ask the LLM with
        only those facts as context → return answer plus the facts cited
        so the planner can audit the source.
        """
        if not question or not question.strip():
            raise ValueError("question is required")

        client = ClientGraphService._require_client(client_id)
        graph_id = client.get("graph_id")

        # Search facts (gracefully empty if no graph yet).
        facts: List[str] = []
        if graph_id:
            try:
                from .postgres_tools import PostgresToolsService

                tools = PostgresToolsService()
                sr = tools.search_graph(graph_id=graph_id, query=question, limit=limit_facts)
                facts = list(sr.facts or [])
            except Exception as e:
                logger.warning(f"predict: graph search failed: {e}")
                facts = []

        # Ask the LLM with the facts as the only allowed evidence base.
        from ..utils.llm_client import LLMClient

        llm = LLMClient()
        bullets = "\n".join(f"- {f}" for f in facts) if facts else "(no facts yet — graph empty)"
        brand_card = "\n".join(
            filter(
                None,
                [
                    f"Industry: {client.get('industry')}" if client.get("industry") else None,
                    f"Description: {client.get('description')}" if client.get("description") else None,
                    f"Brand guidelines: {client.get('brand_guidelines')}" if client.get("brand_guidelines") else None,
                ],
            )
        ) or "(brand card empty)"

        system = (
            "You are an in-house strategist answering brand and marketing questions about "
            "a single client. Use ONLY the facts provided; if the facts are insufficient, "
            "say so explicitly and suggest what context to upload. Be concise (3-6 sentences) "
            "and end with a short bullet list of the facts you cited (verbatim)."
        )
        user = (
            f"Client: {client.get('name')}\n"
            f"=== Brand card ===\n{brand_card}\n\n"
            f"=== Facts on file ===\n{bullets}\n\n"
            f"=== Question ===\n{question.strip()}"
        )

        try:
            answer = llm.chat(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
                max_tokens=600,
            )
        except Exception as e:
            logger.warning(f"predict: LLM call failed: {e}")
            answer = (
                "Could not generate an answer right now. The facts on file are listed below."
            )

        return {
            "client_id": client_id,
            "graph_id": graph_id,
            "question": question.strip(),
            "answer": (answer or "").strip(),
            "facts": facts,
            "fact_count": len(facts),
        }

    @staticmethod
    def search(
        client_id: str,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        client = ClientGraphService._require_client(client_id)
        graph_id = client.get("graph_id")
        if not graph_id:
            raise GraphNotFoundError(f"client {client_id} has no graph yet")
        if not query or not query.strip():
            raise ValueError("query is required")

        from .postgres_tools import PostgresToolsService

        tools = PostgresToolsService()
        result = tools.search_graph(graph_id=graph_id, query=query, limit=limit)
        return {
            "client_id": client_id,
            "graph_id": graph_id,
            "query": query,
            "facts": list(result.facts),
            "edges": list(result.edges),
            "nodes": list(result.nodes),
            "total_count": result.total_count,
        }
