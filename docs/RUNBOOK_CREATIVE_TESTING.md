# Runbook — Creative Testing (R1–R6)

Operational reference for shipping the multi-client multimodal Creative Testing surface to production. Pair with `RUNBOOK_POSTGRES_BACKEND.md` for the persistence layer.

## What ships in this surface

| Stage | Asset on each variant            | Extra dimensions added                                                      |
| ----- | -------------------------------- | --------------------------------------------------------------------------- |
| R3    | text only                        | none (4 base dims: clarity / fit / intent / risk)                           |
| R4    | one image                        | `visual_composition_score`, `visual_legibility_score`                       |
| R5    | 2–10 images (carousel)           | + `visual_narrative_coherence_score`                                        |
| R6    | one video (auto-extracted frames + Whisper transcript) | + `video_pacing_score`, + `audio_message_alignment_score` (only if transcript present) |

Variants in a single brief can mix modalities — the runner chooses the right rubric per variant.

## System requirements

### Required

- **Python 3.11+** (3.12 tested).
- **PostgreSQL with pgvector** for the per-client knowledge graph (see `RUNBOOK_POSTGRES_BACKEND.md`).
- **`ffmpeg` and `ffprobe` on PATH** — needed for R6. Without them, video uploads degrade gracefully (variant becomes text-only) but the operator should know.
  - macOS: `brew install ffmpeg`
  - Debian/Ubuntu: `apt-get install ffmpeg`
  - Alpine: `apk add ffmpeg`
  - Docker: add `RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*` to your Dockerfile.

### Optional but strongly recommended

- **OpenAI API access** — used for both vision (GPT-4o) and audio transcription (Whisper). Without it the live runner falls back to mock and R6 leaves transcripts empty.

## Environment variables

| Variable                      | Required | Default                | Purpose                                                                                          |
| ----------------------------- | -------- | ---------------------- | ------------------------------------------------------------------------------------------------ |
| `OPENAI_API_KEY` / `LLM_API_KEY` | yes (live) | unset               | Used by both `LLMClient` and `video_extractor` (Whisper). Either name is accepted.               |
| `LLM_MODEL_NAME`              | yes      | depends on Config       | Set to `gpt-4o` for any modality with images or video. Cheaper text-only models work for R3.    |
| `LLM_BASE_URL`                | no       | OpenAI                 | Override for Azure OpenAI or compatible providers.                                               |
| `CREATIVE_TESTING_ENABLED`    | yes      | `false`                | Master flag. When `false`, all `/api/report/creative-test/*` routes return 404.                  |
| `CREATIVE_TESTING_MODE`       | yes      | `mock`                 | `mock` (deterministic, no LLM cost) or `live` (calls GPT-4o).                                    |
| `DATABASE_URL`                | yes      | unset                  | Postgres connection. Without it, the `/api/clients/*` routes return 503 and creative-test rejects with `client_id is required`. |

## Costs (OpenAI public pricing, 2026-04, ~4 variants/run)

| Modality           | Approx cost / corrida |
| ------------------ | --------------------- |
| R3 text-only       | ~$0.04                |
| R4 single image    | ~$0.05–0.10           |
| R5 carousel (5 imgs/variant) | ~$0.20–0.50  |
| R6 video (frames + Whisper)  | ~$0.60–1.50  |

R6 is the only modality that hits "USD per corrida" territory. At 50 runs/day with a mix that skews to R6, expect ~$30–75/day. Token-saving levers we already apply: `MAX_SLIDES_PER_VARIANT=10`, `DEFAULT_MAX_FRAMES=8`, `MAX_AUDIO_SECONDS=300`.

## Smoke test — does this actually work end-to-end?

There is a manual smoke harness that hits the LLM (and Whisper for video) without going through Flask. Run from `backend/` after exporting your env:

```bash
OPENAI_API_KEY=sk-... \
  LLM_MODEL_NAME=gpt-4o \
  CREATIVE_TESTING_ENABLED=true \
  CREATIVE_TESTING_MODE=live \
  .venv/bin/python scripts/creative_test_smoke.py \
    --image path/to/sample.png \
    --video path/to/sample.mp4
```

Without flags it runs only the text-only variant (cost: cents). The script prints the normalised result and an audit that flags any modality-rule violations the model produced (e.g. visual scores on a text-only variant).

## Automated tests

```bash
cd backend
.venv/bin/pytest tests/ -v
```

51 tests in <2s as of 2026-04-30. Coverage:

- `test_schema.py` — `parse_request` + `validate_request` for all four modalities; backend cap on slides per variant.
- `test_prompt_pack.py` — `build_messages` block counts and labels (`slide N` vs `frame N`); transcript truncation; base64 strip.
- `test_runner.py` — `_normalize_live_result` drops out-of-modality dims, clamps scores, sorts ranking.
- `test_mock_runner.py` — mock matches live shape per modality; deterministic output.
- `test_video_extractor.py` — ffmpeg integration on a generated test pattern (silent + with-audio); skips automatically when ffmpeg is absent.
- `test_api.py` — multipart parsing, `image_<L>_<idx>` ordering, disabled-flag short-circuit, image/video endpoint sanitisation.

## Known caveats

- **Synchronous video extraction.** `video_extractor.extract()` runs inside the worker thread of `/start`. A 200 MB video can take 30 s+ between ffmpeg and Whisper. The frontend `axios.timeout` is 10 min, but progress polling stays at 0 % until extraction finishes. Future work: a `progress_cb` call between extraction stages.
- **Asset persistence is filesystem-based.** Images live under `uploads/creative_tests/<test_id>/images/`, videos under `uploads/creative_tests/<test_id>/videos/`. For multi-instance deploys mount this on shared storage or migrate to S3 (drop-in if you replace `_persist_slide` and `send_from_directory`).
- **Whisper is best-effort.** If the API call fails or no audio is detected, the variant is recorded with `audio_transcript=None` and `audio_message_alignment_score` is dropped — the rest of the run continues.
- **Records on disk lose `image_data_url` by design.** The base64 stays in memory only; persisted records carry only the relative `image_url`. Don't add code that expects to read base64 from `creative_tests/<id>.json`.

## Where to look when something breaks

- LLM returned malformed JSON → `runner.run_live` falls back to `run_mock` and logs `LLM call failed, falling back to mock`. Inspect logs for the raw payload.
- Variant arrived without expected dims → check `runner._normalize_live_result`; the variant's modality is inferred from the request fields, not from what the LLM returned.
- ffmpeg in container but not on PATH → `video_extractor._ffmpeg_available()` short-circuits and you get an empty extraction. Check `which ffmpeg` inside the container.
- Whisper silently empty → confirm `OPENAI_API_KEY` is set in the worker process (not just in the shell that started it).
