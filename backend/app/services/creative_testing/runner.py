"""
Runner de Creative Testing.

Expone una funcion `run` que recibe el brief y un callback de progreso
y devuelve el resultado final (mismo contrato para mock y live).

- MockRunner: simula etapas con pequenas pausas para validar la UX de
  progreso del frontend (Paso 2 del UX_CREATIVE_TESTING_EXPERIENCE).
- LiveRunner: llama al LLM con el prompt_pack. Si el LLM falla o devuelve
  JSON invalido, cae al MockRunner para no romper la corrida (REGLAS §7).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from ...utils.logger import get_logger
from .mock_runner import generate_mock_result
from .prompt_pack import build_messages
from .schema import CreativeTestRequest


logger = get_logger("mirofish.creative_testing.runner")


ProgressCallback = Callable[[str, int, str], None]


# Etapas declaradas en el UX_CREATIVE_TESTING_EXPERIENCE Paso 2:
# planificacion -> evaluacion -> scoring -> composicion.
STAGES: List[Dict[str, Any]] = [
    {"key": "planning", "weight": 10},
    {"key": "evaluating", "weight": 35},
    {"key": "scoring", "weight": 30},
    {"key": "composing", "weight": 25},
]


def _emit(progress_cb: Optional[ProgressCallback], stage: str, pct: int, message: str):
    if progress_cb is None:
        return
    try:
        progress_cb(stage, pct, message)
    except Exception:
        # un callback roto no debe matar la corrida
        logger.exception("progress callback raised; continuing")


def _fetch_client_facts(
    client_id: Optional[str],
    request: CreativeTestRequest,
    limit: int = 12,
) -> List[str]:
    """Pull top facts from the client graph relevant to this brief.

    Returns an empty list when there is no client_id, no graph yet, or
    the search call fails — callers must treat absence as benign.
    """
    if not client_id:
        return []
    try:
        from ..clients_graph import ClientGraphService

        audience_name = request.audience_profile.name if request.audience_profile else ""
        query = " ".join(
            filter(
                None,
                [request.business_goal or "", request.scenario or "", audience_name],
            )
        ).strip() or "brand context"
        result = ClientGraphService.search(client_id, query, limit=limit)
        facts = list(result.get("facts") or [])
        # Dedupe and trim to keep the prompt focused.
        seen = set()
        unique: List[str] = []
        for f in facts:
            if f and f not in seen:
                seen.add(f)
                unique.append(f)
        return unique
    except Exception as e:
        logger.info(f"client facts unavailable for {client_id}: {e}")
        return []


def run_mock(
    request: CreativeTestRequest,
    progress_cb: Optional[ProgressCallback] = None,
    step_delay: float = 0.6,
    client_facts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Mock con etapas. step_delay configurable para tests rapidos.

    Cuando se pasan client_facts, se exponen como result.client_context_facts
    para que el frontend los muestre en la sección de Evidence.
    """
    cumulative = 0
    for stage in STAGES:
        cumulative += stage["weight"]
        _emit(progress_cb, stage["key"], min(cumulative, 95), f"{stage['key']}...")
        time.sleep(step_delay)

    result = generate_mock_result(request)
    if client_facts:
        result["client_context_facts"] = list(client_facts)
    _emit(progress_cb, "completed", 100, "completed")
    return result


def run_live(
    request: CreativeTestRequest,
    progress_cb: Optional[ProgressCallback] = None,
    client_facts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Live: usa LLMClient.chat_json. Cae a mock ante cualquier error.

    Si se pasan client_facts, el prompt incluye un bloque de "client
    context" para que el modelo razone con la memoria del cliente y
    cite los hechos en su rationale.
    """
    def _mock_with_warning(reason: str) -> Dict[str, Any]:
        result = run_mock(request, progress_cb, client_facts=client_facts)
        result.setdefault("_warnings", []).append(f"Ran in mock mode: {reason}.")
        return result

    try:
        from ...utils.llm_client import LLMClient
    except Exception as e:
        logger.warning(f"LLMClient unavailable, falling back to mock: {e}")
        return _mock_with_warning(f"LLMClient unavailable ({e})")

    _emit(progress_cb, "planning", 10, "drafting prompt")

    try:
        client = LLMClient()
    except Exception as e:
        logger.warning(f"LLMClient init failed, falling back to mock: {e}")
        return _mock_with_warning(f"LLMClient init failed ({e})")

    _emit(progress_cb, "evaluating", 30, "calling LLM")

    try:
        messages = build_messages(request, facts=client_facts or [])
        raw = client.chat_json(messages=messages, temperature=0.3, max_tokens=4096)
    except Exception as e:
        logger.warning(f"LLM call failed, falling back to mock: {e}")
        return _mock_with_warning(f"LLM call failed ({e})")

    _emit(progress_cb, "scoring", 70, "parsing response")

    normalized = _normalize_live_result(raw, request)
    if normalized is None:
        logger.warning("LLM returned malformed JSON; falling back to mock")
        return _mock_with_warning("LLM returned malformed JSON")

    if client_facts:
        normalized["client_context_facts"] = list(client_facts)

    _emit(progress_cb, "composing", 90, "composing recommendation")
    _emit(progress_cb, "completed", 100, "completed")
    return normalized


def run(
    mode: str,
    request: CreativeTestRequest,
    progress_cb: Optional[ProgressCallback] = None,
    client_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Punto de entrada unico. mode in {'mock','live'}.

    Cuando viene client_id, busca hasta 12 facts relevantes del grafo
    del cliente y los pasa al runner correspondiente. Si el cliente no
    tiene grafo o la búsqueda falla, sigue sin contexto extra.
    """
    facts = _fetch_client_facts(client_id, request)
    if mode == "live":
        return run_live(request, progress_cb, client_facts=facts)
    return run_mock(request, progress_cb, client_facts=facts)


# ---------------------------------------------------------------------------
# Normalizacion del JSON devuelto por el LLM
# ---------------------------------------------------------------------------


_REQUIRED_DIMS = (
    "message_clarity_score",
    "audience_fit_score",
    "conversion_intent_score",
    "brand_risk_score",
)

# R4 — image-only dimensions; only meaningful when the variant has an asset.
_VISUAL_DIMS = (
    "visual_composition_score",
    "visual_legibility_score",
)

# R5 — carousel-only dimension (2+ slides).
_CAROUSEL_DIM = "visual_narrative_coherence_score"

# R6 — video-only dimensions.
_VIDEO_PACING_DIM = "video_pacing_score"
_AUDIO_ALIGN_DIM = "audio_message_alignment_score"


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _coerce_recommendation(value: Any) -> str:
    v = _coerce_str(value).strip().lower()
    if v in ("activate", "iterate", "discard"):
        return v
    return "iterate"


def _coerce_risk_level(value: Any) -> str:
    v = _coerce_str(value).strip().lower()
    if v in ("low", "medium", "high"):
        return v
    return "medium"


def _normalize_live_result(
    raw: Dict[str, Any], request: CreativeTestRequest
) -> Optional[Dict[str, Any]]:
    """Normaliza el dict devuelto por el LLM al contrato esperado.

    Devuelve None si la forma es irrecuperable; el caller debe caer al mock.
    """
    if not isinstance(raw, dict):
        return None

    raw_variants = raw.get("variants") or []
    if not isinstance(raw_variants, list) or not raw_variants:
        return None

    # Map variant labels in the request to image/video state. Only variants
    # with an image carry visual scores; only multi-frame variants carry
    # coherence; only video variants carry pacing; only video variants with a
    # transcript carry audio alignment.
    image_count_by_label = {
        v.label: len(v.all_image_data_urls()) for v in (request.creative_variants or [])
    }
    image_urls_by_label = {
        v.label: v.all_image_urls() for v in (request.creative_variants or [])
    }
    is_video_by_label = {
        v.label: v.is_video() for v in (request.creative_variants or [])
    }
    has_transcript_by_label = {
        v.label: bool(v.audio_transcript) for v in (request.creative_variants or [])
    }
    video_url_by_label = {
        v.label: v.video_url for v in (request.creative_variants or [])
    }
    transcript_by_label = {
        v.label: v.audio_transcript for v in (request.creative_variants or [])
    }

    norm_variants: List[Dict[str, Any]] = []
    for v in raw_variants:
        if not isinstance(v, dict):
            continue
        scores_raw = v.get("scores") or {}
        if not isinstance(scores_raw, dict):
            scores_raw = {}
        scores = {dim: max(0, min(100, _coerce_int(scores_raw.get(dim)))) for dim in _REQUIRED_DIMS}
        label = _coerce_str(v.get("label")) or "?"
        n_images = image_count_by_label.get(label, 0)
        is_multi = n_images >= 2
        is_video = is_video_by_label.get(label, False)
        has_transcript = has_transcript_by_label.get(label, False)
        if n_images >= 1:
            for dim in _VISUAL_DIMS:
                scores[dim] = max(0, min(100, _coerce_int(scores_raw.get(dim))))
        if is_multi:
            scores[_CAROUSEL_DIM] = max(
                0, min(100, _coerce_int(scores_raw.get(_CAROUSEL_DIM)))
            )
        if is_video:
            scores[_VIDEO_PACING_DIM] = max(
                0, min(100, _coerce_int(scores_raw.get(_VIDEO_PACING_DIM)))
            )
        if is_video and has_transcript:
            scores[_AUDIO_ALIGN_DIM] = max(
                0, min(100, _coerce_int(scores_raw.get(_AUDIO_ALIGN_DIM)))
            )
        clarity = scores["message_clarity_score"]
        fit = scores["audience_fit_score"]
        intent = scores["conversion_intent_score"]
        risk = scores["brand_risk_score"]
        bonus = 0.0
        if n_images >= 1:
            bonus += 0.5 * (
                scores["visual_composition_score"] + scores["visual_legibility_score"]
            )
        if is_multi:
            bonus += 0.5 * scores[_CAROUSEL_DIM]
        if is_video:
            bonus += 0.5 * scores[_VIDEO_PACING_DIM]
        if is_video and has_transcript:
            bonus += 0.5 * scores[_AUDIO_ALIGN_DIM]
        default_total = int(round(clarity + fit + intent + bonus - risk))
        total = _coerce_int(v.get("total_score"), default=default_total)

        norm_variants.append(
            {
                "label": label,
                "headline": _coerce_str(v.get("headline")),
                "scores": scores,
                "total_score": total,
                "risk_level": _coerce_risk_level(v.get("risk_level")),
                "recommendation": _coerce_recommendation(v.get("recommendation")),
                "rationale": _coerce_str(v.get("rationale")),
                "evidence": v.get("evidence") if isinstance(v.get("evidence"), list) else [],
                "image_url": (image_urls_by_label.get(label) or [None])[0],
                "image_urls": image_urls_by_label.get(label) or [],
                "video_url": video_url_by_label.get(label),
                "audio_transcript": transcript_by_label.get(label),
            }
        )

    if not norm_variants:
        return None

    norm_variants.sort(key=lambda x: x["total_score"], reverse=True)

    ranking = [
        {"rank": i + 1, "label": item["label"], "total_score": item["total_score"]}
        for i, item in enumerate(norm_variants)
    ]
    winner = norm_variants[0]

    summary = raw.get("summary") if isinstance(raw.get("summary"), dict) else {}
    summary = {
        "business_goal": _coerce_str(summary.get("business_goal")) or request.business_goal,
        "audience": _coerce_str(summary.get("audience")) or request.audience_profile.name,
        "winner_label": _coerce_str(summary.get("winner_label")) or winner["label"],
        "winner_recommendation": _coerce_recommendation(
            summary.get("winner_recommendation") or winner["recommendation"]
        ),
    }

    risks = raw.get("risks") if isinstance(raw.get("risks"), list) else []
    next_steps = raw.get("next_steps") if isinstance(raw.get("next_steps"), list) else []

    return {
        "mode": "live",
        "summary": summary,
        "ranking": ranking,
        "variants": norm_variants,
        "channels": list(request.channels),
        "success_metrics": [m.to_dict() for m in request.success_metrics],
        "risks": risks,
        "next_steps": [str(s) for s in next_steps if s],
    }
