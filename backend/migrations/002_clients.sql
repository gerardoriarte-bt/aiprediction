-- 002_clients.sql
-- Entrega 2: modelo Cliente como entidad agrupadora del producto.
-- Cada Cliente puede luego tener su propio graph_id (entrega 3),
-- assets multimodales (entrega 4-6), creative tests, reportes y simulaciones.
--
-- Idempotente: safe to re-run. Apply with backend/migrations/apply.py.

CREATE TABLE IF NOT EXISTS clients (
    client_id        TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    slug             TEXT UNIQUE NOT NULL,
    industry         TEXT,
    description      TEXT,
    brand_guidelines TEXT,
    -- Free-form per-client metadata: social handles, KPIs, study links,
    -- account managers, etc. Kept as JSONB to evolve without schema churn.
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Optional pointer to the per-client knowledge graph (Entrega 3 wires
    -- this end-to-end; for now it is just stored if provided).
    graph_id         TEXT,
    is_default       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_slug   ON clients(slug);
CREATE INDEX IF NOT EXISTS idx_clients_active ON clients(is_default);
