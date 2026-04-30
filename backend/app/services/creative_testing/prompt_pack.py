"""
Prompt pack retail/eCommerce para Creative Testing - Fase 1.

Define los prompts y el contrato de salida JSON que el LiveRunner exige al LLM.
La forma del JSON resultante coincide con la del MockRunner para que el
frontend trate ambos casos de manera identica.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .schema import CreativeTestRequest


SYSTEM_PROMPT = """You are a senior creative strategist working inside an
in-house agency for retail and eCommerce brands. Your job is to evaluate
creative variants against a defined audience and output a decision-ready
comparison.

Operating principles:
- Prioritise actionable judgment over narrative.
- Anchor every score in the audience profile, scenario, and channel mix.
- Surface brand-safety and compliance risks explicitly when present.
- Be conservative with "activate" recommendations; lean to "iterate" when
  evidence is mixed; "discard" only when material risks are detected.
- Output MUST be a valid JSON object that follows the requested schema
  exactly. Do not include prose outside the JSON.
"""


# El esquema de salida es el contrato unificado: lo respeta el mock y lo
# debe respetar el LLM en modo live.
OUTPUT_SCHEMA_HINT = """{
  "summary": {
    "business_goal": "string",
    "audience": "string",
    "winner_label": "string",
    "winner_recommendation": "activate | iterate | discard"
  },
  "ranking": [
    { "rank": 1, "label": "string", "total_score": 0 }
  ],
  "variants": [
    {
      "label": "string",
      "headline": "string",
      "scores": {
        "message_clarity_score": 0,
        "audience_fit_score": 0,
        "conversion_intent_score": 0,
        "brand_risk_score": 0,
        "visual_composition_score": 0,
        "visual_legibility_score": 0,
        "visual_narrative_coherence_score": 0,
        "video_pacing_score": 0,
        "audio_message_alignment_score": 0
      },
      "total_score": 0,
      "risk_level": "low | medium | high",
      "recommendation": "activate | iterate | discard",
      "rationale": "string",
      "evidence": [
        {
          "segment": "string",
          "finding": "string",
          "impact": "string",
          "next_action": "string"
        }
      ]
    }
  ],
  "channels": ["string"],
  "success_metrics": [
    { "name": "string", "target": "string|null", "description": "string|null" }
  ],
  "risks": [
    {
      "type": "string",
      "level": "info | low | medium | high",
      "description": "string"
    }
  ],
  "next_steps": ["string"]
}

Note on visual scores:
- visual_composition_score and visual_legibility_score MUST be reported only
  when at least one image was attached for that variant (see "Visual asset"
  blocks attached as image content). When no image is attached, set both to
  null and ignore them in total_score.
- visual_narrative_coherence_score MUST be reported only when 2+ frames are
  attached (carousel or video). Otherwise set to null.
- video_pacing_score MUST be reported only for VIDEO variants. The "Visual
  assets" block names which variants are video. Otherwise set to null.
- audio_message_alignment_score MUST be reported only when an audio
  transcript is present in the brief for that variant. Otherwise null.
"""


SCORE_RUBRIC = """Scoring rubric (0-100 for each dimension, integer):
- message_clarity_score: how unambiguous and memorable the core message is.
- audience_fit_score: how well the variant resonates with the declared audience.
- conversion_intent_score: how strongly it pushes the audience toward the
  declared success metrics.
- brand_risk_score: HIGHER means HIGHER brand risk (claim issues, compliance,
  fatigue, reputational exposure). Use it as a penalty in your ranking.
- visual_composition_score (image-only): balance, focal hierarchy and brand
  coherence of the attached image(s). For carousels, average across slides.
  ONLY score when at least one image is attached.
- visual_legibility_score (image-only): how legible the headline/CTA are over
  the visual at thumbnail and feed-scroll sizes. For carousels, average across
  slides. ONLY score when at least one image is attached.
- visual_narrative_coherence_score (carousel/video): how well the slides or
  frames flow as a sequence — setup → tension → payoff or whatever narrative
  the variant attempts. Penalise jumps, repetition, and confusing order. ONLY
  score when 2+ slides/frames are attached.
- video_pacing_score (video-only): rhythm and edit cadence across the
  extracted frames. Penalise dead frames or overcuts. ONLY score for video
  variants.
- audio_message_alignment_score (video-only, transcript present): how well the
  voiceover or on-screen audio reinforces the visual claim. ONLY score when an
  audio transcript is provided.

Total score:
- text-only variants: total_score = clarity + fit + intent - risk.
- single-image variants: total_score = clarity + fit + intent + 0.5 * (
  composition + legibility) - risk.
- carousel variants: total_score = clarity + fit + intent + 0.5 * (
  composition + legibility) + 0.5 * narrative_coherence - risk.
- video variants: total_score = clarity + fit + intent + 0.5 * (
  composition + legibility) + 0.5 * narrative_coherence + 0.5 * pacing
  + 0.5 * audio_alignment - risk. Drop any term whose dimension is null.
Use it to sort the ranking (higher first).
Map risk_level: <=30 brand_risk_score = low, 31-60 = medium, >60 = high.
Map recommendation: total_score >= 180 AND risk_level != high => activate;
total_score >= 120 OR risk_level == medium => iterate; otherwise discard.

When images are attached, ground at least one evidence[] entry on a concrete
visual observation (color, focal point, legibility issue, brand element).
For carousels, ground at least one entry on the slide-to-slide flow.
"""


def _strip_inline_images(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Drop heavy/long fields from the brief that goes into the text prompt.

    - Image bytes travel separately as vision content blocks; embedding the
      base64 (slide 0 or any carousel slide) would explode the prompt.
    - audio_transcript is rendered (truncated) under its own dedicated
      "Audio transcripts" section. Leaving it inside the JSON brief would
      duplicate it untruncated and blow the context window on long videos.
    """
    safe = dict(payload)
    variants = []
    for v in safe.get("creative_variants") or []:
        v2 = dict(v)
        v2.pop("image_data_url", None)
        v2.pop("audio_transcript", None)
        slides_clean = []
        for s in (v2.get("slides") or []):
            if not isinstance(s, dict):
                continue
            s2 = {k: val for k, val in s.items() if k != "data_url"}
            slides_clean.append(s2)
        v2["slides"] = slides_clean
        # image_url + slides[].url stay — short relative URLs useful to map
        # evidence back to a slide when the model cites a specific frame.
        variants.append(v2)
    safe["creative_variants"] = variants
    return safe


def build_user_prompt(
    request: CreativeTestRequest,
    facts: Optional[List[str]] = None,
) -> str:
    """Renderiza el brief estructurado como prompt de usuario.

    Cuando se pasan `facts` (extraídos del grafo del cliente), se inyecta
    un bloque "Client context" que el modelo debe consultar al razonar y
    citar en las `evidence` por variante.
    """
    payload = _strip_inline_images(request.to_dict())
    parts = [
        "Evaluate the creative variants below against the declared audience "
        "and scenario. Apply the scoring rubric and return ONLY the JSON object "
        "described in the schema.",
        "",
        f"=== Brief ===\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
    ]
    if facts:
        bullets = "\n".join(f"- {f}" for f in facts[:20])
        parts += [
            "",
            "=== Client context (facts on file for this brand) ===",
            bullets,
            "",
            "When a fact above directly supports or contradicts a variant, cite it "
            "verbatim inside that variant's `evidence[].finding` field, and adjust "
            "scores so the variant best aligned with the client's existing context "
            "ranks higher (and any variant that conflicts with it carries a higher "
            "brand_risk_score).",
        ]

    image_variants = [v for v in request.creative_variants if v.all_image_data_urls()]
    if image_variants:
        descriptors = []
        any_multi = False
        any_video = False
        for v in image_variants:
            n = len(v.all_image_data_urls())
            if v.is_video():
                descriptors.append(f"{v.label} (video, {n} frames)")
                any_multi = True
                any_video = True
            elif n >= 2:
                descriptors.append(f"{v.label} (carousel, {n} slides)")
                any_multi = True
            else:
                descriptors.append(f"{v.label} (single image)")
        guidance = (
            f"Images for variants {', '.join(descriptors)} are attached AFTER "
            "this brief as image content blocks. Each image is preceded by a "
            "text label like '[Variant A slide 0]' (or 'frame 0' for video). "
            "Score visual_composition_score and visual_legibility_score for "
            "any variant with at least one image."
        )
        if any_multi:
            guidance += (
                " For carousel/video variants (2+ slides), also score "
                "visual_narrative_coherence_score."
            )
        if any_video:
            guidance += (
                " For video variants, also score video_pacing_score; if an "
                "audio transcript was provided in the brief for that variant, "
                "additionally score audio_message_alignment_score."
            )
        parts += ["", "=== Visual assets ===", guidance]

    transcript_variants = [
        v for v in request.creative_variants if v.audio_transcript
    ]
    if transcript_variants:
        parts.append("")
        parts.append("=== Audio transcripts (for video variants) ===")
        for v in transcript_variants:
            snippet = v.audio_transcript.strip()
            if len(snippet) > 1500:
                snippet = snippet[:1500].rsplit(" ", 1)[0] + "…"
            parts.append(f"[Variant {v.label} transcript]")
            parts.append(snippet)

    parts += [
        "",
        f"=== Output schema ===\n{OUTPUT_SCHEMA_HINT}",
        "",
        f"=== Rubric ===\n{SCORE_RUBRIC}",
    ]
    return "\n".join(parts)


def build_messages(
    request: CreativeTestRequest,
    facts: Optional[List[str]] = None,
) -> list:
    """Build chat messages, switching to multimodal content when any variant
    has an image_data_url attached. The OpenAI Python SDK accepts an array of
    content blocks for vision models — text first, then one image_url block
    per variant in declaration order, prefixed with a tiny text label so the
    model can map image -> variant unambiguously.
    """
    user_text = build_user_prompt(request, facts=facts)

    image_variants = [v for v in request.creative_variants if v.all_image_data_urls()]
    if not image_variants:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]

    user_content: List[Dict[str, Any]] = [{"type": "text", "text": user_text}]
    for v in image_variants:
        slot_word = "frame" if v.is_video() else "slide"
        for idx, data_url in enumerate(v.all_image_data_urls()):
            user_content.append(
                {"type": "text", "text": f"[Variant {v.label} {slot_word} {idx}]"}
            )
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": data_url, "detail": "high"},
                }
            )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
