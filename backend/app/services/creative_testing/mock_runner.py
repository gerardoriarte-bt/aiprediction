"""
Mock runner deterministico para la rebanada vertical (Stage C).

No llama al LLM, no toca el grafo Zep ni el report_agent. Genera una
respuesta sintetica con la forma esperada de Fase 2 (ranking + scorecards
+ recomendacion) para validar el contrato end-to-end del frontend antes
de cablear el motor real en la siguiente entrega.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from .schema import CreativeTestRequest


_SCORE_DIMENSIONS = (
    "message_clarity_score",
    "audience_fit_score",
    "conversion_intent_score",
    "brand_risk_score",
)


def _seed(request: CreativeTestRequest, label: str, dim: str) -> int:
    h = hashlib.sha1(
        f"{request.business_goal}|{request.audience_profile.name}|{label}|{dim}".encode("utf-8")
    ).hexdigest()
    return int(h[:6], 16)


def _score(request: CreativeTestRequest, label: str, dim: str) -> int:
    base = _seed(request, label, dim) % 41  # 0..40
    if dim == "brand_risk_score":
        # invertimos: riesgo bajo = puntaje alto
        return 60 + base
    return 55 + base


def _risk_level(brand_risk: int) -> str:
    if brand_risk >= 85:
        return "low"
    if brand_risk >= 70:
        return "medium"
    return "high"


def _recommendation(total: int, risk_level: str) -> str:
    if risk_level == "high":
        return "iterate"
    if total >= 320:
        return "activate"
    if total >= 280:
        return "iterate"
    return "discard"


def generate_mock_result(request: CreativeTestRequest) -> Dict[str, Any]:
    variants_out: List[Dict[str, Any]] = []
    for v in request.creative_variants:
        scores = {dim: _score(request, v.label, dim) for dim in _SCORE_DIMENSIONS}
        all_urls = v.all_image_urls()
        all_data = v.all_image_data_urls()
        n_images = max(len(all_urls), len(all_data))
        if n_images >= 1:
            scores["visual_composition_score"] = _score(request, v.label, "visual_composition_score")
            scores["visual_legibility_score"] = _score(request, v.label, "visual_legibility_score")
        if n_images >= 2:
            scores["visual_narrative_coherence_score"] = _score(
                request, v.label, "visual_narrative_coherence_score"
            )
        if v.is_video():
            scores["video_pacing_score"] = _score(request, v.label, "video_pacing_score")
            if v.audio_transcript:
                scores["audio_message_alignment_score"] = _score(
                    request, v.label, "audio_message_alignment_score"
                )
        total = sum(scores.values())
        risk_level = _risk_level(scores["brand_risk_score"])
        variants_out.append(
            {
                "label": v.label,
                "headline": v.headline,
                "scores": scores,
                "total_score": total,
                "risk_level": risk_level,
                "recommendation": _recommendation(total, risk_level),
                "rationale": (
                    f"Mock rationale for {v.label}: high-level fit with "
                    f"{request.audience_profile.name}; "
                    f"brand risk {risk_level}."
                ),
                "evidence": [
                    {
                        "segment": request.audience_profile.name,
                        "finding": f"{v.label} resonates around the headline framing.",
                        "impact": "expected lift in CTR",
                        "next_action": "test in preferred channel",
                    }
                ],
                "image_url": (all_urls or [None])[0],
                "image_urls": all_urls,
                "video_url": v.video_url,
                "audio_transcript": v.audio_transcript,
            }
        )

    variants_out.sort(key=lambda x: x["total_score"], reverse=True)

    ranking = [
        {"rank": i + 1, "label": item["label"], "total_score": item["total_score"]}
        for i, item in enumerate(variants_out)
    ]

    winner = variants_out[0] if variants_out else None

    return {
        "mode": "mock",
        "summary": {
            "business_goal": request.business_goal,
            "audience": request.audience_profile.name,
            "winner_label": winner["label"] if winner else None,
            "winner_recommendation": winner["recommendation"] if winner else None,
        },
        "ranking": ranking,
        "variants": variants_out,
        "channels": list(request.channels),
        "success_metrics": [m.to_dict() for m in request.success_metrics],
        "risks": [
            {
                "type": "incomplete_brief",
                "level": "info",
                "description": (
                    "Mock output: this is a placeholder until the scoring engine "
                    "is wired in Phase 2."
                ),
            }
        ],
        "next_steps": [
            "Review mock ranking for plausibility against the brief.",
            "When backend scoring is enabled, re-run to obtain LLM-backed evidence.",
        ],
    }
