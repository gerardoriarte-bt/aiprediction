"""
Tests for build_messages — the LLM input contract.

The shape of the messages is what GPT-4o actually consumes. Asserting on it
guards us against silent regressions where the LLM stops seeing the images
or the labels (in which case scores look plausible but are blind).
"""

from app.services.creative_testing.prompt_pack import build_messages, build_user_prompt
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


def _user_blocks(req):
    """Helper: returns the user-message content as a list of blocks
    regardless of whether it's a string or a multimodal list."""
    msgs = build_messages(req)
    user = msgs[1]
    content = user["content"]
    return content if isinstance(content, list) else [{"type": "text", "text": content}]


def _block_types(blocks):
    return [b.get("type") for b in blocks if isinstance(b, dict)]


def _block_texts(blocks):
    return [b["text"] for b in blocks if isinstance(b, dict) and b.get("type") == "text"]


# ---------- text-only --------------------------------------------------------


def test_text_only_emits_string_content():
    req = _req([
        {"label": "A", "headline": "h1"},
        {"label": "B", "headline": "h2"},
    ])
    msgs = build_messages(req)
    # Two messages: system + user. User is a plain string.
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert isinstance(msgs[1]["content"], str)


# ---------- imagen single ----------------------------------------------------


def test_single_image_emits_one_image_block():
    req = _req([
        {
            "label": "A", "headline": "h1",
            "image_data_url": "data:image/png;base64,xxx",
            "image_url": "/img/A.png",
        },
        {"label": "B", "headline": "h2"},
    ])
    blocks = _user_blocks(req)
    assert _block_types(blocks).count("image_url") == 1
    # Slide label is "slide 0" for non-video
    assert "[Variant A slide 0]" in _block_texts(blocks)


# ---------- carrusel ---------------------------------------------------------


def test_carousel_emits_one_block_per_slide_in_order():
    req = _req([
        {
            "label": "A", "headline": "h1",
            "image_data_url": "data:image/png;base64,a0",
            "image_url": "/img/A_0.png",
            "slides": [
                {"data_url": "data:image/png;base64,a1", "url": "/img/A_1.png"},
                {"data_url": "data:image/png;base64,a2", "url": "/img/A_2.png"},
            ],
        },
    ])
    blocks = _user_blocks(req)
    assert _block_types(blocks).count("image_url") == 3
    texts = _block_texts(blocks)
    # Order matters; the model relies on it to map evidence to slides.
    assert texts.index("[Variant A slide 0]") < texts.index("[Variant A slide 1]") < texts.index("[Variant A slide 2]")


# ---------- video ------------------------------------------------------------


def test_video_uses_frame_label_not_slide():
    req = _req([
        {
            "label": "V", "headline": "h1",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V_frame_00.jpg",
            "slides": [
                {"data_url": "data:image/jpeg;base64,f1", "url": "/img/V_frame_01.jpg"},
            ],
            "video_url": "/api/.../V.mp4",
            "audio_transcript": "voiceover text",
        },
    ])
    blocks = _user_blocks(req)
    texts = _block_texts(blocks)
    assert "[Variant V frame 0]" in texts
    assert "[Variant V frame 1]" in texts
    # Negative: never use 'slide' for video.
    assert not any("[Variant V slide" in t for t in texts)


def test_video_transcript_appears_in_user_text():
    req = _req([
        {
            "label": "V", "headline": "h1",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V_frame_00.jpg",
            "video_url": "/api/.../V.mp4",
            "audio_transcript": "limited time only",
        },
        {"label": "T", "headline": "text-only"},
    ])
    text = build_user_prompt(req)
    assert "Audio transcripts" in text
    assert "[Variant V transcript]" in text
    assert "limited time only" in text
    # T has no transcript → no leak into the prompt
    assert "[Variant T transcript]" not in text


def test_transcript_is_truncated_at_1500_chars():
    long_text = "a" * 5000
    req = _req([
        {
            "label": "V", "headline": "h1",
            "image_data_url": "data:image/jpeg;base64,f0",
            "image_url": "/img/V.jpg",
            "video_url": "/x.mp4",
            "audio_transcript": long_text,
        },
        {"label": "T", "headline": "h2"},
    ])
    text = build_user_prompt(req)
    # The full 5000-char string never appears; the truncated form ends with …
    assert long_text not in text
    assert "…" in text


# ---------- inline image strip ----------------------------------------------


def test_image_data_urls_are_stripped_from_text_prompt():
    """The base64 must NOT travel inside the JSON brief embedded in the text
    prompt — only as proper image content blocks. Otherwise the prompt
    explodes and the model gets confused."""
    big_b64 = "data:image/png;base64," + ("Q" * 4000)
    req = _req([
        {
            "label": "A", "headline": "h1",
            "image_data_url": big_b64,
            "image_url": "/img/A.png",
            "slides": [
                {"data_url": "data:image/png;base64," + ("Z" * 4000),
                 "url": "/img/A_1.png"},
            ],
        },
    ])
    text = build_user_prompt(req)
    assert "QQQQ" not in text
    assert "ZZZZ" not in text
    # The relative URL (small, useful) must stay so the LLM can cite slides.
    assert "/img/A_0.png" not in text  # we did not declare A_0 in payload
    assert "/img/A.png" in text  # but we did declare this one
    assert "/img/A_1.png" in text


# ---------- mixed brief ------------------------------------------------------


def test_mixed_brief_emits_correct_block_counts():
    """One text-only, one single-image, one carousel-of-2, one video-with-3
    frames-and-transcript. End-to-end count: 1+2+3 = 6 image blocks; the
    video has 3 frames + 2 base = 6 image blocks total counting all visual
    variants. Audio transcript appears once."""
    req = _req([
        {"label": "T", "headline": "text"},
        {
            "label": "I", "headline": "image",
            "image_data_url": "data:image/png;base64,i0",
            "image_url": "/img/I.png",
        },
        {
            "label": "C", "headline": "carousel",
            "image_data_url": "data:image/png;base64,c0",
            "image_url": "/img/C_0.png",
            "slides": [
                {"data_url": "data:image/png;base64,c1", "url": "/img/C_1.png"},
            ],
        },
        {
            "label": "V", "headline": "video",
            "image_data_url": "data:image/jpeg;base64,v0",
            "image_url": "/img/V_0.jpg",
            "slides": [
                {"data_url": "data:image/jpeg;base64,v1", "url": "/img/V_1.jpg"},
                {"data_url": "data:image/jpeg;base64,v2", "url": "/img/V_2.jpg"},
            ],
            "video_url": "/x.mp4",
            "audio_transcript": "audio",
        },
    ])
    blocks = _user_blocks(req)
    # I=1 + C=2 + V=3 = 6 image blocks
    assert _block_types(blocks).count("image_url") == 6
    texts = _block_texts(blocks)
    # Video is labelled with 'frame', the other multi-asset is labelled 'slide'.
    assert "[Variant V frame 0]" in texts
    assert "[Variant C slide 0]" in texts
    # Transcript only mentioned for V.
    assert any("[Variant V transcript]" in t for t in texts)
    assert not any("[Variant T transcript]" in t for t in texts)
