# Sintetic Prediction AI

> **An evolution of [MiroFish](https://github.com/666ghj/MiroFish).** Sintetic Prediction AI is a product layer built on top of the MiroFish multi-agent simulation engine. The original MiroFish project provides the agent-based social simulation core (OASIS-derived: graph build, persona generation, dual-platform simulation). Sintetic adds the multi-client product layer on top: per-client knowledge graphs, creative testing (R1–R6 multimodal), grounded predictions, and a redesigned Vue 3 workspace. Where MiroFish ends as a single-graph predictor, Sintetic begins as an agency-grade workspace for planners and digital media teams.

Multi-client predictive workspace for planners and digital media teams. Each client has its own knowledge graph (briefs, studies, metrics, brand guidelines). On top of that graph, the platform runs **creative tests** (text / single image / carousel / video), **agent-based simulations**, and **predictions** grounded on the client's actual context.

The simulation engine remains MiroFish — kept as the technical attribution throughout the codebase (env vars `MIROFISH_*`, badge `Powered by MiroFish`, OASIS internals). The multimodal stack (vision + audio) and the multi-client knowledge layer are Sintetic's contribution.

```
┌────────────────────────────────────────────────────────────────────┐
│ Frontend (Vue 3 + Vite, :3000)                                     │
│  Home → Client Workspace → Context / Tests / Sims / Reports        │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ REST + multipart
┌──────────────────────────────▼─────────────────────────────────────┐
│ Backend (Flask, :5001)                                             │
│  /api/clients          per-client CRUD + scoped lists              │
│  /api/graph            ontology gen + graph build (Postgres path)  │
│  /api/report/...       creative-test (text/image/carousel/video)   │
└──────────────┬──────────────────────────────────────┬──────────────┘
               │                                      │
               ▼                                      ▼
   ┌───────────────────────┐              ┌───────────────────────┐
   │ Postgres + pgvector   │              │ External services     │
   │   graphs / nodes /    │              │   OpenAI (chat+vision │
   │   edges / chunks      │              │   + Whisper) / Ollama │
   │   episodes / clients  │              │   ffmpeg (local bin)  │
   └───────────────────────┘              └───────────────────────┘
```

---

## Features

| Stage | Capability                                              | State            |
| ----- | ------------------------------------------------------- | ---------------- |
| R1    | Multi-client model + Home + per-client workspace        | shipped          |
| R2    | Cliente-céntrica UI (TopNav, Sidebar, tabs, manual)     | shipped          |
| R3.1  | Per-client knowledge graph + ingest                     | shipped          |
| R3.2  | `predict()` — answer questions grounded on the graph    | shipped          |
| R3.3  | Reports / sims scoped to a client                       | shipped          |
| R3.4  | Project creation flow propagates `client_id`            | shipped          |
| R4    | Creative test with single image (GPT-4o vision)         | shipped (mock E2E + live shape) |
| R5    | Carousel — multi-image with narrative coherence scoring | shipped (mock E2E + live shape) |
| R6    | Video — ffmpeg frames + Whisper transcript              | shipped (mock E2E + live shape) |

> The **live mode** of R4–R6 needs an `OPENAI_API_KEY`. Without it the runner falls back to deterministic mock — the UI is identical, the scoring is synthesized.

51 automated tests cover schema, prompt building, runner normalization, mock generation, video extraction (ffmpeg integration), and the multipart parsing of the start endpoint. See `backend/tests/`.

---

## System requirements

### Required

| Component  | Min version | Why                                                      |
| ---------- | ----------- | -------------------------------------------------------- |
| Python     | 3.11+       | Backend (Flask). Tested on 3.12.                         |
| Node.js    | 20 LTS+     | Frontend (Vite + Vue 3). Older Node can work but unverified. |
| PostgreSQL | 15+         | Persistence + `pgvector` extension for semantic search.  |
| pgvector   | 0.5+        | Vector index for chunk embeddings.                       |

### Required for the multimodal stack (R4–R6)

| Component       | Why                                                    |
| --------------- | ------------------------------------------------------ |
| `ffmpeg` + `ffprobe` | Frame extraction and audio demux for R6 video creative tests. macOS: `brew install ffmpeg`. Debian/Ubuntu: `apt-get install ffmpeg`. |
| OpenAI API key  | Vision (GPT-4o) and audio transcription (Whisper). Same `OPENAI_API_KEY` is used for both. |

### Optional

| Component | Why                                                                  |
| --------- | -------------------------------------------------------------------- |
| Ollama    | If you want to run LLM locally instead of OpenAI. Set `LLM_BASE_URL` accordingly. |
| Docker    | The repo ships a `docker-compose.yml` for Postgres + pgvector locally. |

---

## Quick start (local development)

### 1. Clone and enter

```bash
git clone https://github.com/gerriarte/SintecticPredictionAi.git
cd SintecticPredictionAi
```

### 2. Bring up Postgres (Docker)

```bash
docker compose up -d
# Postgres 16 + pgvector listening on localhost:5432
# Default URL: postgresql://mirofish:mirofish@localhost:5432/mirofish
```

If you already have Postgres locally, install pgvector and create a DB:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# apply migrations (idempotent)
psql "$DATABASE_URL" -f migrations/001_initial.sql
psql "$DATABASE_URL" -f migrations/002_clients.sql
```

### 4. Frontend

```bash
cd frontend
npm install
```

### 5. Configure environment

Create `.env` at the **repo root** (one level above `backend/`). Minimum viable config:

```bash
# --- LLM (vision + chat + Whisper) ---
LLM_API_KEY=sk-...                   # OpenAI key, also used by Whisper
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o                # gpt-4o for multimodal; gpt-4o-mini for text-only

# --- Persistence ---
DATABASE_URL=postgresql://mirofish:mirofish@localhost:5432/mirofish
GRAPH_BACKEND=postgres               # 'zep' is legacy; 'postgres' is the supported path
EMBEDDING_PROVIDER=openai            # or 'ollama'
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# --- Creative testing surface ---
CREATIVE_TESTING_ENABLED=true
CREATIVE_TESTING_MODE=mock           # 'mock' for free; 'live' to call GPT-4o per run

# --- Server ---
FLASK_HOST=0.0.0.0
FLASK_PORT=5001
FLASK_DEBUG=True
```

A complete reference is in `.env.example`.

### 6. Run

```bash
# Terminal 1 — backend
cd backend
.venv/bin/python run.py
# → Flask on http://localhost:5001

# Terminal 2 — frontend
cd frontend
npm run dev
# → Vite on http://localhost:3000 (auto-bumps to 3001/3002 if busy)
```

Open http://localhost:3000/, create a client from the home, and follow the **Context guide** (top-right pill) to load good context before launching a creative test.

---

## Environment variables — full reference

| Variable                       | Required                | Default              | Notes |
| ------------------------------ | ----------------------- | -------------------- | ----- |
| `LLM_API_KEY`                  | yes (live mode)         | —                    | OpenAI / Azure OpenAI / Ollama-compatible. Reused by Whisper. |
| `LLM_BASE_URL`                 | no                      | `https://api.openai.com/v1` | Override for Azure or Ollama. |
| `LLM_MODEL_NAME`               | yes                     | depends on Config    | `gpt-4o` for any modality with images or video. |
| `DATABASE_URL`                 | yes (when postgres)     | —                    | Standard `postgresql://...` URL. |
| `GRAPH_BACKEND`                | yes                     | `zep`                | Use `postgres`. `zep` is legacy. |
| `EMBEDDING_PROVIDER`           | when postgres           | `openai`             | `openai` or `ollama`. |
| `EMBEDDING_MODEL`              | when postgres           | `text-embedding-3-small` | Must match `EMBEDDING_DIM`. |
| `EMBEDDING_DIM`                | when postgres           | `1536`               | Vector column dim. Must match the model. |
| `CREATIVE_TESTING_ENABLED`     | yes (to use the surface)| `false`              | When `false`, `/api/report/creative-test/*` returns 404. |
| `CREATIVE_TESTING_MODE`        | yes                     | `mock`               | `mock` (deterministic, free) or `live` (calls LLM). |
| `MIROFISH_MAX_UPLOAD_MB`       | no                      | `200`                | Hard cap on uploads at the Flask layer. |
| `ZEP_API_KEY`                  | only when `GRAPH_BACKEND=zep` | —              | Legacy. Free tier rate-limits at 5 req/min — switch to postgres. |
| `FLASK_HOST` / `FLASK_PORT`    | no                      | `0.0.0.0` / `5001`   | |
| `FLASK_DEBUG`                  | no                      | `True`               | |

---

## Cost cheat-sheet (OpenAI public pricing, 2026-04, ~4 variants/run)

| Modality                         | Approx cost per creative test |
| -------------------------------- | ----------------------------- |
| Text-only                        | ~$0.04                        |
| Single image                     | ~$0.05–0.10                   |
| Carousel (5 images per variant)  | ~$0.20–0.50                   |
| Video (frames + Whisper)         | ~$0.60–1.50                   |

R6 video is the only modality that pushes beyond cents per run. Token-saving levers already applied in code: `MAX_SLIDES_PER_VARIANT=10`, `DEFAULT_MAX_FRAMES=8`, `MAX_AUDIO_SECONDS=300`.

---

## Testing

Pytest suite, ~2 seconds:

```bash
cd backend
.venv/bin/pytest tests/ -v
```

What it covers:

- `test_schema.py` — `parse_request` + `validate_request` for all four modalities; backend cap on slides per variant.
- `test_prompt_pack.py` — `build_messages` block counts and labels (`slide N` vs `frame N`); transcript truncation; base64 strip from JSON brief.
- `test_runner.py` — `_normalize_live_result` drops out-of-modality dims, clamps scores 0–100, sorts ranking descending.
- `test_mock_runner.py` — mock matches live shape per modality; deterministic output.
- `test_video_extractor.py` — ffmpeg integration on a generated test pattern (silent + with-audio); skips automatically when ffmpeg is absent.
- `test_api.py` — multipart parsing, `image_<L>_<idx>` ordering, disabled-flag short-circuit, image/video endpoint sanitisation.

### Live smoke against OpenAI real

A separate harness exercises the entire stack against the real LLM (and Whisper for video). Run from `backend/`:

```bash
OPENAI_API_KEY=sk-... \
  LLM_MODEL_NAME=gpt-4o \
  CREATIVE_TESTING_ENABLED=true \
  CREATIVE_TESTING_MODE=live \
  .venv/bin/python scripts/creative_test_smoke.py \
    --image path/to/sample.png \
    --video path/to/sample.mp4
```

Without flags it runs only the text-only variant (cost: cents). The script prints the normalised result and an audit that flags any modality-rule violations the model produced (e.g. visual scores on a text-only variant, missing required dim for a video).

---

## Project layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/                 # Flask blueprints
│   │   │   ├── clients.py       # multi-client CRUD + scoped projects/sims/reports
│   │   │   ├── creative_test.py # /api/report/creative-test/*  (R4-R6)
│   │   │   ├── graph.py         # /api/graph/* (ontology, build, data)
│   │   │   └── ...
│   │   ├── repositories/graph/  # Backend-agnostic graph layer
│   │   │   ├── postgres_backend.py  # Postgres + pgvector
│   │   │   └── zep_backend.py       # legacy
│   │   ├── services/
│   │   │   ├── creative_testing/    # schema, prompt_pack, runner, mock_runner, video_extractor, store
│   │   │   ├── clients.py
│   │   │   ├── clients_graph.py     # ingest_text + search + predict
│   │   │   ├── entity_reader.py     # factory: postgres or zep
│   │   │   ├── graph_tools.py       # factory: postgres or zep
│   │   │   ├── graph_ingest.py      # chunks → embed → LLM extract → upsert
│   │   │   └── ...
│   │   ├── utils/llm_client.py
│   │   └── ...
│   ├── migrations/
│   │   ├── 001_initial.sql      # graphs/nodes/edges/episodes/chunks
│   │   └── 002_clients.sql      # clients table
│   ├── scripts/
│   │   └── creative_test_smoke.py
│   ├── tests/
│   │   └── creative_testing/    # pytest suite (51 tests)
│   ├── run.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                 # axios clients
│   │   ├── components/
│   │   │   ├── shell/           # TopNav, Sidebar, Breadcrumb, CmdK
│   │   │   ├── ui/              # Button, Card, Badge, Icon, …
│   │   │   ├── graph/           # GraphCanvas (D3 force layout)
│   │   │   └── charts/          # RadarChart
│   │   ├── views/
│   │   │   ├── Home.vue
│   │   │   ├── ClientWorkspace.vue
│   │   │   ├── client/          # Overview, Context, CreativeTests, TestDetail, …
│   │   │   ├── Guide.vue        # /guide — context-loading guide for users
│   │   │   ├── Manual.vue       # /manual
│   │   │   ├── Help.vue         # /help — keyboard shortcuts
│   │   │   └── CreativeTestView.vue  # creative test wizard
│   │   ├── design/              # tokens, typography, components.css
│   │   └── router/index.js
│   ├── index.html
│   └── vite.config.js
├── locales/
│   ├── es.json
│   └── en.json
├── docs/
│   ├── RUNBOOK_CREATIVE_TESTING.md   # operational reference
│   ├── RUNBOOK_POSTGRES_BACKEND.md
│   └── …
├── docker-compose.yml
└── .env                         # NOT committed
```

---

## Operational notes

### Switching between Zep and Postgres

`GRAPH_BACKEND=zep` is the legacy path. The free tier of Zep Cloud rate-limits at 5 req/min, which makes graph builds fail mid-flight. Use `GRAPH_BACKEND=postgres` and skip Zep entirely.

### Restarting the backend after `.env` changes

Flask debug autoreload reloads code, **not env vars**. After editing `.env` you must stop and restart `python run.py`.

### Asset persistence (creative test images and videos)

Lives under `backend/uploads/creative_tests/<test_id>/{images,videos}/`. For multi-instance deploys mount this on shared storage or migrate to S3 (drop-in replacement of `_persist_slide` and `send_from_directory` in `app/api/creative_test.py`).

### Synchronous video extraction

`video_extractor.extract()` runs inside the worker thread of `/start`. A 200 MB video can take 30 s+ between ffmpeg and Whisper. Frontend `axios.timeout` is 10 min, but progress polling reports 0 % until extraction finishes. Acceptable for v1; planned improvement: a `progress_cb` call between extraction stages.

### Records on disk lose `image_data_url` by design

The base64 stays in memory only; persisted records (`backend/uploads/creative_tests/<id>.json`) carry only the relative `image_url`. Don't add code that expects to read base64 from those records.

---

## Troubleshooting

| Symptom                                                       | Cause / fix                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------ |
| `Batch 1 failed: ... Rate limit exceeded for FREE plan`       | `GRAPH_BACKEND` is `zep` (default). Set `GRAPH_BACKEND=postgres` and restart. |
| `creative-test/health` returns `enabled: false`               | Set `CREATIVE_TESTING_ENABLED=true` in `.env` and restart backend. |
| `/api/graph/data/<id>` returns 500 with traceback             | If the message references Zep but you're on postgres, rebuild the project on postgres backend (data was created in zep). |
| Video upload completes but no frames extracted                | `ffmpeg` not on PATH inside the worker process. Verify `which ffmpeg`. |
| Whisper silently empty                                        | `LLM_API_KEY` missing in the worker process. Confirm `.env` and restart. |
| `ModuleNotFoundError: No module named 'app.repositories.repositories'` | Stale build of `repositories/graph/postgres_backend.py`. Ensure you have the post-2026-04-30 fix. |
| Frontend shows "Lo.Bueno" anywhere                            | Stale Vite build. Run `npm run build` or hard-refresh dev server. |
| `pytest` skips `test_video_extractor.py`                       | ffmpeg/ffprobe not on PATH. Install ffmpeg. |

---

## Roadmap status (2026-04-30)

| Item                                                | Status      |
| --------------------------------------------------- | ----------- |
| R1–R6 (creative testing multimodal)                 | implemented |
| Audit fixes (postgres branch wiring, factory usage) | applied     |
| 51 automated tests + smoke harness                  | green       |
| Polish: Chinese strings in legacy wizards           | done (Process.vue user-visible) |
| Polish: full ES translation of `common.*`           | done        |
| **Live smoke against real OpenAI**                  | **pending — needs operator with API key** |
| **Async progress for video extraction**             | pending     |
| **Per-frame evidence linking in TestDetailTab**     | pending     |

---

## Lineage and credits

Sintetic Prediction AI is **an evolution built on top of MiroFish**. The relationship between the two projects:

| Layer                                                         | Owner            |
| ------------------------------------------------------------- | ---------------- |
| Multi-agent social simulation engine (OASIS adapter)          | **MiroFish** ([666ghj/MiroFish](https://github.com/666ghj/MiroFish)) |
| Knowledge graph build (entity + relation extraction over text) | MiroFish (extended for Postgres+pgvector by Sintetic) |
| Persona / Agent profile generation                            | MiroFish         |
| Dual-platform simulation runner (Twitter + Reddit)            | MiroFish         |
| Report Agent (post-simulation analysis)                       | MiroFish (kept; tools factory rewired for Postgres) |
| **Per-client model + workspace + sidebar/topnav redesign**    | **Sintetic**     |
| **Per-client knowledge graph + ingest_text + predict()**      | **Sintetic**     |
| **Creative testing surface (R1–R6 multimodal)**               | **Sintetic**     |
| **GPT-4o vision + Whisper integration**                       | **Sintetic**     |
| **Postgres + pgvector backend (replaces Zep Cloud)**          | **Sintetic**     |

If you remove the Sintetic layer, you have an enhanced MiroFish that runs on Postgres instead of Zep. If you remove MiroFish, you have a creative testing tool without the simulation engine that backs the agent runs.

The codebase intentionally preserves MiroFish's identity in the technical layer:
- Backend env vars are still prefixed `MIROFISH_*`.
- The simulation runner and report agent log under `mirofish.*` namespaces.
- `Powered by MiroFish` appears as an engine badge in the home view.
- Internal Python packages and database table prefixes (`mirofish_<graph_id>`) reference MiroFish.

The user-facing **product** is rebranded to **Sintetic Prediction AI**; the **engine attribution** remains MiroFish.

### Other credits

- **GPT-4o + Whisper** — OpenAI for vision, chat and audio transcription.
- **pgvector** — vector index for the per-client knowledge graph.
- **OASIS** ([camel-ai/oasis](https://github.com/camel-ai/oasis)) — the upstream multi-agent simulation framework that MiroFish wraps.
- **Sintetic Prediction AI** — product layer by [@gerriarte](https://github.com/gerriarte).

---

## License

This product layer is released under the same license as the upstream MiroFish engine. See `LICENSE` for details.
