"""
Tests for parse_request / validate_request across the four modalities.

These tests own the contract between the wizard payload and the rest of
the pipeline. If they break, the wizard and the LLM stop seeing the same
brief — which is exactly the bug class we cannot ship.
"""

from app.services.creative_testing.schema import (
    CreativeVariant,
    parse_request,
    validate_request,
)


def _base_payload(variants):
    return {
        "business_goal": "launch X",
        "scenario": "Black Friday MX",
        "audience_profile": {"name": "jovenes 18-24"},
        "creative_variants": variants,
        "channels": ["instagram"],
        "success_metrics": ["CTR"],
    }


# ---------- text-only --------------------------------------------------------


def test_parse_text_only_variant():
    req = parse_request(_base_payload([
        {"label": "A", "headline": "h1"},
        {"label": "B", "headline": "h2"},
    ]))
    assert validate_request(req) == []
    assert all(not v.is_video() for v in req.creative_variants)
    assert all(not v.is_carousel() for v in req.creative_variants)
    assert all(v.all_image_data_urls() == [] for v in req.creative_variants)


# ---------- single image (R4) ------------------------------------------------


def test_parse_single_image_variant():
    req = parse_request(_base_payload([
        {
            "label": "A", "headline": "h1",
            "image_data_url": "data:image/png;base64,abc",
            "image_url": "/img/A.png",
        },
        {"label": "B", "headline": "h2"},
    ]))
    a, b = req.creative_variants
    assert a.image_data_url == "data:image/png;base64,abc"
    assert a.all_image_data_urls() == ["data:image/png;base64,abc"]
    assert a.all_image_urls() == ["/img/A.png"]
    assert not a.is_carousel()  # need 2+ slides
    assert not a.is_video()
    assert b.all_image_data_urls() == []


# ---------- carousel (R5) ----------------------------------------------------


def test_parse_carousel_variant():
    req = parse_request(_base_payload([
        {
            "label": "A", "headline": "h1",
            "image_data_url": "data:image/png;base64,a0",
            "image_url": "/img/A_0.png",
            "slides": [
                {"data_url": "data:image/png;base64,a1", "url": "/img/A_1.png"},
                {"data_url": "data:image/png;base64,a2", "url": "/img/A_2.png"},
            ],
        },
    ]))
    (a,) = req.creative_variants
    assert a.is_carousel()
    assert not a.is_video()
    assert a.all_image_data_urls() == [
        "data:image/png;base64,a0",
        "data:image/png;base64,a1",
        "data:image/png;base64,a2",
    ]
    assert a.all_image_urls() == ["/img/A_0.png", "/img/A_1.png", "/img/A_2.png"]


def test_carousel_slides_without_data_url_are_kept_for_persisted_url():
    """When loading a record from disk we lose the data_url (in-memory only)
    but the persisted url stays. all_image_data_urls drops missing entries."""
    req = parse_request(_base_payload([
        {
            "label": "A", "headline": "h1",
            "image_url": "/img/A_0.png",
            "slides": [
                {"url": "/img/A_1.png"},
                {"url": "/img/A_2.png"},
            ],
        },
    ]))
    (a,) = req.creative_variants
    assert a.all_image_urls() == ["/img/A_0.png", "/img/A_1.png", "/img/A_2.png"]
    assert a.all_image_data_urls() == []  # nothing to feed the LLM


# ---------- video (R6) -------------------------------------------------------


def test_parse_video_variant():
    req = parse_request(_base_payload([
        {
            "label": "V", "headline": "h1",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V_frame_00.jpg",
            "slides": [
                {"data_url": "data:image/jpeg;base64,f1", "url": "/img/V_frame_01.jpg"},
            ],
            "video_url": "/api/.../V.mp4",
            "audio_transcript": "buy now and save",
        },
        {"label": "T", "headline": "h2"},
    ]))
    v, t = req.creative_variants
    assert v.is_video()
    assert v.is_carousel()  # video with 2 frames is also "carousel-like"
    assert v.audio_transcript == "buy now and save"
    assert v.video_url.endswith("/V.mp4")
    assert not t.is_video()
    assert t.audio_transcript is None


# ---------- validation -------------------------------------------------------


def test_validate_rejects_missing_headline():
    req = parse_request(_base_payload([
        {"label": "A", "headline": ""},
        {"label": "B", "headline": "h2"},
    ]))
    errors = validate_request(req)
    assert any("headline" in e for e in errors)


def test_validate_rejects_duplicate_labels():
    req = parse_request(_base_payload([
        {"label": "A", "headline": "h1"},
        {"label": "A", "headline": "h2"},
    ]))
    errors = validate_request(req)
    assert any("unique" in e for e in errors)


def test_validate_requires_min_two_variants():
    req = parse_request(_base_payload([
        {"label": "A", "headline": "h1"},
    ]))
    errors = validate_request(req)
    assert any("at least" in e for e in errors)


def test_validate_caps_eight_variants():
    req = parse_request(_base_payload([
        {"label": chr(ord("A") + i), "headline": f"h{i}"} for i in range(9)
    ]))
    errors = validate_request(req)
    assert any("at most" in e for e in errors)


# ---------- helper sanity ----------------------------------------------------


def test_creative_variant_helpers_match_field_state():
    v = CreativeVariant(label="A", headline="h", video_url="/x.mp4")
    # video_url alone (no frames yet) — is_video True, is_carousel False
    assert v.is_video()
    assert not v.is_carousel()


def test_parse_caps_slides_per_variant():
    """Backend defense-in-depth cap: image_url + slides[] cannot exceed
    MAX_SLIDES_PER_VARIANT (10) regardless of what the wizard sends."""
    req = parse_request(_base_payload([
        {
            "label": "A", "headline": "h",
            "image_url": "/img/A_0.png",
            "slides": [
                {"url": f"/img/A_{i}.png"} for i in range(20)
            ],
        },
        {"label": "B", "headline": "h"},
    ]))
    a = req.creative_variants[0]
    # Slot 0 + 9 slides = 10 total assets.
    assert len(a.all_image_urls()) == 10


def test_parse_caps_slides_when_no_slot_zero():
    """When image_url is missing, all 10 may live in slides[]."""
    req = parse_request(_base_payload([
        {
            "label": "A", "headline": "h",
            "slides": [
                {"url": f"/img/A_{i}.png"} for i in range(20)
            ],
        },
        {"label": "B", "headline": "h"},
    ]))
    a = req.creative_variants[0]
    assert len(a.all_image_urls()) == 10
