"""
GraphIngestService — pipeline equivalente al ingest de Zep, pero contra Postgres.

Fase 2 del roadmap IMPLEMENTATION_ZEP_TO_POSTGRES.

Para cada chunk de texto:
  1. Genera embedding (OpenAI o Ollama según EMBEDDING_PROVIDER).
  2. Inserta el chunk en `graph_chunks` con su vector.
  3. Llama al LLM para extraer entidades y relaciones siguiendo la ontología
     persistida en `graphs.ontology_json`.
  4. Upsert idempotente sobre `graph_nodes` (UNIQUE graph_id+name) y
     append en `graph_edges`.

Diseño:
- El servicio NO ejecuta SQL: delega 100% en los repositorios. REGLAS_COMPLEMENTO §2.
- Errores de un chunk individual se loguean pero no abortan toda la corrida —
  preferimos un grafo parcial y reportar la falla, en lugar de perder todo el
  trabajo (REGLAS §7: "si un complemento falla, el sistema debe poder seguir
  operando con el flujo actual"). Si la ratio de fallos supera FAIL_RATIO, abortamos.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..repositories.graph.repos import (
    ChunkRepository,
    EdgeRepository,
    EpisodeRepository,
    NodeRepository,
)
from ..services.embeddings import EmbeddingError, get_embedding_client
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger


logger = get_logger("mirofish.graph.ingest")


ProgressCallback = Callable[[str, float], None]


_FAIL_RATIO = 0.6  # if more than this fraction of chunks fail, abort the run.


_EXTRACT_SYSTEM_PROMPT = """You extract entities and relations from a single
text chunk for a knowledge graph. Output valid JSON only — no prose, no
markdown fences. Stay strictly inside the entity_types and edge_types from
the ontology provided. Skip anything that doesn't fit.

Output schema:
{
  "entities": [
    {
      "name": "string (canonical, English when possible)",
      "labels": ["EntityTypeName"],
      "summary": "<= 200 chars",
      "attributes": {"key": "value"}
    }
  ],
  "relations": [
    {
      "source": "entity name (must match an entity above)",
      "target": "entity name (must match an entity above)",
      "relation": "RELATION_NAME (UPPER_SNAKE_CASE, must be in ontology edge_types)",
      "fact": "natural-language sentence describing the relation"
    }
  ]
}
"""


def _build_extract_user_prompt(chunk_text: str, ontology: Dict[str, Any]) -> str:
    entity_types = ontology.get("entity_types") or []
    edge_types = ontology.get("edge_types") or []

    def _shorten(items, fields):
        out = []
        for it in items[:32]:  # don't bloat the prompt with huge ontologies
            out.append({k: it.get(k) for k in fields if k in it})
        return out

    onto_compact = {
        "entity_types": _shorten(entity_types, ["name", "description"]),
        "edge_types": _shorten(edge_types, ["name", "description", "source_targets"]),
    }
    return (
        "=== Ontology ===\n"
        f"{json.dumps(onto_compact, ensure_ascii=False)}\n\n"
        "=== Text chunk ===\n"
        f"{chunk_text}\n\n"
        "Return JSON only."
    )


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _coerce_entity(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = (raw.get("name") or "").strip()
    if not name:
        return None
    labels = raw.get("labels") or []
    if not isinstance(labels, list):
        labels = [str(labels)]
    labels = [str(x).strip() for x in labels if str(x).strip()]
    summary = raw.get("summary") or ""
    if not isinstance(summary, str):
        summary = str(summary)
    if len(summary) > 800:
        summary = summary[:800]
    attrs = raw.get("attributes") or {}
    if not isinstance(attrs, dict):
        attrs = {"raw": str(attrs)}
    return {"name": name, "labels": labels, "summary": summary, "attributes": attrs}


_REL_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _coerce_relation(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    src = (raw.get("source") or "").strip()
    tgt = (raw.get("target") or "").strip()
    rel = (raw.get("relation") or "").strip()
    if not src or not tgt or not rel:
        return None
    if not _REL_NAME_RE.match(rel):
        # normalise loose names (e.g. "works for") to UPPER_SNAKE
        rel = re.sub(r"[^A-Za-z0-9]+", "_", rel).strip("_").upper()
        if not rel:
            return None
    fact = raw.get("fact") or ""
    if not isinstance(fact, str):
        fact = str(fact)
    return {"source": src, "target": tgt, "relation": rel, "fact": fact}


@dataclass
class IngestStats:
    chunks_total: int = 0
    chunks_failed: int = 0
    entities_upserted: int = 0
    edges_inserted: int = 0
    edges_skipped_unknown_node: int = 0


class GraphIngestService:
    """Stateless ingest pipeline. One instance per build_task is enough."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        embedding_client=None,
        max_chunks_per_episode: int = 64,
    ) -> None:
        self.llm = llm_client or LLMClient()
        self.embed = embedding_client or get_embedding_client()
        self.max_chunks_per_episode = max_chunks_per_episode

    # ---- Public API -----------------------------------------------------

    def ingest(
        self,
        conn_factory,
        graph_id: str,
        chunks: List[str],
        ontology: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """Run the full ingest. `conn_factory` returns a context-managed psycopg
        connection (e.g. `connection.get_pool().connection`)."""
        stats = IngestStats(chunks_total=len(chunks))
        if not chunks:
            return {"episode_uuids": [], "stats": stats.__dict__}

        # 1) Episode + embeddings + chunk insert ------------------------------
        with conn_factory() as conn:
            episode_id = EpisodeRepository.insert(
                conn,
                graph_id=graph_id,
                source="postgres-ingest-v1",
                metadata={"chunk_count": len(chunks)},
                status="processing",
            )
            conn.commit()

        self._emit(progress_callback, "embedding chunks...", 0.0)

        # Embed in modest batches to keep memory bounded.
        BATCH = 32
        all_chunk_records: List[Dict[str, Any]] = []
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i : i + BATCH]
            try:
                vectors = self.embed.embed_batch(batch)
            except EmbeddingError as e:
                logger.error(f"embedding batch starting at {i} failed: {e}")
                # Record the failure and continue with zero vectors so the
                # text is still searchable as plaintext later.
                vectors = [[0.0] * self.embed.dim for _ in batch]
                stats.chunks_failed += len(batch)
            for text, vec in zip(batch, vectors):
                all_chunk_records.append(
                    {
                        "text": text,
                        "embedding": vec,
                        "text_hash": _hash_text(text),
                    }
                )
            self._emit(
                progress_callback,
                f"embedded {min(i + BATCH, len(chunks))}/{len(chunks)} chunks",
                min(0.4, (i + BATCH) / max(1, len(chunks)) * 0.4),
            )

        with conn_factory() as conn:
            ChunkRepository.insert_batch(conn, graph_id, episode_id, all_chunk_records)
            conn.commit()

        # 2) LLM extract + upsert per chunk -----------------------------------
        node_id_cache: Dict[str, int] = {}
        for idx, chunk_text in enumerate(chunks):
            try:
                extracted = self._extract(chunk_text, ontology)
            except Exception as e:
                logger.warning(f"chunk {idx}: LLM extract failed: {e}")
                stats.chunks_failed += 1
                self._fail_check(stats)
                self._emit_chunk_progress(progress_callback, idx, len(chunks))
                continue

            entities = [
                e for e in (_coerce_entity(x) for x in extracted.get("entities", [])) if e
            ]
            relations = [
                r for r in (_coerce_relation(x) for x in extracted.get("relations", [])) if r
            ]

            # Embed entity-level and edge-level texts so search_graph can
            # rank against them (the chunk-level vector is not enough —
            # entities and facts are the units the agent actually queries).
            entity_texts: List[str] = [
                f"{e['name']}. {e['summary']}".strip().rstrip(".") for e in entities
            ]
            relation_texts: List[str] = [
                (r["fact"] or f"{r['source']} {r['relation']} {r['target']}").strip()
                for r in relations
            ]
            try:
                entity_vectors = (
                    self.embed.embed_batch(entity_texts) if entity_texts else []
                )
            except EmbeddingError as e:
                logger.warning(f"chunk {idx}: entity embedding failed: {e}")
                entity_vectors = [None] * len(entity_texts)
            try:
                relation_vectors = (
                    self.embed.embed_batch(relation_texts) if relation_texts else []
                )
            except EmbeddingError as e:
                logger.warning(f"chunk {idx}: relation embedding failed: {e}")
                relation_vectors = [None] * len(relation_texts)

            # Upsert nodes (with embedding when available)
            with conn_factory() as conn:
                for i_e, ent in enumerate(entities):
                    try:
                        ent_vec = entity_vectors[i_e] if i_e < len(entity_vectors) else None
                        node_id = NodeRepository.upsert(
                            conn,
                            graph_id=graph_id,
                            name=ent["name"],
                            labels=ent["labels"],
                            summary=ent["summary"],
                            attributes=ent["attributes"],
                            embedding=ent_vec,
                        )
                        node_id_cache[ent["name"]] = node_id
                        stats.entities_upserted += 1
                    except Exception as e:
                        logger.warning(f"chunk {idx}: upsert node {ent['name']!r} failed: {e}")
                conn.commit()

            # Resolve relations only when both endpoints are known
            with conn_factory() as conn:
                for i_r, rel in enumerate(relations):
                    src = node_id_cache.get(rel["source"])
                    tgt = node_id_cache.get(rel["target"])
                    if src is None:
                        src = NodeRepository.get_id_by_name(conn, graph_id, rel["source"])
                    if tgt is None:
                        tgt = NodeRepository.get_id_by_name(conn, graph_id, rel["target"])
                    if src is None or tgt is None:
                        stats.edges_skipped_unknown_node += 1
                        continue
                    try:
                        rel_vec = relation_vectors[i_r] if i_r < len(relation_vectors) else None
                        EdgeRepository.upsert(
                            conn,
                            graph_id=graph_id,
                            source_node_id=src,
                            target_node_id=tgt,
                            relation_name=rel["relation"],
                            fact_text=rel["fact"],
                            embedding=rel_vec,
                        )
                        stats.edges_inserted += 1
                    except Exception as e:
                        logger.warning(f"chunk {idx}: upsert edge failed: {e}")
                conn.commit()

            self._emit_chunk_progress(progress_callback, idx, len(chunks))
            self._fail_check(stats)

        # 3) Mark episode processed ------------------------------------------
        with conn_factory() as conn:
            EpisodeRepository.mark_processed(conn, episode_id)
            conn.commit()

        self._emit(progress_callback, "ingest complete", 1.0)
        return {
            "episode_uuids": [str(episode_id)],
            "stats": stats.__dict__,
        }

    # ---- Internals ------------------------------------------------------

    def _extract(self, chunk_text: str, ontology: Dict[str, Any]) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": _build_extract_user_prompt(chunk_text, ontology)},
        ]
        return self.llm.chat_json(messages=messages, temperature=0.2, max_tokens=2048)

    def _emit(self, cb: Optional[ProgressCallback], msg: str, ratio: float) -> None:
        if cb is None:
            return
        try:
            cb(msg, max(0.0, min(1.0, ratio)))
        except Exception:
            logger.exception("progress callback raised; continuing")

    def _emit_chunk_progress(self, cb: Optional[ProgressCallback], idx: int, total: int) -> None:
        # 40-100% allocated to LLM extraction phase
        ratio = 0.4 + ((idx + 1) / max(1, total)) * 0.6
        self._emit(cb, f"materialised chunk {idx + 1}/{total}", ratio)

    def _fail_check(self, stats: IngestStats) -> None:
        if stats.chunks_total == 0:
            return
        ratio = stats.chunks_failed / stats.chunks_total
        if ratio > _FAIL_RATIO:
            raise RuntimeError(
                f"Ingest aborted: {stats.chunks_failed}/{stats.chunks_total} chunks failed"
                f" (ratio {ratio:.0%} > limit {_FAIL_RATIO:.0%})"
            )
