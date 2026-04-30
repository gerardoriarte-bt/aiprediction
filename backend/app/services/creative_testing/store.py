"""
Persistencia simple de Creative Tests.

Guarda cada test en archivos nuevos bajo uploads/creative_tests/<id>.json.
No toca uploads/reports/ ni archivos historicos del flujo actual.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_BASE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "uploads", "creative_tests"
)
_BASE_DIR = os.path.abspath(_BASE_DIR)

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir() -> None:
    os.makedirs(_BASE_DIR, exist_ok=True)


def _path_for(test_id: str) -> str:
    safe = "".join(c for c in test_id if c.isalnum() or c in ("_", "-"))
    return os.path.join(_BASE_DIR, f"{safe}.json")


class CreativeTestStore:
    """Store basado en archivos JSON. Aislado del store de reportes."""

    @staticmethod
    def new_id() -> str:
        return f"ctest_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def save(record: Dict[str, Any]) -> Dict[str, Any]:
        _ensure_dir()
        test_id = record.get("test_id") or CreativeTestStore.new_id()
        record["test_id"] = test_id
        record.setdefault("created_at", _now_iso())
        record["updated_at"] = _now_iso()

        path = _path_for(test_id)
        with _lock:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        return record

    @staticmethod
    def get(test_id: str) -> Optional[Dict[str, Any]]:
        path = _path_for(test_id)
        if not os.path.exists(path):
            return None
        with _lock:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    @staticmethod
    def list_recent(limit: int = 50) -> List[Dict[str, Any]]:
        if not os.path.isdir(_BASE_DIR):
            return []
        files = [
            os.path.join(_BASE_DIR, name)
            for name in os.listdir(_BASE_DIR)
            if name.endswith(".json")
        ]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        out: List[Dict[str, Any]] = []
        for path in files[:limit]:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                continue
        return out

    @staticmethod
    def list_by_client(client_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Filter the on-disk records to those belonging to a single client.

        Records persisted before R1 do not have a `client_id`; they remain
        on disk for traceability but are excluded from this listing — the
        product is now strictly client-scoped (REGLAS_COMPLEMENTO §3 evolves
        into a 'corridas deben tener cliente' policy from R1 onward).
        """
        if not os.path.isdir(_BASE_DIR):
            return []
        files = [
            os.path.join(_BASE_DIR, name)
            for name in os.listdir(_BASE_DIR)
            if name.endswith(".json")
        ]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        out: List[Dict[str, Any]] = []
        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    record = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if record.get("client_id") == client_id:
                out.append(record)
                if len(out) >= limit:
                    break
        return out
