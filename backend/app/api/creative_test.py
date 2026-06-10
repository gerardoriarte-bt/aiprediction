"""
Creative Testing API (additive, opt-in).

Vive bajo el blueprint `report_bp` con prefijo de URL `/api/report/creative-test`.
No modifica las rutas existentes en report.py. Si `CREATIVE_TESTING_ENABLED`
es False, todas las rutas responden 404 — el flujo de reporte actual queda
totalmente sin cambios para usuarios actuales (REGLAS_COMPLEMENTO §3 y §10).
"""

import base64
import json as _json
import mimetypes
import os
import threading
import traceback
from typing import Any, Dict, List
from flask import jsonify, request, send_from_directory

from . import report_bp
from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..utils.limiter import limiter
from ..services.creative_testing import (
    CreativeTestStore,
    generate_mock_result,
    parse_request,
    run_creative_test,
    validate_request,
)
from ..utils.logger import get_logger


_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB / variant; vision tokens make bigger pointless
_ALLOWED_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}
_MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB hard cap to keep Whisper bills bounded


logger = get_logger("mirofish.api.creative_test")


_TASK_TYPE = "creative_test_run"


def _flag_off_response():
    return (
        jsonify(
            {
                "success": False,
                "error": "Creative testing is disabled (set CREATIVE_TESTING_ENABLED=true to opt-in).",
            }
        ),
        404,
    )


def _images_dir(test_id: str) -> str:
    """Per-test directory for variant images (R4)."""
    safe = "".join(c for c in test_id if c.isalnum() or c in ("_", "-"))
    base = os.path.join(
        os.path.dirname(__file__), "..", "..", "uploads", "creative_tests", safe, "images"
    )
    return os.path.abspath(base)


def _videos_dir(test_id: str) -> str:
    """Per-test directory for original video uploads (R6)."""
    safe = "".join(c for c in test_id if c.isalnum() or c in ("_", "-"))
    base = os.path.join(
        os.path.dirname(__file__), "..", "..", "uploads", "creative_tests", safe, "videos"
    )
    return os.path.abspath(base)


def _persist_video_and_extract(test_id: str, label: str, file_storage):
    """Save the video, extract frames + transcript, return (video_url,
    list_of_(slide_url, slide_data_url), transcript)."""
    raw = file_storage.read()
    if len(raw) > _MAX_VIDEO_BYTES:
        raise ValueError(f"Video for variant {label} exceeds {_MAX_VIDEO_BYTES} bytes.")
    ext = os.path.splitext(file_storage.filename or "")[1].lower() or ".mp4"
    if ext not in _ALLOWED_VIDEO_EXTS:
        raise ValueError(
            f"Unsupported video type for variant {label}: {ext} (allowed: "
            f"{sorted(_ALLOWED_VIDEO_EXTS)})."
        )
    safe_label = "".join(c for c in label if c.isalnum() or c in ("_", "-")) or "X"
    out_dir = _videos_dir(test_id)
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{safe_label}{ext}"
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "wb") as fh:
        fh.write(raw)
    video_url = f"/api/report/creative-test/{test_id}/videos/{filename}"

    # Extract frames + transcript next to the image folder so the existing
    # /images/<file> endpoint can serve them without a second router.
    frames_dir = _images_dir(test_id)
    os.makedirs(frames_dir, exist_ok=True)
    work_dir = os.path.join(frames_dir, f"_video_{safe_label}")
    os.makedirs(work_dir, exist_ok=True)

    try:
        from ..services.creative_testing.video_extractor import extract
        extraction = extract(out_path, work_dir)
    except Exception as e:
        logger.warning(f"video extraction failed for {label}: {e}")
        return video_url, [], None

    # Move extracted frames into the per-test images dir with predictable
    # filenames so the slide endpoint serves them.
    slides_payload: List[tuple[str, str]] = []
    for idx, src in enumerate(extraction.frame_paths):
        dst_name = f"{safe_label}_frame_{idx:02d}.jpg"
        dst_path = os.path.join(frames_dir, dst_name)
        try:
            os.replace(src, dst_path)
        except OSError:
            continue
        with open(dst_path, "rb") as fh:
            blob = fh.read()
        data_url = (
            f"data:image/jpeg;base64,{base64.b64encode(blob).decode('ascii')}"
        )
        slide_url = f"/api/report/creative-test/{test_id}/images/{dst_name}"
        slides_payload.append((slide_url, data_url))

    # Best-effort cleanup of the extraction work dir.
    try:
        for name in os.listdir(work_dir):
            os.remove(os.path.join(work_dir, name))
        os.rmdir(work_dir)
    except OSError:
        pass

    return video_url, slides_payload, extraction.audio_transcript


def _persist_slide(test_id: str, label: str, slide_idx: int, file_storage) -> tuple[str, str]:
    """Save one slide's upload to disk, return (relative URL, base64 data URL).

    Slide 0 is the single-image case (R4); slide_idx >= 1 only happens for
    carousels (R5).
    """
    raw = file_storage.read()
    if len(raw) > _MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image for variant {label} slide {slide_idx} exceeds "
            f"{_MAX_IMAGE_BYTES} bytes."
        )
    ext = os.path.splitext(file_storage.filename or "")[1].lower() or ".png"
    if ext not in _ALLOWED_IMAGE_EXTS:
        raise ValueError(
            f"Unsupported image type for variant {label} slide {slide_idx}: "
            f"{ext} (allowed: {sorted(_ALLOWED_IMAGE_EXTS)})."
        )
    safe_label = "".join(c for c in label if c.isalnum() or c in ("_", "-")) or "X"
    filename = f"{safe_label}_{slide_idx}{ext}"
    out_dir = _images_dir(test_id)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "wb") as fh:
        fh.write(raw)

    mime = mimetypes.guess_type(out_path)[0] or "image/png"
    data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    rel_url = f"/api/report/creative-test/{test_id}/images/{filename}"
    return rel_url, data_url


def _attach_variant_images(test_id: str, parsed_request, files_by_label):
    """Attach uploaded slides to the request (in-memory only).

    `files_by_label` maps variant label -> ordered list of FileStorage. The
    first entry becomes slide 0 (image_data_url + image_url); the rest become
    `slides[]` with both data_url (memory) and url (persisted, for the UI).
    """
    for variant in parsed_request.creative_variants:
        files = [f for f in (files_by_label.get(variant.label) or []) if f and getattr(f, "filename", None)]
        if not files:
            continue

        first = files[0]
        rel_url, data_url = _persist_slide(test_id, variant.label, 0, first)
        variant.image_data_url = data_url
        variant.image_url = rel_url

        for idx, f in enumerate(files[1:], start=1):
            slide_url, slide_data = _persist_slide(test_id, variant.label, idx, f)
            variant.slides.append({"url": slide_url, "data_url": slide_data})


@report_bp.route("/creative-test/generate", methods=["POST"])
@limiter.limit("10 per minute")
def creative_test_generate():
    """Inicia una corrida de creative testing.

    En modo `mock` (default cuando el flag esta encendido) devuelve un
    resultado deterministico sintetico, sin llamar al LLM ni al grafo,
    para validar el contrato end-to-end con el frontend.
    """
    if not Config.CREATIVE_TESTING_ENABLED:
        return _flag_off_response()

    try:
        payload = request.get_json(silent=True) or {}
        req = parse_request(payload)
        errors = validate_request(req)
        if errors:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid creative test brief.",
                        "validation_errors": errors,
                    }
                ),
                400,
            )

        mode = Config.CREATIVE_TESTING_MODE
        if mode != "mock":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            "Live mode is not available yet. Set "
                            "CREATIVE_TESTING_MODE=mock until Phase 2 ships."
                        ),
                    }
                ),
                501,
            )

        result = generate_mock_result(req)

        record = {
            "test_id": CreativeTestStore.new_id(),
            "mode": mode,
            "status": "completed",
            "request": req.to_dict(),
            "result": result,
        }
        record = CreativeTestStore.save(record)

        return jsonify({"success": True, "data": record})

    except Exception as e:
        logger.error(f"creative-test generate failed: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@report_bp.route("/creative-test/<test_id>", methods=["GET"])
def creative_test_get(test_id: str):
    if not Config.CREATIVE_TESTING_ENABLED:
        return _flag_off_response()

    try:
        record = CreativeTestStore.get(test_id)
        if not record:
            return (
                jsonify(
                    {"success": False, "error": f"Creative test not found: {test_id}"}
                ),
                404,
            )
        return jsonify({"success": True, "data": record})

    except Exception as e:
        logger.error(f"creative-test get failed: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@report_bp.route("/creative-test/list", methods=["GET"])
def creative_test_list():
    if not Config.CREATIVE_TESTING_ENABLED:
        return _flag_off_response()

    try:
        limit = request.args.get("limit", 50, type=int)
        records = CreativeTestStore.list_recent(limit=limit)
        return jsonify({"success": True, "data": records, "count": len(records)})

    except Exception as e:
        logger.error(f"creative-test list failed: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@report_bp.route("/creative-test/health", methods=["GET"])
def creative_test_health():
    """Endpoint de auto-descubrimiento. Siempre 200, indica si la feature
    esta activada para que el frontend la oculte sin romper si esta apagada."""
    return jsonify(
        {
            "success": True,
            "data": {
                "enabled": Config.CREATIVE_TESTING_ENABLED,
                "mode": Config.CREATIVE_TESTING_MODE,
                "phase": 1,
                "stage": "phase-1-async",
            },
        }
    )


# ---------------------------------------------------------------------------
# Async flow (Stage B): /start lanza tarea en thread, /<id>/status hace polling
# ---------------------------------------------------------------------------


@report_bp.route("/creative-test/start", methods=["POST"])
@limiter.limit("5 per minute")
def creative_test_start():
    """Lanza una corrida async y devuelve test_id + task_id de inmediato.

    El frontend hace polling a /<test_id>/status para mostrar el avance del
    UX Paso 2 ("Test en progreso"). Cuando status=completed, recupera el
    resultado por /<test_id>.

    R1 — client_id es obligatorio: toda corrida debe pertenecer a un cliente.
    """
    if not Config.CREATIVE_TESTING_ENABLED:
        return _flag_off_response()

    try:
        # Two intake shapes are supported:
        #  - application/json: legacy text-only brief.
        #  - multipart/form-data: text-only brief lives in the `payload` field
        #    (JSON string), and one file per variant comes as `image_<label>`.
        if request.content_type and request.content_type.startswith("multipart/"):
            raw = request.form.get("payload") or "{}"
            try:
                payload = _json.loads(raw)
            except _json.JSONDecodeError:
                return (
                    jsonify({"success": False, "error": "Invalid JSON in `payload` field."}),
                    400,
                )
        else:
            payload = request.get_json(silent=True) or {}

        client_id = (payload.get("client_id") or "").strip()
        if not client_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "client_id is required (every run must belong to a client).",
                    }
                ),
                400,
            )

        # Verify the client exists; surface 404 instead of orphan records.
        try:
            from ..repositories.clients import ClientNotFoundError
            from ..services.clients import ClientService

            ClientService.get_client(client_id)
        except ClientNotFoundError:
            return (
                jsonify({"success": False, "error": f"Client not found: {client_id}"}),
                404,
            )
        except Exception as e:
            logger.warning(f"client lookup failed: {e}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            "Clients module is not available. "
                            "Ensure DATABASE_URL is configured."
                        ),
                    }
                ),
                503,
            )

        req = parse_request(payload)
        errors = validate_request(req)
        if errors:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid creative test brief.",
                        "validation_errors": errors,
                    }
                ),
                400,
            )

        mode = Config.CREATIVE_TESTING_MODE if Config.CREATIVE_TESTING_MODE in ("mock", "live") else "mock"

        test_id = CreativeTestStore.new_id()

        # R4/R5 — multipart variant images. Two key shapes are accepted per
        # variant label L:
        #   - image_<L>             : single slide (R4 backward compat).
        #   - image_<L>_0..N        : ordered carousel slides (R5).
        # Both can be combined; ordering is by numeric suffix, with the
        # unsuffixed key prepended when present.
        if request.content_type and request.content_type.startswith("multipart/"):
            files_by_label: Dict[str, List[Any]] = {}
            for v in req.creative_variants:
                ordered: List[Any] = []
                base = request.files.get(f"image_{v.label}")
                if base and getattr(base, "filename", None):
                    ordered.append(base)

                indexed: List[tuple[int, Any]] = []
                prefix = f"image_{v.label}_"
                for key in request.files.keys():
                    if not key.startswith(prefix):
                        continue
                    suffix = key[len(prefix):]
                    if not suffix.isdigit():
                        continue
                    f = request.files.get(key)
                    if f and getattr(f, "filename", None):
                        indexed.append((int(suffix), f))
                indexed.sort(key=lambda t: t[0])
                ordered.extend(f for _, f in indexed)

                if ordered:
                    files_by_label[v.label] = ordered

            if files_by_label:
                try:
                    _attach_variant_images(test_id, req, files_by_label)
                except ValueError as e:
                    return (
                        jsonify({"success": False, "error": str(e)}),
                        400,
                    )

            # R6 — one optional `video_<label>` per variant. When present,
            # we extract frames + transcript and feed them through the same
            # carousel slot the LLM already understands.
            for v in req.creative_variants:
                vid = request.files.get(f"video_{v.label}")
                if not vid or not getattr(vid, "filename", None):
                    continue
                try:
                    video_url, slide_pairs, transcript = _persist_video_and_extract(
                        test_id, v.label, vid
                    )
                except ValueError as e:
                    return jsonify({"success": False, "error": str(e)}), 400
                v.video_url = video_url
                if transcript:
                    v.audio_transcript = transcript
                # Frames load into slide 0 + slides[]; if the variant already
                # had image uploads, the video frames append after them.
                first_idx = 0
                if not v.image_url and slide_pairs:
                    slide_url, data_url = slide_pairs[0]
                    v.image_url = slide_url
                    v.image_data_url = data_url
                    first_idx = 1
                for slide_url, data_url in slide_pairs[first_idx:]:
                    v.slides.append({"url": slide_url, "data_url": data_url})

        # Strip the heavy base64 data URL from the persisted brief — it lives
        # in memory only for the LLM call. Keep image_url so the UI can render.
        persisted_request = req.to_dict()
        for v in persisted_request.get("creative_variants") or []:
            v.pop("image_data_url", None)

        CreativeTestStore.save(
            {
                "test_id": test_id,
                "client_id": client_id,
                "mode": mode,
                "status": "running",
                "request": persisted_request,
                "result": None,
            }
        )

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type=_TASK_TYPE,
            metadata={"test_id": test_id, "mode": mode, "client_id": client_id},
        )

        def _worker():
            task_manager.update_task(
                task_id, status=TaskStatus.PROCESSING, progress=0, message="starting"
            )

            def progress_cb(stage: str, pct: int, message: str):
                task_manager.update_task(
                    task_id,
                    progress=int(pct),
                    message=f"[{stage}] {message}",
                    progress_detail={"stage": stage},
                )

            try:
                result = run_creative_test(
                    mode=mode,
                    request=req,
                    progress_cb=progress_cb,
                    client_id=client_id,
                )
                completed_request = req.to_dict()
                for v in completed_request.get("creative_variants") or []:
                    v.pop("image_data_url", None)
                CreativeTestStore.save(
                    {
                        "test_id": test_id,
                        "client_id": client_id,
                        "mode": mode,
                        "status": "completed",
                        "request": completed_request,
                        "result": result,
                    }
                )
                task_manager.complete_task(
                    task_id,
                    result={"test_id": test_id, "status": "completed"},
                )
            except Exception as e:
                logger.exception("creative-test worker failed")
                failed_request = req.to_dict()
                for v in failed_request.get("creative_variants") or []:
                    v.pop("image_data_url", None)
                CreativeTestStore.save(
                    {
                        "test_id": test_id,
                        "client_id": client_id,
                        "mode": mode,
                        "status": "failed",
                        "request": failed_request,
                        "result": None,
                        "error": str(e),
                    }
                )
                task_manager.fail_task(task_id, str(e))

        threading.Thread(target=_worker, daemon=True).start()

        return jsonify(
            {
                "success": True,
                "data": {
                    "test_id": test_id,
                    "task_id": task_id,
                    "mode": mode,
                    "status": "running",
                },
            }
        )

    except Exception as e:
        logger.error(f"creative-test start failed: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@report_bp.route("/creative-test/<test_id>/status", methods=["GET"])
def creative_test_status(test_id: str):
    """Devuelve el estado actual de una corrida (polling).

    Combina el record persistido (test_id, status, mode) con el TaskManager
    en memoria (progress, stage, message) cuando esta disponible.
    """
    if not Config.CREATIVE_TESTING_ENABLED:
        return _flag_off_response()

    try:
        record = CreativeTestStore.get(test_id)
        if not record:
            return (
                jsonify(
                    {"success": False, "error": f"Creative test not found: {test_id}"}
                ),
                404,
            )

        # Buscar task asociada en TaskManager (in-memory; puede no existir
        # si el server reinicio en medio del run).
        task_manager = TaskManager()
        task = None
        for t in task_manager.list_tasks(task_type=_TASK_TYPE):
            if t.get("metadata", {}).get("test_id") == test_id:
                task = t
                break

        progress = 100 if record.get("status") == "completed" else 0
        stage = "completed" if record.get("status") == "completed" else "pending"
        message = ""
        if task:
            progress = task.get("progress", progress)
            stage = (task.get("progress_detail") or {}).get("stage") or stage
            message = task.get("message", "")

        return jsonify(
            {
                "success": True,
                "data": {
                    "test_id": test_id,
                    "status": record.get("status"),
                    "mode": record.get("mode"),
                    "progress": progress,
                    "stage": stage,
                    "message": message,
                    "error": record.get("error"),
                    # Solo devolvemos el resultado completo cuando termino,
                    # para que el polling sea liviano.
                    "result": record.get("result") if record.get("status") == "completed" else None,
                },
            }
        )

    except Exception as e:
        logger.error(f"creative-test status failed: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )


@report_bp.route("/creative-test/<test_id>/images/<filename>", methods=["GET"])
def creative_test_image(test_id: str, filename: str):
    """Serve a per-variant image saved at start time (R4).

    The path is sanitised: only [A-Za-z0-9_-] in test_id/filename and only
    extensions in the allow-list are returned. Anything else 404s without
    leaking whether the file exists.
    """
    if not Config.CREATIVE_TESTING_ENABLED:
        return _flag_off_response()

    safe_test = "".join(c for c in test_id if c.isalnum() or c in ("_", "-"))
    safe_name = os.path.basename(filename)
    ext = os.path.splitext(safe_name)[1].lower()
    if not safe_test or ext not in _ALLOWED_IMAGE_EXTS:
        return jsonify({"success": False, "error": "not found"}), 404

    directory = _images_dir(safe_test)
    target = os.path.join(directory, safe_name)
    if not os.path.isfile(target):
        return jsonify({"success": False, "error": "not found"}), 404

    return send_from_directory(directory, safe_name)


@report_bp.route("/creative-test/<test_id>/videos/<filename>", methods=["GET"])
def creative_test_video(test_id: str, filename: str):
    """Serve the original video upload for a variant (R6).

    Same path-sanitisation contract as the image endpoint.
    """
    if not Config.CREATIVE_TESTING_ENABLED:
        return _flag_off_response()

    safe_test = "".join(c for c in test_id if c.isalnum() or c in ("_", "-"))
    safe_name = os.path.basename(filename)
    ext = os.path.splitext(safe_name)[1].lower()
    if not safe_test or ext not in _ALLOWED_VIDEO_EXTS:
        return jsonify({"success": False, "error": "not found"}), 404

    directory = _videos_dir(safe_test)
    target = os.path.join(directory, safe_name)
    if not os.path.isfile(target):
        return jsonify({"success": False, "error": "not found"}), 404

    return send_from_directory(directory, safe_name)
