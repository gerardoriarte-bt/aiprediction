"""
Contrato de entrada de Creative Testing.

Define el esquema obligatorio que el roadmap exige para cada corrida:
business_goal, audience_profile, scenario, creative_variants[], channels[],
success_metrics[]. Mantiene validaciones explicitas para guiar al planner
y evitar briefs incompletos (riesgo principal listado en el roadmap).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


class ValidationError(ValueError):
    """Error de validacion del brief de creative testing."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class AudienceProfile:
    name: str
    country: Optional[str] = None
    region: Optional[str] = None
    nse: Optional[str] = None
    age_range: Optional[str] = None
    primary_channel: Optional[str] = None
    sensitivities: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CreativeVariant:
    label: str
    headline: str
    body: Optional[str] = None
    cta: Optional[str] = None
    tone: Optional[str] = None
    visual_concept: Optional[str] = None
    # R4 — slide 0 (single-image case). Held in memory only.
    image_data_url: Optional[str] = None
    # R4 — relative URL for the persisted slide-0 asset.
    image_url: Optional[str] = None
    # R5 — additional slides for carousel variants. Each entry is
    # `{"data_url": str?, "url": str?}`; data_url stays out of the persisted
    # record. The full ordered slide sequence is `[image_url, *slides]`.
    slides: List[Dict[str, Any]] = field(default_factory=list)
    # R6 — relative URL for the persisted video asset (mp4/webm/...).
    # The UI uses it to render an HTML5 <video>; the LLM never sees it
    # directly — it only sees the extracted frames (loaded into `slides`)
    # and the transcript below.
    video_url: Optional[str] = None
    # R6 — Whisper transcript of the video's audio track. Empty when the
    # video has no audio or Whisper is unavailable.
    audio_transcript: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # image_data_url + slides[].data_url stay out of the persisted record
        # by convention — callers strip them before saving so the JSON file
        # does not balloon.
        return asdict(self)

    def is_carousel(self) -> bool:
        """True when the variant carries more than one slide."""
        return len(self.slides) >= 1 and bool(self.image_url or self.image_data_url)

    def is_video(self) -> bool:
        """True when the variant came from a video upload (R6)."""
        return bool(self.video_url)

    def all_image_data_urls(self) -> List[str]:
        """Ordered base64 data URLs for the LLM call (slide 0 first)."""
        out: List[str] = []
        if self.image_data_url:
            out.append(self.image_data_url)
        for s in self.slides:
            url = (s or {}).get("data_url")
            if url:
                out.append(url)
        return out

    def all_image_urls(self) -> List[str]:
        """Ordered served URLs for the UI (slide 0 first)."""
        out: List[str] = []
        if self.image_url:
            out.append(self.image_url)
        for s in self.slides:
            url = (s or {}).get("url")
            if url:
                out.append(url)
        return out


@dataclass
class SuccessMetric:
    name: str
    target: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CreativeTestRequest:
    business_goal: str
    scenario: str
    audience_profile: AudienceProfile
    creative_variants: List[CreativeVariant]
    channels: List[str]
    success_metrics: List[SuccessMetric]
    project_id: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_goal": self.business_goal,
            "scenario": self.scenario,
            "audience_profile": self.audience_profile.to_dict(),
            "creative_variants": [v.to_dict() for v in self.creative_variants],
            "channels": list(self.channels),
            "success_metrics": [m.to_dict() for m in self.success_metrics],
            "project_id": self.project_id,
            "notes": self.notes,
        }


# Limites alineados con el roadmap (Fase 1: 3-5 variantes minimas para comparativo).
MIN_VARIANTS = 2
MAX_VARIANTS = 8
MAX_CHANNELS = 10
MAX_METRICS = 10
# R5/R6 — cap on assets per variant. The full ordered sequence is
# `[image_url, *slides]`, so MAX_SLIDES_PER_VARIANT counts both. At ~765
# tokens per high-detail image this keeps the per-corrida vision cost
# bounded even if a power user uploads a long carousel.
MAX_SLIDES_PER_VARIANT = 10


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def parse_request(payload: Dict[str, Any]) -> CreativeTestRequest:
    """Convierte el JSON crudo en un CreativeTestRequest sin validar.

    La validacion completa (con mensajes accionables) se hace en
    validate_request, para que el endpoint pueda devolver una lista de
    errores util al wizard del frontend.
    """
    payload = payload or {}

    audience_raw = payload.get("audience_profile") or {}
    if not isinstance(audience_raw, dict):
        audience_raw = {}

    audience = AudienceProfile(
        name=_as_str(audience_raw.get("name")),
        country=_as_str(audience_raw.get("country")) or None,
        region=_as_str(audience_raw.get("region")) or None,
        nse=_as_str(audience_raw.get("nse")) or None,
        age_range=_as_str(audience_raw.get("age_range")) or None,
        primary_channel=_as_str(audience_raw.get("primary_channel")) or None,
        sensitivities=_as_str_list(audience_raw.get("sensitivities")),
        notes=_as_str(audience_raw.get("notes")) or None,
    )

    variants_raw = payload.get("creative_variants") or []
    if not isinstance(variants_raw, list):
        variants_raw = []
    variants: List[CreativeVariant] = []
    for idx, v in enumerate(variants_raw):
        if not isinstance(v, dict):
            continue
        slides_raw = v.get("slides") or []
        slides_list: List[Dict[str, Any]] = []
        if isinstance(slides_raw, list):
            for s in slides_raw:
                if not isinstance(s, dict):
                    continue
                entry: Dict[str, Any] = {}
                if s.get("url"):
                    entry["url"] = _as_str(s.get("url"))
                if s.get("data_url"):
                    entry["data_url"] = _as_str(s.get("data_url"))
                if entry:
                    slides_list.append(entry)
        # Defense-in-depth cap: slot 0 (image_url) + slides[] cannot exceed
        # MAX_SLIDES_PER_VARIANT. The wizard caps too, but a power user with
        # devtools or an automated client can bypass that.
        has_slot_zero = bool(_as_str(v.get("image_url")) or _as_str(v.get("image_data_url")))
        ceiling = MAX_SLIDES_PER_VARIANT - (1 if has_slot_zero else 0)
        if len(slides_list) > ceiling:
            slides_list = slides_list[:max(0, ceiling)]

        variants.append(
            CreativeVariant(
                label=_as_str(v.get("label")) or f"Variant {chr(ord('A') + idx)}",
                headline=_as_str(v.get("headline")),
                body=_as_str(v.get("body")) or None,
                cta=_as_str(v.get("cta")) or None,
                tone=_as_str(v.get("tone")) or None,
                visual_concept=_as_str(v.get("visual_concept")) or None,
                image_data_url=_as_str(v.get("image_data_url")) or None,
                image_url=_as_str(v.get("image_url")) or None,
                slides=slides_list,
                video_url=_as_str(v.get("video_url")) or None,
                audio_transcript=_as_str(v.get("audio_transcript")) or None,
            )
        )

    metrics_raw = payload.get("success_metrics") or []
    if not isinstance(metrics_raw, list):
        metrics_raw = []
    metrics: List[SuccessMetric] = []
    for m in metrics_raw:
        if isinstance(m, str):
            name = m.strip()
            if name:
                metrics.append(SuccessMetric(name=name))
        elif isinstance(m, dict):
            name = _as_str(m.get("name"))
            if name:
                metrics.append(
                    SuccessMetric(
                        name=name,
                        target=_as_str(m.get("target")) or None,
                        description=_as_str(m.get("description")) or None,
                    )
                )

    return CreativeTestRequest(
        business_goal=_as_str(payload.get("business_goal")),
        scenario=_as_str(payload.get("scenario")),
        audience_profile=audience,
        creative_variants=variants,
        channels=_as_str_list(payload.get("channels")),
        success_metrics=metrics,
        project_id=_as_str(payload.get("project_id")) or None,
        notes=_as_str(payload.get("notes")) or None,
    )


def validate_request(req: CreativeTestRequest) -> List[str]:
    """Devuelve lista de errores. Vacia significa brief valido."""
    errors: List[str] = []

    if not req.business_goal:
        errors.append("business_goal is required")
    if not req.scenario:
        errors.append("scenario is required")

    if not req.audience_profile or not req.audience_profile.name:
        errors.append("audience_profile.name is required")

    n = len(req.creative_variants)
    if n < MIN_VARIANTS:
        errors.append(f"creative_variants must have at least {MIN_VARIANTS} entries")
    elif n > MAX_VARIANTS:
        errors.append(f"creative_variants must have at most {MAX_VARIANTS} entries")
    for idx, v in enumerate(req.creative_variants):
        if not v.headline:
            errors.append(f"creative_variants[{idx}].headline is required")

    if not req.channels:
        errors.append("channels must include at least one entry")
    elif len(req.channels) > MAX_CHANNELS:
        errors.append(f"channels must have at most {MAX_CHANNELS} entries")

    if not req.success_metrics:
        errors.append("success_metrics must include at least one entry")
    elif len(req.success_metrics) > MAX_METRICS:
        errors.append(f"success_metrics must have at most {MAX_METRICS} entries")

    labels = [v.label for v in req.creative_variants]
    if len(set(labels)) != len(labels):
        errors.append("creative_variants labels must be unique")

    return errors
