"""
End-to-end smoke for the Postgres graph backend (Phase 1).

Requires:
  - GRAPH_BACKEND=postgres
  - DATABASE_URL set
  - Postgres running with the 001_initial.sql migration applied
  - psycopg installed (extras: backend pip install -e '.[postgres]')

Usage:
  cd backend
  GRAPH_BACKEND=postgres \\
    DATABASE_URL=postgresql://mirofish:mirofish@localhost:5432/mirofish \\
    LLM_API_KEY=dummy \\
    .venv/bin/python -m scripts.postgres_smoke

Exits non-zero on any assertion failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config  # noqa: E402
from app.repositories.graph import get_graph_backend  # noqa: E402
from app.repositories.graph.errors import GraphNotFoundError  # noqa: E402


def _fail(msg: str) -> None:
    print(f"[postgres_smoke] FAIL: {msg}")
    raise SystemExit(2)


def _ok(msg: str) -> None:
    print(f"[postgres_smoke] OK   {msg}")


def main() -> int:
    if Config.GRAPH_BACKEND != "postgres":
        _fail(f"GRAPH_BACKEND={Config.GRAPH_BACKEND!r}; expected 'postgres'")
    if not Config.DATABASE_URL:
        _fail("DATABASE_URL is empty")

    backend = get_graph_backend()
    if backend.name != "postgres":
        _fail(f"factory returned {backend.name}; expected 'postgres'")
    _ok(f"factory returned PostgresGraphBackend (model={Config.EMBEDDING_MODEL}, dim={Config.EMBEDDING_DIM})")

    if not backend.healthcheck():
        _fail("healthcheck returned False — is Postgres up and migration applied?")
    _ok("healthcheck pass")

    # ---- Create graph + ontology ----------------------------------------
    graph_id = backend.create_graph(name="phase1-smoke")
    _ok(f"create_graph -> {graph_id}")
    backend.set_ontology(graph_id, {"entity_types": [{"name": "Person"}], "edge_types": []})
    _ok("set_ontology")

    # ---- Upsert nodes + edge --------------------------------------------
    alice = backend.upsert_node(graph_id, "Alice", labels=["Person"], summary="QA lead")
    bob = backend.upsert_node(graph_id, "Bob", labels=["Person"], summary="Reviewer")
    _ok(f"upsert_node Alice={alice} Bob={bob}")
    edge_id = backend.upsert_edge(
        graph_id,
        source_name="Alice",
        target_name="Bob",
        relation_name="REVIEWS",
        fact_text="Alice's PR is reviewed by Bob",
    )
    _ok(f"upsert_edge -> {edge_id}")

    # Re-upsert same node should not duplicate (UNIQUE on graph_id+name).
    alice_again = backend.upsert_node(graph_id, "Alice", labels=["Person"], summary="QA lead v2")
    if alice_again != alice:
        _fail(f"upsert_node not idempotent: first={alice}, second={alice_again}")
    _ok("upsert_node idempotent")

    # ---- Wire format parity ---------------------------------------------
    data = backend.get_graph_data(graph_id)
    expected_node_keys = {"uuid", "name", "labels", "summary", "attributes", "created_at"}
    expected_edge_keys = {
        "uuid", "name", "fact", "fact_type", "source_node_uuid", "target_node_uuid",
        "source_node_name", "target_node_name", "attributes",
        "created_at", "valid_at", "invalid_at", "expired_at", "episodes",
    }
    if not data["nodes"]:
        _fail("get_graph_data returned no nodes")
    if set(data["nodes"][0].keys()) != expected_node_keys:
        _fail(f"node keys mismatch: {set(data['nodes'][0].keys())}")
    if set(data["edges"][0].keys()) != expected_edge_keys:
        _fail(f"edge keys mismatch: {set(data['edges'][0].keys())}")
    if data["node_count"] != 2 or data["edge_count"] != 1:
        _fail(f"counts wrong: nodes={data['node_count']}, edges={data['edge_count']}")
    _ok("get_graph_data wire format matches Zep contract")

    # ---- Statistics ------------------------------------------------------
    stats = backend.get_graph_statistics(graph_id)
    if stats["total_nodes"] != 2 or stats["total_edges"] != 1:
        _fail(f"stats counts wrong: {stats}")
    if stats["entity_types"].get("Person") != 2:
        _fail(f"entity_types wrong: {stats['entity_types']}")
    if stats["relation_types"].get("REVIEWS") != 1:
        _fail(f"relation_types wrong: {stats['relation_types']}")
    _ok("get_graph_statistics consistent")

    # ---- Phase 3: entity reader paridad ----------------------------------
    from app.services.entity_reader import get_entity_reader

    reader = get_entity_reader()
    if reader.__class__.__name__ != "PostgresEntityReader":
        _fail(f"factory returned {reader.__class__.__name__}; expected PostgresEntityReader")
    _ok("entity_reader factory returns PostgresEntityReader")

    filtered = reader.filter_defined_entities(
        graph_id=graph_id, defined_entity_types=None, enrich_with_edges=True
    )
    if filtered.filtered_count != 2:
        _fail(f"filter_defined_entities filtered_count={filtered.filtered_count}; expected 2")
    if "Person" not in filtered.entity_types:
        _fail(f"filter_defined_entities missing Person label: {filtered.entity_types}")
    if not all(e.related_edges for e in filtered.entities):
        _fail("expected enriched related_edges for both entities")
    _ok("filter_defined_entities preserves wire format and enriches edges")

    by_type = reader.get_entities_by_type(graph_id, "Person", enrich_with_edges=False)
    if len(by_type) != 2:
        _fail(f"get_entities_by_type len={len(by_type)}; expected 2")
    _ok("get_entities_by_type Person -> 2")

    alice_uuid = next(e.uuid for e in filtered.entities if e.name == "Alice")
    full = reader.get_entity_with_context(graph_id, alice_uuid)
    if full is None or full.name != "Alice":
        _fail("get_entity_with_context Alice failed")
    _ok("get_entity_with_context returns hydrated EntityNode")

    # ---- Phase 4 stubs --------------------------------------------------
    try:
        backend.search_graph(graph_id, "anything")
        _fail("search_graph should raise NotImplementedError in Phase 3")
    except NotImplementedError:
        _ok("search_graph correctly raises NotImplementedError (Phase 4)")

    # wait_for_episodes is a no-op in Phase 1+
    backend.wait_for_episodes([])
    _ok("wait_for_episodes no-op")

    # ---- Cleanup --------------------------------------------------------
    backend.delete_graph(graph_id)
    _ok(f"delete_graph {graph_id}")
    try:
        backend.delete_graph(graph_id)
        _fail("delete_graph should raise GraphNotFoundError when missing")
    except GraphNotFoundError:
        _ok("delete_graph raises GraphNotFoundError on missing graph")

    print("[postgres_smoke] ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
