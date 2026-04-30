"""
Tests for _normalize_live_result.

This is the function that decides which dimensions live in the final record
and how total_score is computed. It MUST drop dimensions that don't apply
(visual scores on a text-only variant should never appear) and it MUST keep
the totals consistent with the rubric the LLM was given.
"""

from app.services.creative_testing.runner import _normalize_live_result
from app.services.creative_testing.schema import parse_request


def _req(variants):
    return parse_request({
        "business_goal": "g",
        "scenario": "s",
        "audience_profile": {"name": "aud"},
        "creative_variants": variants,
        "channels": ["instagram"],
        "success_metrics": ["CTR"],
    })


def _llm_variant(label, scores, headline="h", reco="iterate", risk_level="medium"):
    return {
        "label": label,
        "headline": headline,
        "scores": scores,
        "risk_level": risk_level,
        "recommendation": reco,
        "rationale": "r",
        "evidence": [],
    }


# ---------- malformed input -------------------------------------------------


def test_returns_none_when_raw_is_not_dict():
    assert _normalize_live_result([], _req([
        {"label": "A", "headline": "h"}, {"label": "B", "headline": "h"}
    ])) is None


def test_returns_none_when_no_variants():
    req = _req([{"label": "A", "headline": "h"}, {"label": "B", "headline": "h"}])
    assert _normalize_live_result({"variants": []}, req) is None
    assert _normalize_live_result({"variants": "not-a-list"}, req) is None


# ---------- text-only --------------------------------------------------------


def test_text_only_keeps_4_base_dims_only():
    req = _req([
        {"label": "A", "headline": "h"},
        {"label": "B", "headline": "h"},
    ])
    raw = {"variants": [
        _llm_variant("A", {
            "message_clarity_score": 70, "audience_fit_score": 80,
            "conversion_intent_score": 75, "brand_risk_score": 20,
            # LLM hallucinated a visual score; we must IGNORE it for text-only.
            "visual_composition_score": 90,
        }),
        _llm_variant("B", {
            "message_clarity_score": 60, "audience_fit_score": 65,
            "conversion_intent_score": 55, "brand_risk_score": 25,
        }),
    ]}
    res = _normalize_live_result(raw, req)
    assert res is not None
    a = next(v for v in res["variants"] if v["label"] == "A")
    assert set(a["scores"].keys()) == {
        "message_clarity_score", "audience_fit_score",
        "conversion_intent_score", "brand_risk_score",
    }
    # Default total when omitted: clarity + fit + intent - risk = 70+80+75-20 = 205
    assert a["total_score"] == 205


# ---------- single image ----------------------------------------------------


def test_single_image_keeps_visual_dims_drops_carousel_dim():
    req = _req([
        {
            "label": "A", "headline": "h",
            "image_data_url": "data:image/png;base64,a",
            "image_url": "/img/A.png",
        },
        {"label": "B", "headline": "h"},
    ])
    raw = {"variants": [
        _llm_variant("A", {
            "message_clarity_score": 70, "audience_fit_score": 80,
            "conversion_intent_score": 75, "brand_risk_score": 20,
            "visual_composition_score": 85, "visual_legibility_score": 90,
            # Hallucinated coherence; must drop because only 1 slide.
            "visual_narrative_coherence_score": 99,
        }),
        _llm_variant("B", {"message_clarity_score": 60, "audience_fit_score": 65,
                           "conversion_intent_score": 55, "brand_risk_score": 25}),
    ]}
    res = _normalize_live_result(raw, req)
    a = next(v for v in res["variants"] if v["label"] == "A")
    assert "visual_composition_score" in a["scores"]
    assert "visual_legibility_score" in a["scores"]
    assert "visual_narrative_coherence_score" not in a["scores"]
    # Total: clarity+fit+intent + 0.5*(comp+leg) - risk
    # = 70+80+75 + 0.5*(85+90) - 20 = 225 + 87.5 - 20 = 292.5 → 292 or 293 (rounded)
    assert a["total_score"] in (292, 293)
    # Single-image variant's image_url roundtrip
    assert a["image_url"] == "/img/A.png"
    assert a["image_urls"] == ["/img/A.png"]


# ---------- carrusel ---------------------------------------------------------


def test_carousel_keeps_coherence_drops_video_dims():
    req = _req([
        {
            "label": "A", "headline": "h",
            "image_data_url": "data:image/png;base64,a0",
            "image_url": "/img/A_0.png",
            "slides": [
                {"data_url": "data:image/png;base64,a1", "url": "/img/A_1.png"},
            ],
        },
    ])
    raw = {"variants": [
        _llm_variant("A", {
            "message_clarity_score": 70, "audience_fit_score": 80,
            "conversion_intent_score": 75, "brand_risk_score": 20,
            "visual_composition_score": 85, "visual_legibility_score": 90,
            "visual_narrative_coherence_score": 80,
            # Hallucinated video dims; must drop.
            "video_pacing_score": 95, "audio_message_alignment_score": 95,
        }),
    ]}
    res = _normalize_live_result(raw, req)
    a = res["variants"][0]
    assert "visual_narrative_coherence_score" in a["scores"]
    assert "video_pacing_score" not in a["scores"]
    assert "audio_message_alignment_score" not in a["scores"]
    assert a["image_urls"] == ["/img/A_0.png", "/img/A_1.png"]


# ---------- video con transcript --------------------------------------------


def test_video_with_transcript_keeps_all_video_dims():
    req = _req([
        {
            "label": "V", "headline": "h",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V_0.jpg",
            "slides": [
                {"data_url": "data:image/jpeg;base64,f1", "url": "/img/V_1.jpg"},
            ],
            "video_url": "/x.mp4",
            "audio_transcript": "voice over",
        },
    ])
    raw = {"variants": [
        _llm_variant("V", {
            "message_clarity_score": 70, "audience_fit_score": 80,
            "conversion_intent_score": 75, "brand_risk_score": 20,
            "visual_composition_score": 85, "visual_legibility_score": 90,
            "visual_narrative_coherence_score": 80,
            "video_pacing_score": 75, "audio_message_alignment_score": 88,
        }),
    ]}
    res = _normalize_live_result(raw, req)
    v = res["variants"][0]
    assert set(v["scores"].keys()) == {
        "message_clarity_score", "audience_fit_score",
        "conversion_intent_score", "brand_risk_score",
        "visual_composition_score", "visual_legibility_score",
        "visual_narrative_coherence_score",
        "video_pacing_score", "audio_message_alignment_score",
    }
    assert v["video_url"] == "/x.mp4"
    assert v["audio_transcript"] == "voice over"
    # Total = 70+80+75 + 0.5*(85+90) + 0.5*80 + 0.5*75 + 0.5*88 - 20 = 414
    assert v["total_score"] == 414


def test_video_without_transcript_drops_audio_align():
    req = _req([
        {
            "label": "V", "headline": "h",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V_0.jpg",
            "slides": [
                {"data_url": "data:image/jpeg;base64,f1", "url": "/img/V_1.jpg"},
            ],
            "video_url": "/x.mp4",
            # no audio_transcript
        },
    ])
    raw = {"variants": [
        _llm_variant("V", {
            "message_clarity_score": 70, "audience_fit_score": 80,
            "conversion_intent_score": 75, "brand_risk_score": 20,
            "visual_composition_score": 85, "visual_legibility_score": 90,
            "visual_narrative_coherence_score": 80, "video_pacing_score": 75,
            # Hallucinated audio_align without transcript: must drop.
            "audio_message_alignment_score": 95,
        }),
    ]}
    res = _normalize_live_result(raw, req)
    v = res["variants"][0]
    assert "video_pacing_score" in v["scores"]
    assert "audio_message_alignment_score" not in v["scores"]


# ---------- coercion + clamping ---------------------------------------------


def test_scores_are_clamped_to_0_100_and_coerced():
    req = _req([
        {"label": "A", "headline": "h"}, {"label": "B", "headline": "h"},
    ])
    raw = {"variants": [
        _llm_variant("A", {
            "message_clarity_score": 999,        # over -> 100
            "audience_fit_score": -50,           # under -> 0
            "conversion_intent_score": "75",     # string -> 75
            "brand_risk_score": "abc",           # garbage -> 0
        }),
        _llm_variant("B", {
            "message_clarity_score": 60, "audience_fit_score": 65,
            "conversion_intent_score": 55, "brand_risk_score": 25,
        }),
    ]}
    res = _normalize_live_result(raw, req)
    a = next(v for v in res["variants"] if v["label"] == "A")
    assert a["scores"]["message_clarity_score"] == 100
    assert a["scores"]["audience_fit_score"] == 0
    assert a["scores"]["conversion_intent_score"] == 75
    assert a["scores"]["brand_risk_score"] == 0


def test_ranking_is_sorted_descending_by_total():
    req = _req([
        {"label": "A", "headline": "h"},
        {"label": "B", "headline": "h"},
        {"label": "C", "headline": "h"},
    ])
    raw = {"variants": [
        _llm_variant("A", {"message_clarity_score": 50, "audience_fit_score": 50,
                            "conversion_intent_score": 50, "brand_risk_score": 50}),
        _llm_variant("B", {"message_clarity_score": 90, "audience_fit_score": 90,
                            "conversion_intent_score": 90, "brand_risk_score": 10}),
        _llm_variant("C", {"message_clarity_score": 70, "audience_fit_score": 70,
                            "conversion_intent_score": 70, "brand_risk_score": 20}),
    ]}
    res = _normalize_live_result(raw, req)
    labels = [r["label"] for r in res["ranking"]]
    assert labels == ["B", "C", "A"]
