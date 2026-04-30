-- 001_initial.sql
-- Phase 0 of ROADMAP IMPLEMENTATION_ZEP_TO_POSTGRES.
-- Minimum schema with parity intent. Apply with backend/migrations/apply.py
-- which substitutes :embedding_dim from Config.EMBEDDING_DIM.
--
-- Idempotent: safe to re-run during Phase 0/1.

CREATE EXTENSION IF NOT EXISTS vector;

-- Graphs (top-level container; 1:1 with project graph_id).
CREATE TABLE IF NOT EXISTS graphs (
    graph_id        TEXT PRIMARY KEY,
    name            TEXT,
    description     TEXT,
    ontology_json   JSONB,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Episodes: traceability for ingest batches (parity with Zep episodes).
CREATE TABLE IF NOT EXISTS graph_episodes (
    episode_id      BIGSERIAL PRIMARY KEY,
    graph_id        TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
    external_uuid   TEXT,
    source          TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_graph_episodes_graph
    ON graph_episodes(graph_id, created_at DESC);

-- Chunks: raw text + embedding per ingest unit.
-- vector dimension is templated via :embedding_dim in apply.py.
CREATE TABLE IF NOT EXISTS graph_chunks (
    chunk_id        BIGSERIAL PRIMARY KEY,
    graph_id        TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
    episode_id      BIGINT REFERENCES graph_episodes(episode_id) ON DELETE SET NULL,
    text            TEXT NOT NULL,
    text_hash       TEXT,
    embedding       vector(:embedding_dim),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_graph_chunks_graph
    ON graph_chunks(graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_chunks_episode
    ON graph_chunks(episode_id);
-- HNSW vector index (best general-purpose; switch to IVFFlat if dataset
-- becomes very large and you want lower memory at the cost of recall).
CREATE INDEX IF NOT EXISTS idx_graph_chunks_embedding
    ON graph_chunks USING hnsw (embedding vector_cosine_ops);

-- Nodes: materialised entities.
CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id         BIGSERIAL PRIMARY KEY,
    graph_id        TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    labels          TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    summary         TEXT,
    attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding       vector(:embedding_dim),
    -- Optional Zep correlation key for the dual-write/migration window.
    zep_uuid        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (graph_id, name)
);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_graph
    ON graph_nodes(graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_labels
    ON graph_nodes USING GIN (labels);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_zep_uuid
    ON graph_nodes(zep_uuid) WHERE zep_uuid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_graph_nodes_embedding
    ON graph_nodes USING hnsw (embedding vector_cosine_ops);

-- Edges: relations between nodes; carry temporal validity for parity with
-- Zep's "active vs historical/expired" semantics (PanoramaResult / EdgeInfo).
CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id         BIGSERIAL PRIMARY KEY,
    graph_id        TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
    source_node_id  BIGINT NOT NULL REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    target_node_id  BIGINT NOT NULL REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    relation_name   TEXT NOT NULL,
    fact_text       TEXT,
    attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding       vector(:embedding_dim),
    valid_at        TIMESTAMPTZ,
    invalid_at      TIMESTAMPTZ,
    expired_at      TIMESTAMPTZ,
    zep_uuid        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_graph_edges_graph
    ON graph_edges(graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_source
    ON graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target
    ON graph_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_relation
    ON graph_edges(graph_id, relation_name);
CREATE INDEX IF NOT EXISTS idx_graph_edges_validity
    ON graph_edges(graph_id, valid_at, invalid_at, expired_at);
CREATE INDEX IF NOT EXISTS idx_graph_edges_embedding
    ON graph_edges USING hnsw (embedding vector_cosine_ops);

-- Schema migration ledger so apply.py can be idempotent and traceable.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         TEXT PRIMARY KEY,
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding_dim   INTEGER NOT NULL
);
