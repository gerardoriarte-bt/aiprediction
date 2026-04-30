"""
Tests for generate_mock_result.

Mock is what the frontend hits when CREATIVE_TESTING_MODE=mock or when the
LLM call fails. It must produce the same shape as the live runner — same
variant fields, same dim presence rules — otherwise the UI breaks when
falling back to mock.
"""

from app.services.creative_testing.mock_runner import generate_mock_result
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


def _by_label(result, label):
    return next(v for v in result["variants"] if v["label"] == label)


def test_text_only_has_only_4_base_dims():
    req = _req([
        {"label": "A", "headline": "h"}, {"label": "B", "headline": "h"},
    ])
    res = generate_mock_result(req)
    a = _by_label(res, "A")
    assert set(a["scores"].keys()) == {
        "message_clarity_score", "audience_fit_score",
        "conversion_intent_score", "brand_risk_score",
    }
    assert a["image_urls"] == []
    assert a["video_url"] is None
    assert a["audio_transcript"] is None


def test_single_image_adds_visual_dims_only():
    req = _req([
        {
            "label": "A", "headline": "h",
            "image_data_url": "data:image/png;base64,a",
            "image_url": "/img/A.png",
        },
        {"label": "B", "headline": "h"},
    ])
    res = generate_mock_result(req)
    a = _by_label(res, "A")
    assert "visual_composition_score" in a["scores"]
    assert "visual_legibility_score" in a["scores"]
    assert "visual_narrative_coherence_score" not in a["scores"]
    assert "video_pacing_score" not in a["scores"]


def test_carousel_adds_narrative_coherence():
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
    res = generate_mock_result(req)
    a = res["variants"][0]
    assert "visual_narrative_coherence_score" in a["scores"]
    assert "video_pacing_score" not in a["scores"]
    assert a["image_urls"] == ["/img/A_0.png", "/img/A_1.png"]


def test_video_adds_pacing_and_audio_align_when_transcript():
    req = _req([
        {
            "label": "V", "headline": "h",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V_0.jpg",
            "slides": [
                {"data_url": "data:image/jpeg;base64,f1", "url": "/img/V_1.jpg"},
            ],
            "video_url": "/x.mp4",
            "audio_transcript": "vo text",
        },
    ])
    res = generate_mock_result(req)
    v = res["variants"][0]
    assert "video_pacing_score" in v["scores"]
    assert "audio_message_alignment_score" in v["scores"]
    assert v["video_url"] == "/x.mp4"
    assert v["audio_transcript"] == "vo text"


def test_video_without_transcript_skips_audio_align():
    req = _req([
        {
            "label": "V", "headline": "h",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V_0.jpg",
            "video_url": "/x.mp4",
            # no audio_transcript
        },
        {"label": "T", "headline": "h"},
    ])
    res = generate_mock_result(req)
    v = _by_label(res, "V")
    assert "video_pacing_score" in v["scores"]
    assert "audio_message_alignment_score" not in v["scores"]


def test_mock_is_deterministic_per_brief():
    """Same brief twice => same scores. The mock seeds on a hash, so this
    should be stable regardless of process order or hash randomisation."""
    payload = [
        {"label": "A", "headline": "h1"},
        {"label": "B", "headline": "h2"},
    ]
    res1 = generate_mock_result(_req(payload))
    res2 = generate_mock_result(_req(payload))
    s1 = {v["label"]: v["scores"] for v in res1["variants"]}
    s2 = {v["label"]: v["scores"] for v in res2["variants"]}
    assert s1 == s2


def test_mock_marks_mode_as_mock():
    res = generate_mock_result(_req([
        {"label": "A", "headline": "h"}, {"label": "B", "headline": "h"},
    ]))
    assert res["mode"] == "mock"
    assert "summary" in res
    assert "ranking" in res
