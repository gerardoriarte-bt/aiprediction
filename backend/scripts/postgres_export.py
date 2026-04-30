"""
Export a single graph_id from Postgres to JSON (Phase 7).

Use case: A/B parity checks against Zep, snapshot before destructive
operations, share a graph between machines, or feed downstream tools.

Output is JSON with graphs/nodes/edges/episodes plus chunks (text only —
embeddings are dropped because they balloon the file and they can be
regenerated from text). Wire format mirrors PostgresGraphBackend.get_graph_data
where possible so the file is human-diffable.

Usage:
    cd backend
    GRAPH_BACKEND=postgres \\
      DATABASE_URL=postgresql://mirofish:mirofish@localhost:5432/mirofish \\
      LLM_API_KEY=dummy \\
      .venv/bin/python -m scripts.postgres_export <graph_id> [output.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config  # noqa: E402


def _fail(msg: str) -> int:
    print(f"[postgres_export] FAIL: {msg}", file=sys.stderr)
    return 2


def _serialise(value: Any) -> Any:
    """Coerce psycopg/postgres types to JSON-friendly primitives."""
    from datetime import datetime, date

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialise(v) for v in value]
    return value


def export_graph(graph_id: str) -> Dict[str, Any]:
    if Config.GRAPH_BACKEND != "postgres":
        raise SystemExit(_fail(f"GRAPH_BACKEND={Config.GRAPH_BACKEND!r}; expected 'postgres'"))
    if not Config.DATABASE_URL:
        raise SystemExit(_fail("DATABASE_URL is empty"))

    from app.repositories.graph import connection
    from app.repositories.graph.errors import GraphNotFoundError
    from app.repositories.graph.repos import (
        EdgeRepository,
        EpisodeRepository,
        GraphRepository,
        NodeRepository,
    )

    with connection.get_pool().connection() as conn:
        graph = GraphRepository.get(conn, graph_id)
        if not graph:
            raise SystemExit(_fail(f"graph not found: {graph_id}"))

        nodes = NodeRepository.list_by_graph(conn, graph_id)
        edges = EdgeRepository.list_by_graph(conn, graph_id)
        episodes = EpisodeRepository.list_by_graph(conn, graph_id)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_id, episode_id, text, text_hash, metadata, created_at
                FROM graph_chunks
                WHERE graph_id = %s
                ORDER BY chunk_id;
                """,
                (graph_id,),
            )
            cols = [d[0] for d in cur.description]
            chunks = [dict(zip(cols, row)) for row in cur.fetchall()]

    payload = {
        "format_version": 1,
        "exported_at": _serialise(__import__("datetime").datetime.utcnow()),
        "embedding_dim": Config.EMBEDDING_DIM,
        "embedding_provider": Config.EMBEDDING_PROVIDER,
        "embedding_model": Config.EMBEDDING_MODEL,
        "graph": _serialise(graph),
        "nodes": [_serialise(n) for n in nodes],
        "edges": [_serialise(e) for e in edges],
        "episodes": [_serialise(ep) for ep in episodes],
        "chunks": [_serialise(c) for c in chunks],
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges),
            "episodes": len(episodes),
            "chunks": len(chunks),
        },
    }
    return payload


def main(argv: list) -> int:
    if len(argv) < 2:
        print("Usage: postgres_export.py <graph_id> [output.json]", file=sys.stderr)
        return 1
    graph_id = argv[1]
    out_path = Path(argv[2]) if len(argv) >= 3 else Path(f"{graph_id}.export.json")

    payload = export_graph(graph_id)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = payload["stats"]
    print(
        f"[postgres_export] wrote {out_path} — "
        f"nodes={stats['nodes']} edges={stats['edges']} "
        f"episodes={stats['episodes']} chunks={stats['chunks']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
