"""
Tests for the /api/report/creative-test/start endpoint multipart parser.

Covers what unit tests can't: the actual Werkzeug parsing of multipart
fields, the `image_<L>_<idx>` ordering, and the disabled-flag short-circuit.
We patch the service-layer hooks so we don't actually run the LLM, the
clients module, or the threaded worker — we only assert that the endpoint
shapes the request correctly.
"""

import io
import json

import pytest

import app.api.creative_test as ct_api


@pytest.fixture(autouse=True)
def _enable_flag(monkeypatch):
    monkeypatch.setattr(ct_api.Config, "CREATIVE_TESTING_ENABLED", True)
    monkeypatch.setattr(ct_api.Config, "CREATIVE_TESTING_MODE", "mock")


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Replace the heavy parts of the start endpoint so we can assert on
    what got attached to the request without running threads or saving
    files. Returns a dict captured by the stubs."""
    captured = {}

    # Skip client lookup (no DB in tests).
    class _ClientService:
        @staticmethod
        def get_client(client_id):
            captured["client_id"] = client_id
            return {"client_id": client_id, "name": "Test Client"}

    monkeypatch.setattr(
        "app.services.clients.ClientService.get_client",
        _ClientService.get_client,
    )

    # Capture the request that would have been persisted + queued.
    def _save(record):
        captured.setdefault("saves", []).append(record)
        return record
    monkeypatch.setattr(ct_api.CreativeTestStore, "save", _save)
    monkeypatch.setattr(ct_api.CreativeTestStore, "new_id", lambda: "ctest_TEST")

    # Don't start a real thread; capture the parsed request that would run.
    import threading
    monkeypatch.setattr(threading, "Thread", lambda *a, **kw: type(
        "FakeThread", (), {"start": lambda self: None, "daemon": True}
    )())

    # Skip task manager.
    class _TM:
        def create_task(self, **kw):
            captured["task_meta"] = kw.get("metadata")
            return "task_TEST"
    monkeypatch.setattr(ct_api, "TaskManager", lambda: _TM())

    # Stub video extraction so we don't shell out to ffmpeg in this suite.
    def _fake_extract(video_path, work_dir, max_frames=8):
        captured.setdefault("extract_calls", []).append(video_path)

        class R:
            frame_paths = []
            audio_transcript = None
            duration_seconds = None
        return R()
    monkeypatch.setattr(
        "app.services.creative_testing.video_extractor.extract",
        _fake_extract,
    )

    return captured


def _valid_brief(client_id="cli_X"):
    return {
        "client_id": client_id,
        "business_goal": "g",
        "scenario": "s",
        "audience_profile": {"name": "aud"},
        "creative_variants": [
            {"label": "A", "headline": "h1"},
            {"label": "B", "headline": "h2"},
        ],
        "channels": ["instagram"],
        "success_metrics": ["CTR"],
    }


def test_disabled_flag_returns_404(client, monkeypatch):
    monkeypatch.setattr(ct_api.Config, "CREATIVE_TESTING_ENABLED", False)
    res = client.post("/api/report/creative-test/start", json=_valid_brief())
    assert res.status_code == 404


def test_missing_client_id_returns_400(client, stub_pipeline):
    payload = _valid_brief()
    payload.pop("client_id")
    res = client.post("/api/report/creative-test/start", json=payload)
    assert res.status_code == 400
    assert "client_id" in res.get_json()["error"]


def test_invalid_brief_returns_400(client, stub_pipeline):
    payload = _valid_brief()
    payload["creative_variants"] = [{"label": "A", "headline": ""}]
    res = client.post("/api/report/creative-test/start", json=payload)
    assert res.status_code == 400
    body = res.get_json()
    assert body["success"] is False
    assert "validation_errors" in body


def test_text_only_json_path(client, stub_pipeline):
    res = client.post("/api/report/creative-test/start", json=_valid_brief())
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["data"]["test_id"] == "ctest_TEST"
    assert body["data"]["mode"] == "mock"
    assert stub_pipeline["client_id"] == "cli_X"


def _png_bytes():
    """Minimal valid 1x1 PNG."""
    return bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000D4944415478DA63FCFFFF3F0300050001017F4D7A560000000049454E44AE426082"
    )


def test_multipart_image_slides_arrive_in_order(client, stub_pipeline, monkeypatch, tmp_path):
    """`image_<L>_0/_1/_2` must end up as slide 0/1/2 on variant L. We
    intercept _attach_variant_images so we can read the parsed request
    rather than actually writing files."""
    captured_req = {}

    def _spy(test_id, parsed_request, files_by_label):
        captured_req["files_by_label"] = {
            k: [f.filename for f in v] for k, v in files_by_label.items()
        }

    monkeypatch.setattr(ct_api, "_attach_variant_images", _spy)

    payload = _valid_brief()
    data = {
        "payload": json.dumps(payload),
        "image_A_0": (io.BytesIO(_png_bytes()), "a0.png"),
        "image_A_1": (io.BytesIO(_png_bytes()), "a1.png"),
        "image_A_2": (io.BytesIO(_png_bytes()), "a2.png"),
        # Out-of-order key for B; should still land in numeric order.
        "image_B_2": (io.BytesIO(_png_bytes()), "b2.png"),
        "image_B_0": (io.BytesIO(_png_bytes()), "b0.png"),
    }
    res = client.post(
        "/api/report/creative-test/start",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 200, res.get_json()
    files = captured_req["files_by_label"]
    assert files["A"] == ["a0.png", "a1.png", "a2.png"]
    assert files["B"] == ["b0.png", "b2.png"]


def test_multipart_unsuffixed_image_is_treated_as_slide_zero(client, stub_pipeline, monkeypatch):
    """`image_<L>` (R4 backward-compat) is prepended before any indexed
    slides — it represents slide 0."""
    captured_req = {}

    def _spy(test_id, parsed_request, files_by_label):
        captured_req["files_by_label"] = {
            k: [f.filename for f in v] for k, v in files_by_label.items()
        }

    monkeypatch.setattr(ct_api, "_attach_variant_images", _spy)

    payload = _valid_brief()
    data = {
        "payload": json.dumps(payload),
        "image_A": (io.BytesIO(_png_bytes()), "a_main.png"),
        "image_A_1": (io.BytesIO(_png_bytes()), "a_extra.png"),
    }
    res = client.post(
        "/api/report/creative-test/start",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    files = captured_req["files_by_label"]
    assert files["A"] == ["a_main.png", "a_extra.png"]


def test_invalid_payload_json_returns_400(client, stub_pipeline):
    data = {"payload": "{not valid json"}
    res = client.post(
        "/api/report/creative-test/start",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "JSON" in res.get_json()["error"]


def test_image_endpoint_404s_for_bad_extension(client):
    res = client.get("/api/report/creative-test/abc/images/evil.exe")
    assert res.status_code == 404


def test_video_endpoint_404s_for_bad_extension(client):
    res = client.get("/api/report/creative-test/abc/videos/evil.exe")
    assert res.status_code == 404


def test_image_endpoint_404s_for_missing_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(ct_api, "_images_dir", lambda tid: str(tmp_path))
    res = client.get("/api/report/creative-test/abc/images/missing.png")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_always_200_when_enabled(client):
    res = client.get("/api/report/creative-test/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    data = body["data"]
    assert data["enabled"] is True
    assert data["mode"] == "mock"
    assert data["phase"] == 1


def test_health_200_even_when_flag_off(client, monkeypatch):
    monkeypatch.setattr(ct_api.Config, "CREATIVE_TESTING_ENABLED", False)
    res = client.get("/api/report/creative-test/health")
    assert res.status_code == 200
    assert res.get_json()["data"]["enabled"] is False


# ---------------------------------------------------------------------------
# GET /list
# ---------------------------------------------------------------------------

def test_list_returns_empty_when_no_records(client, monkeypatch):
    monkeypatch.setattr(ct_api.CreativeTestStore, "list_recent", lambda limit: [])
    res = client.get("/api/report/creative-test/list")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["data"] == []
    assert body["count"] == 0


def test_list_respects_limit_param(client, monkeypatch):
    received = {}

    def _list(limit):
        received["limit"] = limit
        return []

    monkeypatch.setattr(ct_api.CreativeTestStore, "list_recent", _list)
    client.get("/api/report/creative-test/list?limit=5")
    assert received["limit"] == 5


def test_list_returns_records(client, monkeypatch):
    records = [{"test_id": "t1", "status": "completed"}, {"test_id": "t2", "status": "running"}]
    monkeypatch.setattr(ct_api.CreativeTestStore, "list_recent", lambda limit: records)
    res = client.get("/api/report/creative-test/list")
    body = res.get_json()
    assert body["count"] == 2
    assert body["data"][0]["test_id"] == "t1"


def test_list_404_when_flag_off(client, monkeypatch):
    monkeypatch.setattr(ct_api.Config, "CREATIVE_TESTING_ENABLED", False)
    res = client.get("/api/report/creative-test/list")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /<test_id>
# ---------------------------------------------------------------------------

def test_get_test_returns_record(client, monkeypatch):
    record = {"test_id": "ctest_ABC", "status": "completed", "result": {"score": 0.9}}
    monkeypatch.setattr(ct_api.CreativeTestStore, "get", lambda tid: record)
    res = client.get("/api/report/creative-test/ctest_ABC")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["data"]["test_id"] == "ctest_ABC"


def test_get_test_404_for_unknown(client, monkeypatch):
    monkeypatch.setattr(ct_api.CreativeTestStore, "get", lambda tid: None)
    res = client.get("/api/report/creative-test/nonexistent")
    assert res.status_code == 404
    assert "not found" in res.get_json()["error"]


def test_get_test_404_when_flag_off(client, monkeypatch):
    monkeypatch.setattr(ct_api.Config, "CREATIVE_TESTING_ENABLED", False)
    res = client.get("/api/report/creative-test/ctest_ABC")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /<test_id>/status
# ---------------------------------------------------------------------------

def _make_status_stubs(monkeypatch, record):
    monkeypatch.setattr(ct_api.CreativeTestStore, "get", lambda tid: record)

    class _TM:
        def list_tasks(self, task_type=None):
            return []

    monkeypatch.setattr(ct_api, "TaskManager", lambda: _TM())


def test_status_completed_record(client, monkeypatch):
    record = {
        "test_id": "ctest_C",
        "status": "completed",
        "mode": "mock",
        "result": {"score": 0.8},
        "warnings": [],
    }
    _make_status_stubs(monkeypatch, record)
    res = client.get("/api/report/creative-test/ctest_C/status")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert data["result"] is not None
    assert data["warnings"] == []


def test_status_running_no_result(client, monkeypatch):
    record = {"test_id": "ctest_R", "status": "running", "mode": "mock", "warnings": []}
    _make_status_stubs(monkeypatch, record)
    res = client.get("/api/report/creative-test/ctest_R/status")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["status"] == "running"
    assert data["result"] is None


def test_status_failed_exposes_warnings(client, monkeypatch):
    record = {
        "test_id": "ctest_F",
        "status": "failed",
        "mode": "live",
        "error": "boom",
        "warnings": ["Video extraction failed for variant 'A': frames and transcript unavailable."],
    }
    _make_status_stubs(monkeypatch, record)
    res = client.get("/api/report/creative-test/ctest_F/status")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["error"] == "boom"
    assert len(data["warnings"]) == 1
    assert "Video extraction failed" in data["warnings"][0]


def test_status_404_for_unknown_id(client, monkeypatch):
    monkeypatch.setattr(ct_api.CreativeTestStore, "get", lambda tid: None)
    res = client.get("/api/report/creative-test/nope/status")
    assert res.status_code == 404


def test_status_404_when_flag_off(client, monkeypatch):
    monkeypatch.setattr(ct_api.Config, "CREATIVE_TESTING_ENABLED", False)
    res = client.get("/api/report/creative-test/ctest_X/status")
    assert res.status_code == 404
