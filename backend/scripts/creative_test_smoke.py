"""
End-to-end smoke for Creative Testing against a real LLM (and optionally
Whisper for video). Run from `backend/`:

    OPENAI_API_KEY=sk-... \\
    LLM_MODEL_NAME=gpt-4o \\
    CREATIVE_TESTING_ENABLED=true \\
    CREATIVE_TESTING_MODE=live \\
    .venv/bin/python scripts/creative_test_smoke.py

Optional: pass --image PATH and/or --video PATH to attach assets. With no
flags the script runs only the text-only modality, which keeps the cost
under one cent.

The script does NOT touch the persistence layer or threads — it calls the
runner directly and prints what the model returned + how the normaliser
shaped it. Use it to sanity-check that GPT-4o:
- Respects the rubric (visual scores absent for text-only variants).
- Maps slide labels back to evidence correctly.
- Returns valid JSON that the live path actually parses.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


# Make the `app` package importable when running this file directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        return f"data:{mime};base64,{base64.b64encode(fh.read()).decode('ascii')}"


def _build_brief(
    image_path: Optional[str],
    video_path: Optional[str],
    work_dir: str,
) -> Dict[str, Any]:
    """Build a minimal 3-variant brief that exercises text + (optional)
    image + (optional) video paths. Carousel is constructed by reusing the
    same image asset twice — enough to confirm the model honours slide
    ordering, not a marketing-quality test."""
    variants: List[Dict[str, Any]] = [
        {
            "label": "T",
            "headline": "Limited-time launch — ends Friday",
            "cta": "Shop now",
            "tone": "urgent",
        },
    ]

    if image_path:
        # Single image variant.
        variants.append({
            "label": "I",
            "headline": "Discover the new collection",
            "cta": "See more",
            "tone": "aspirational",
            "image_data_url": _data_url(image_path),
            "image_url": "/local/I_0",
        })
        # Carousel variant (reuse the asset twice so we do exercise R5).
        variants.append({
            "label": "C",
            "headline": "From day one to weekend ready",
            "cta": "Build your set",
            "tone": "narrative",
            "image_data_url": _data_url(image_path),
            "image_url": "/local/C_0",
            "slides": [
                {"data_url": _data_url(image_path), "url": "/local/C_1"},
            ],
        })

    if video_path:
        # Run the extractor on the user's video — tests the real R6 path.
        from app.services.creative_testing.video_extractor import extract

        ext = extract(video_path, os.path.join(work_dir, "video_work"), max_frames=4)
        if ext.frame_paths:
            slides = [
                {"data_url": _data_url(p), "url": f"/local/V_{i+1}"}
                for i, p in enumerate(ext.frame_paths[1:])
            ]
            variants.append({
                "label": "V",
                "headline": "See it in motion",
                "cta": "Watch",
                "tone": "energetic",
                "image_data_url": _data_url(ext.frame_paths[0]),
                "image_url": "/local/V_0",
                "slides": slides,
                "video_url": "/local/V.mp4",
                "audio_transcript": ext.audio_transcript or "",
            })
        else:
            print("[warn] video extraction returned no frames; skipping V variant")

    return {
        "business_goal": "Pick the launch claim for the spring drop",
        "scenario": "Spring 2026 launch in MX City; campaign window 2 weeks.",
        "audience_profile": {
            "name": "Urban 24–34",
            "country": "MX",
            "primary_channel": "instagram",
        },
        "creative_variants": variants,
        "channels": ["instagram", "tiktok"],
        "success_metrics": [{"name": "CTR"}, {"name": "add-to-cart"}],
    }


def _audit(normalized: Dict[str, Any], brief: Dict[str, Any]) -> List[str]:
    """Sanity-check the model's output against expectations."""
    issues: List[str] = []
    expected = {v["label"]: v for v in brief["creative_variants"]}
    seen = {v["label"] for v in normalized.get("variants") or []}

    for lbl in expected:
        if lbl not in seen:
            issues.append(f"variant {lbl} missing from result")

    for v in normalized.get("variants") or []:
        lbl = v["label"]
        spec = expected.get(lbl, {})
        n_images = (1 if spec.get("image_url") else 0) + len(spec.get("slides") or [])
        is_video = bool(spec.get("video_url"))
        has_transcript = bool(spec.get("audio_transcript"))
        scores = v.get("scores") or {}

        if n_images == 0:
            for k in ("visual_composition_score", "visual_legibility_score",
                      "visual_narrative_coherence_score", "video_pacing_score",
                      "audio_message_alignment_score"):
                if k in scores:
                    issues.append(f"{lbl}: text-only variant should not carry {k}")
        if n_images >= 1:
            for k in ("visual_composition_score", "visual_legibility_score"):
                if k not in scores:
                    issues.append(f"{lbl}: missing {k} (n_images={n_images})")
        if n_images >= 2 and "visual_narrative_coherence_score" not in scores:
            issues.append(f"{lbl}: missing visual_narrative_coherence_score")
        if not is_video and "video_pacing_score" in scores:
            issues.append(f"{lbl}: non-video should not carry video_pacing_score")
        if is_video and "video_pacing_score" not in scores:
            issues.append(f"{lbl}: video missing video_pacing_score")
        if is_video and has_transcript and "audio_message_alignment_score" not in scores:
            issues.append(f"{lbl}: video w/ transcript missing audio_message_alignment_score")
        if not (is_video and has_transcript) and "audio_message_alignment_score" in scores:
            issues.append(f"{lbl}: should not carry audio_message_alignment_score")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Creative Testing live smoke")
    parser.add_argument("--image", type=str, default=None, help="Path to test image")
    parser.add_argument("--video", type=str, default=None, help="Path to test video")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("LLM_API_KEY"):
        print("[err] OPENAI_API_KEY or LLM_API_KEY must be set", file=sys.stderr)
        return 2

    # Force live mode for this run (independent of the global config).
    os.environ.setdefault("CREATIVE_TESTING_ENABLED", "true")
    os.environ.setdefault("CREATIVE_TESTING_MODE", "live")
    os.environ.setdefault("LLM_MODEL_NAME", "gpt-4o")

    from app.services.creative_testing.runner import run_live
    from app.services.creative_testing.schema import parse_request, validate_request

    with tempfile.TemporaryDirectory(prefix="ct_smoke_") as work:
        brief = _build_brief(args.image, args.video, work)
        req = parse_request(brief)
        errors = validate_request(req)
        if errors:
            print("[err] brief did not validate:", errors, file=sys.stderr)
            return 2

        print(f"[info] running live with {len(req.creative_variants)} variants:",
              [v.label for v in req.creative_variants])

        def progress(stage: str, pct: int, message: str):
            print(f"  [{pct:>3}%] {stage}: {message}")

        result = run_live(req, progress_cb=progress)

    print("\n=== Normalised result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    issues = _audit(result, brief)
    print("\n=== Audit ===")
    if issues:
        for i in issues:
            print(f"  - {i}")
        return 1
    print("  no issues — scoring respects modality rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
