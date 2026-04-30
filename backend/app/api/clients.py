"""
Clients API (Entrega 2 — multi-cliente).

Disponible solo cuando DATABASE_URL está configurado. Cuando no, los
endpoints devuelven 503 con un mensaje claro y la UI puede esconder la
sección. /api/clients/health siempre responde 200 para discovery.
"""

from __future__ import annotations

import traceback
from typing import Any, Dict

from flask import jsonify, request

from . import clients_bp
from ..repositories.clients import ClientNotFoundError, ClientSlugTaken
from ..repositories.graph.errors import GraphNotFoundError
from ..services.clients import ClientService
from ..services.clients_graph import ClientGraphService
from ..utils.logger import get_logger


logger = get_logger("mirofish.api.clients")


def _unavailable_response():
    return (
        jsonify(
            {
                "success": False,
                "error": (
                    "Clients module requires DATABASE_URL to be configured. "
                    "Set DATABASE_URL and apply migrations 002_clients.sql."
                ),
            }
        ),
        503,
    )


@clients_bp.route("/health", methods=["GET"])
def clients_health():
    """Discovery endpoint. Always 200.

    R1 — no longer auto-creates a default workspace. Every run must belong
    to an explicit client; legacy data without a client is hidden from the
    new UI but kept on disk for traceability.
    """
    available = ClientService.is_available()
    info: Dict[str, Any] = {"available": available}
    if available:
        try:
            # Cheap connectivity probe via list (limit=1) so misconfigured
            # DATABASE_URL surfaces here, not deep in a request handler.
            ClientService.list_clients(limit=1)
        except Exception as e:
            logger.warning("clients health probe failed: %s", e)
            info["available"] = False
            info["error"] = str(e)
    return jsonify({"success": True, "data": info})


@clients_bp.route("", methods=["GET"])
def list_clients():
    """List clients. Pass `?with_stats=true` to include per-client counts.

    Stats: creative_tests (filesystem) and graph entities/edges/episodes
    (Postgres) — used by the cliente-céntrica home (R2.2).
    """
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        limit = request.args.get("limit", 200, type=int)
        with_stats = request.args.get("with_stats", "false").lower() in ("1", "true", "yes")
        records = ClientService.list_clients(limit=limit)

        if with_stats and records:
            from ..services.creative_testing import CreativeTestStore
            from ..repositories.graph import connection
            from ..repositories.graph.repos import (
                EdgeRepository,
                EpisodeRepository,
                NodeRepository,
            )

            # 1 connection, N small queries — for typical agency volumes
            # (<200 clients) this is well under 100ms total.
            try:
                with connection.get_pool().connection() as conn:
                    for r in records:
                        gid = r.get("graph_id")
                        if gid:
                            try:
                                r["episodes"] = len(
                                    EpisodeRepository.list_by_graph(conn, gid)
                                )
                                r["entities"] = NodeRepository.count_by_graph(conn, gid)
                                r["edges"] = EdgeRepository.count_by_graph(conn, gid)
                            except Exception:
                                r["episodes"] = 0
                                r["entities"] = 0
                                r["edges"] = 0
                        else:
                            r["episodes"] = 0
                            r["entities"] = 0
                            r["edges"] = 0
            except Exception as e:
                logger.warning("with_stats: postgres counts skipped: %s", e)

            for r in records:
                try:
                    r["tests"] = len(
                        CreativeTestStore.list_by_client(r["client_id"], limit=10000)
                    )
                except Exception:
                    r["tests"] = 0
                # Reports + simulations counters land when those modules
                # get client-scoped (entrega 3.6). Keep keys for stable shape.
                r.setdefault("reports", 0)
                r.setdefault("sims", 0)

        return jsonify({"success": True, "data": records, "count": len(records)})
    except Exception as e:
        logger.error("list_clients failed: %s", e)
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


@clients_bp.route("", methods=["POST"])
def create_client():
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        payload = request.get_json(silent=True) or {}
        record = ClientService.create_client(payload)
        return jsonify({"success": True, "data": record}), 201
    except ClientSlugTaken as e:
        return jsonify({"success": False, "error": str(e)}), 409
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("create_client failed: %s", e)
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


@clients_bp.route("/<client_id>", methods=["GET"])
def get_client(client_id: str):
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        record = ClientService.get_client(client_id)
        return jsonify({"success": True, "data": record})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error("get_client failed: %s", e)
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


@clients_bp.route("/<client_id>", methods=["PATCH"])
def update_client(client_id: str):
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        payload = request.get_json(silent=True) or {}
        record = ClientService.update_client(client_id, payload)
        return jsonify({"success": True, "data": record})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ClientSlugTaken as e:
        return jsonify({"success": False, "error": str(e)}), 409
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("update_client failed: %s", e)
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


@clients_bp.route("/<client_id>", methods=["DELETE"])
def delete_client(client_id: str):
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        ClientService.delete_client(client_id)
        return jsonify({"success": True})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("delete_client failed: %s", e)
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


# ---------------------------------------------------------------------------
# Entrega 3: per-client graph endpoints
# ---------------------------------------------------------------------------


@clients_bp.route("/<client_id>/graph", methods=["POST"])
def bootstrap_graph(client_id: str):
    """Create + attach the client graph (idempotent)."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        record = ClientGraphService.bootstrap_graph(client_id)
        return jsonify({"success": True, "data": record})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("bootstrap_graph failed")
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


@clients_bp.route("/<client_id>/context", methods=["POST"])
def ingest_context(client_id: str):
    """Ingest a chunk of text (brief, study, copy) into the client graph."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        payload = request.get_json(silent=True) or {}
        text = payload.get("text") or ""
        source = payload.get("source") or None
        chunk_size = int(payload.get("chunk_size") or 600)
        chunk_overlap = int(payload.get("chunk_overlap") or 80)

        result = ClientGraphService.ingest_text(
            client_id=client_id,
            text=text,
            source=source,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return jsonify({"success": True, "data": result})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("ingest_context failed")
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


@clients_bp.route("/<client_id>/context/upload", methods=["POST"])
def upload_context(client_id: str):
    """Upload PDF/MD/TXT files and ingest each as its own episode.

    Multipart form-data: field `files[]` (one or many). Each file is
    parsed with FileParser, the extracted text is ingested into the
    client graph, and we return a per-file summary so the UI can show
    which uploads failed without aborting the whole batch.
    """
    if not ClientService.is_available():
        return _unavailable_response()

    import os
    import tempfile
    from werkzeug.utils import secure_filename
    from ..utils.file_parser import FileParser

    try:
        # Verify the client exists upfront.
        ClientService.get_client(client_id)

        # Flask spreads files across both `files` and `files[]` keys
        # depending on the client; accept both.
        uploaded = request.files.getlist("files") or request.files.getlist("files[]")
        if not uploaded:
            return (
                jsonify(
                    {"success": False, "error": "No files received (field 'files')."}
                ),
                400,
            )

        results = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in uploaded:
                fname = secure_filename(f.filename or "")
                if not fname:
                    results.append(
                        {
                            "filename": f.filename,
                            "success": False,
                            "error": "Empty/unsafe filename.",
                        }
                    )
                    continue

                ext = os.path.splitext(fname)[1].lower()
                if ext not in FileParser.SUPPORTED_EXTENSIONS:
                    results.append(
                        {
                            "filename": fname,
                            "success": False,
                            "error": f"Unsupported extension: {ext or '(none)'}",
                        }
                    )
                    continue

                tmp_path = os.path.join(tmpdir, fname)
                f.save(tmp_path)

                try:
                    text = FileParser.extract_text(tmp_path)
                except Exception as e:
                    results.append(
                        {
                            "filename": fname,
                            "success": False,
                            "error": f"Could not extract text: {e}",
                        }
                    )
                    continue

                if not text or not text.strip():
                    results.append(
                        {
                            "filename": fname,
                            "success": False,
                            "error": "File parsed to empty text.",
                        }
                    )
                    continue

                try:
                    ingest = ClientGraphService.ingest_text(
                        client_id=client_id,
                        text=text,
                        source=fname,
                    )
                    results.append(
                        {
                            "filename": fname,
                            "success": True,
                            "chunk_count": ingest.get("chunk_count", 0),
                            "stats": ingest.get("stats", {}),
                            "episode_uuids": ingest.get("episode_uuids", []),
                        }
                    )
                except Exception as e:
                    logger.exception("ingest failed for %s", fname)
                    results.append(
                        {
                            "filename": fname,
                            "success": False,
                            "error": str(e),
                        }
                    )

        ok_count = sum(1 for r in results if r.get("success"))
        return jsonify(
            {
                "success": True,
                "data": {
                    "client_id": client_id,
                    "uploaded": len(results),
                    "succeeded": ok_count,
                    "failed": len(results) - ok_count,
                    "files": results,
                },
            }
        )
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("upload_context failed")
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


@clients_bp.route("/<client_id>/context", methods=["GET"])
def list_context(client_id: str):
    """List ingested episodes + totals for the client graph."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        result = ClientGraphService.list_context(client_id)
        return jsonify({"success": True, "data": result})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("list_context failed")
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


@clients_bp.route("/<client_id>/creative-tests", methods=["GET"])
def list_client_creative_tests(client_id: str):
    """List creative tests scoped to this client."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        # Verify the client exists.
        ClientService.get_client(client_id)
        from ..services.creative_testing import CreativeTestStore

        records = CreativeTestStore.list_by_client(client_id)
        # Slim each record to what the list view actually needs.
        slim = []
        for r in records:
            result = (r.get("result") or {}) if isinstance(r.get("result"), dict) else {}
            summary = result.get("summary") or {}
            slim.append(
                {
                    "test_id": r.get("test_id"),
                    "client_id": r.get("client_id"),
                    "status": r.get("status"),
                    "mode": r.get("mode"),
                    "created_at": r.get("created_at"),
                    "updated_at": r.get("updated_at"),
                    "winner_label": summary.get("winner_label"),
                    "winner_recommendation": summary.get("winner_recommendation"),
                    "audience": summary.get("audience"),
                    "business_goal": (r.get("request") or {}).get("business_goal"),
                }
            )
        return jsonify({"success": True, "data": slim, "count": len(slim)})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("list_client_creative_tests failed")
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


@clients_bp.route("/<client_id>/projects", methods=["GET"])
def list_client_projects(client_id: str):
    """List projects scoped to this client (R3.3)."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        ClientService.get_client(client_id)  # 404 if missing
        from ..models.project import ProjectManager

        projects = ProjectManager.list_by_client(client_id)
        slim = [
            {
                "project_id": p.project_id,
                "name": p.name,
                "status": p.status.value if hasattr(p.status, "value") else p.status,
                "graph_id": p.graph_id,
                "simulation_requirement": p.simulation_requirement,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in projects
        ]
        return jsonify({"success": True, "data": slim, "count": len(slim)})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("list_client_projects failed")
        return (jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500)


@clients_bp.route("/<client_id>/simulations", methods=["GET"])
def list_client_simulations(client_id: str):
    """List simulations whose project belongs to this client (R3.3)."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        ClientService.get_client(client_id)
        from ..models.project import ProjectManager
        from ..services.simulation_manager import SimulationManager

        scoped_project_ids = {p.project_id for p in ProjectManager.list_by_client(client_id)}
        if not scoped_project_ids:
            return jsonify({"success": True, "data": [], "count": 0})

        manager = SimulationManager()
        out = []
        for state in manager.list_simulations():
            if state.project_id in scoped_project_ids:
                out.append({
                    "simulation_id": state.simulation_id,
                    "project_id": state.project_id,
                    "graph_id": state.graph_id,
                    "status": state.status.value if hasattr(state.status, "value") else state.status,
                    "entities_count": getattr(state, "entities_count", 0),
                    "profiles_count": getattr(state, "profiles_count", 0),
                    "created_at": getattr(state, "created_at", ""),
                    "error": getattr(state, "error", None),
                })
        out.sort(key=lambda s: s.get("created_at") or "", reverse=True)
        return jsonify({"success": True, "data": out, "count": len(out)})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("list_client_simulations failed")
        return (jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500)


@clients_bp.route("/<client_id>/reports", methods=["GET"])
def list_client_reports(client_id: str):
    """List reports tied to simulations of projects of this client (R3.3)."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        ClientService.get_client(client_id)
        from ..models.project import ProjectManager
        from ..services.simulation_manager import SimulationManager
        from ..services.report_agent import ReportManager

        scoped_project_ids = {p.project_id for p in ProjectManager.list_by_client(client_id)}
        if not scoped_project_ids:
            return jsonify({"success": True, "data": [], "count": 0})

        manager = SimulationManager()
        sim_ids = [
            state.simulation_id
            for state in manager.list_simulations()
            if state.project_id in scoped_project_ids
        ]
        out = []
        for sim_id in sim_ids:
            try:
                report = ReportManager.get_report_by_simulation(sim_id)
                if report:
                    rd = report.to_dict() if hasattr(report, "to_dict") else {}
                    out.append({
                        "report_id": rd.get("report_id"),
                        "simulation_id": rd.get("simulation_id"),
                        "status": rd.get("status"),
                        "created_at": rd.get("created_at"),
                        "completed_at": rd.get("completed_at"),
                        "title": rd.get("outline", {}).get("title") if isinstance(rd.get("outline"), dict) else None,
                    })
            except Exception:
                continue
        out.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return jsonify({"success": True, "data": out, "count": len(out)})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("list_client_reports failed")
        return (jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500)


@clients_bp.route("/<client_id>/predict", methods=["POST"])
def predict_for_client(client_id: str):
    """Answer an open question grounded on the client knowledge graph (R3.2)."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        payload = request.get_json(silent=True) or {}
        question = (payload.get("question") or payload.get("query") or "").strip()
        result = ClientGraphService.predict(client_id=client_id, question=question)
        return jsonify({"success": True, "data": result})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("predict_for_client failed")
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


@clients_bp.route("/<client_id>/graph/data", methods=["GET"])
def graph_data(client_id: str):
    """Return the client graph as {nodes, edges} ready for the D3 canvas."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        result = ClientGraphService.graph_data(client_id)
        return jsonify({"success": True, "data": result})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.exception("graph_data failed")
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


@clients_bp.route("/<client_id>/search", methods=["POST"])
def search_client(client_id: str):
    """Top-k semantic search over the client graph."""
    if not ClientService.is_available():
        return _unavailable_response()
    try:
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        limit = int(payload.get("limit") or 10)

        result = ClientGraphService.search(
            client_id=client_id, query=query, limit=limit
        )
        return jsonify({"success": True, "data": result})
    except ClientNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except GraphNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 409
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("search_client failed")
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
