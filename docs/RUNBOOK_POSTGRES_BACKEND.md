# Runbook — Backend Postgres + pgvector (Fase 0)

> Estado: **Fase 0 lista** (infraestructura, flag, esqueleto). Las
> Fases 1-7 (CRUD, ingesta, herramientas del Report Agent) llegan después.
> Mientras tanto, `GRAPH_BACKEND=zep` (default) sigue funcionando igual.

## Para qué sirve

Activar el backend Postgres+pgvector como reemplazo de Zep Cloud. La
selección se hace por variable de entorno:

```
GRAPH_BACKEND=zep         # default — usa Zep Cloud (sin cambios)
GRAPH_BACKEND=postgres    # usa Postgres + pgvector
```

Coexistencia prolongada: ambos backends pueden vivir uno al lado del
otro durante toda la migración. Es un **rollback de un solo cambio de
variable**.

## 1. Levantar Postgres local con pgvector

El `docker-compose.yml` define un servicio `db` bajo el profile
`postgres`, así que **no se enciende a menos que lo pidas**:

```bash
# Levanta solo Postgres (no toca el contenedor mirofish actual)
docker compose --profile postgres up -d db

# Health
docker compose --profile postgres ps
```

Credenciales por defecto (cambiables con env vars antes de levantar):

| Variable | Default |
|---|---|
| `POSTGRES_USER` | `mirofish` |
| `POSTGRES_PASSWORD` | `mirofish` |
| `POSTGRES_DB` | `mirofish` |
| `POSTGRES_PORT` | `5432` |

Volumen persistente: `mirofish_pgdata`. Para borrar todo:

```bash
docker compose --profile postgres down -v
```

## 2. Configurar variables de entorno

En `.env` de la raíz del proyecto:

```ini
GRAPH_BACKEND=postgres
DATABASE_URL=postgresql://mirofish:mirofish@localhost:5432/mirofish

# --- Embeddings ---
EMBEDDING_PROVIDER=openai          # openai | ollama
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Si usas Ollama:
# EMBEDDING_PROVIDER=ollama
# EMBEDDING_MODEL=nomic-embed-text
# EMBEDDING_DIM=768
# OLLAMA_BASE_URL=http://localhost:11434
```

> ⚠️ La dimensión del vector está cableada en el esquema SQL en el
> momento de aplicar la migración. **Cambiar `EMBEDDING_DIM` después
> exige rehacer el esquema** (Fase 1+ ofrecerá un script de re-embed).

## 3. Instalar dependencias del backend Postgres

Las libs `psycopg`, `psycopg-pool` y `pgvector` son **opcionales** —
solo necesarias cuando `GRAPH_BACKEND=postgres`:

```bash
cd backend
.venv/bin/pip install -e '.[postgres]'
```

## 4. Aplicar migraciones

```bash
cd backend
.venv/bin/python -m migrations.apply
```

Salida esperada:

```
[apply.py] Connecting to Postgres (embedding_dim=1536)...
[apply.py] 001_initial.sql: applying...
[apply.py] 001_initial.sql: OK
[apply.py] All migrations applied.
```

Re-ejecutarlo es seguro (idempotente, lleva ledger en
`schema_migrations`).

## 5. Embeddings con Ollama (opcional)

Si quieres correr 100 % local sin OpenAI:

```bash
# Mac
brew install ollama
ollama serve &
ollama pull nomic-embed-text
```

Luego en `.env`:

```
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
```

Verifica que el endpoint responde:

```bash
curl -sS http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"hola mundo"}' | head -c 80
```

## 6. Estado actual de la migración

| Capa | Fase | Estado |
|---|---|---|
| `docker-compose db` + pgvector | 0 | ✅ |
| Flag `GRAPH_BACKEND` + validación | 0 | ✅ |
| Migración SQL inicial (`graphs`, `nodes`, `edges`, `chunks`, `episodes`) | 0 | ✅ |
| `repositories/graph/protocol.py` (`GraphBackend` Protocol) | 0 | ✅ |
| `ZepGraphBackend` (wrapper sobre código actual) | 0 | ✅ |
| `PostgresGraphBackend` esqueleto (NotImplementedError) | 0 | ✅ |
| `services/embeddings/` (OpenAI + Ollama) | 0 | ✅ |
| CRUD nodos/aristas en Postgres | 1 | ✅ |
| Ingesta + chunking + embeddings + materialización | 2 | ✅ |
| Entity reader paridad | 3 | ✅ |
| Report Agent tools paridad | 4 | ✅ |
| Memoria dinámica de grafo durante simulación | 5 | ✅ |
| OASIS profiles + interview_agents sin Zep directo | 6 | ✅ |
| Observabilidad (admin/health, métricas, export) | 7 | ✅ |

## 7. Rollback

Cambiar:
```
GRAPH_BACKEND=zep
```
y reiniciar el backend. La feature flag domina; los modules de Postgres
no se cargan si no son necesarios.

## 8. Healthcheck rápido del Postgres backend

```python
from app.repositories.graph import get_graph_backend
backend = get_graph_backend()
print(backend.name)  # 'postgres'
print(backend.healthcheck())  # True si la conexión funciona
```

## 8b. Endpoint admin (Fase 7)

Mientras el backend Flask esté corriendo:

```bash
# Diagnóstico unificado: backend activo, pool psycopg, ping a embedding,
# conteos por tabla, y resumen de métricas de tools.
curl -sS http://localhost:5001/api/admin/graph-backend/health | jq

# Métricas de latencia/errores por tool (calls, avg_ms, p_min/max, errors).
curl -sS http://localhost:5001/api/admin/graph-backend/metrics | jq

# Resetear métricas in-memory (útil después de un benchmark).
curl -sS -X POST http://localhost:5001/api/admin/graph-backend/metrics/reset
```

Salida típica de `/health` con `GRAPH_BACKEND=postgres` + Ollama local:

```json
{
  "success": true,
  "ok": true,
  "data": {
    "backend": "postgres",
    "embedding": {
      "provider": "ollama",
      "model": "nomic-embed-text",
      "dim": 768,
      "reachable": true,
      "latency_ms": 8.43
    },
    "postgres": { "reachable": true, "latency_ms": 1.27 },
    "counts": { "graphs": 2, "graph_nodes": 137, "graph_edges": 412, ... },
    "tool_metrics": { ... }
  }
}
```

Si `embedding.reachable=false` → arrancá `ollama serve` o revisá la
`LLM_API_KEY`. Si `postgres.reachable=false` → verificá que el contenedor
`db` esté arriba (`docker compose --profile postgres ps`).

## 9. Export de un graph_id (Fase 7, A/B y snapshots)

```bash
cd backend
GRAPH_BACKEND=postgres \
  DATABASE_URL=postgresql://mirofish:mirofish@localhost:5432/mirofish \
  LLM_API_KEY=dummy \
  .venv/bin/python -m scripts.postgres_export <graph_id> snapshot.json
```

El JSON incluye `graph`, `nodes`, `edges`, `episodes` y `chunks` (texto;
los vectores se omiten para mantener el archivo manejable). Forma del
output diff-friendly. Útil para:
- Comparar `graph_id` migrado contra su gemelo en Zep (paridad estadística).
- Snapshot antes de un re-build destructivo.
- Compartir un grafo entre máquinas sin volver a correr ingesta.

## 9. Documentos relacionados

- [docs/IMPLEMENTATION_ZEP_TO_POSTGRES.md](IMPLEMENTATION_ZEP_TO_POSTGRES.md) — plan completo
- [REGLAS_COMPLEMENTO.md](../REGLAS_COMPLEMENTO.md) — gobierno de cambios
- [docs/INDEX_ROADMAPS.md](INDEX_ROADMAPS.md) — orden recomendado de roadmaps
