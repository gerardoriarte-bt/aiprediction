"""ClientService — application logic for the multi-cliente entity.

Owns slug generation/validation, default-workspace bootstrap, and any
orchestration that touches more than the `clients` table. The HTTP layer
in api/clients.py only translates JSON <-> service calls.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..repositories.clients import (
    ClientNotFoundError,
    ClientRepository,
    ClientSlugTaken,
)
from ..repositories.graph import connection
from ..utils.logger import get_logger


logger = get_logger("mirofish.clients.service")


_DEFAULT_SLUG = "default"
_DEFAULT_NAME = "Default workspace"
_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _new_client_id() -> str:
    return f"cli_{uuid.uuid4().hex[:12]}"


def _slugify(value: str) -> str:
    if not value:
        return ""
    s = value.strip().lower()
    s = s.replace(" ", "-")
    s = _SLUG_RE.sub("", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:64]


def _serialise_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce psycopg-native types (datetime, etc.) to JSON-friendly."""
    if record is None:
        return None  # type: ignore[return-value]
    out: Dict[str, Any] = {}
    for k, v in record.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


class ClientService:
    """Stateless façade over ClientRepository."""

    @staticmethod
    def is_available() -> bool:
        return bool(Config.DATABASE_URL)

    # ---- Bootstrap ------------------------------------------------------

    @staticmethod
    def ensure_default_workspace() -> Dict[str, Any]:
        """Create the 'Default workspace' client if it does not exist.

        Lets the agency keep using legacy projects while gradually moving
        them under explicit clients.
        """
        with connection.get_pool().connection() as conn:
            existing = ClientRepository.get_by_slug(conn, _DEFAULT_SLUG)
            if existing is not None:
                return _serialise_record(existing)
            record = ClientRepository.insert(
                conn,
                client_id=_new_client_id(),
                name=_DEFAULT_NAME,
                slug=_DEFAULT_SLUG,
                description="Workspace for legacy projects without an explicit client.",
                metadata={},
                is_default=True,
            )
            conn.commit()
        logger.info("Default workspace bootstrap: %s", record["client_id"])
        return _serialise_record(record)

    # ---- CRUD -----------------------------------------------------------

    @staticmethod
    def list_clients(limit: int = 200) -> List[Dict[str, Any]]:
        with connection.get_pool().connection() as conn:
            rows = ClientRepository.list_all(conn, limit=limit)
        return [_serialise_record(r) for r in rows]

    @staticmethod
    def get_client(client_id: str) -> Dict[str, Any]:
        with connection.get_pool().connection() as conn:
            record = ClientRepository.get(conn, client_id)
        if not record:
            raise ClientNotFoundError(client_id)
        return _serialise_record(record)

    @staticmethod
    def create_client(payload: Dict[str, Any]) -> Dict[str, Any]:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")

        slug = _slugify(payload.get("slug") or name)
        if not slug:
            raise ValueError("slug could not be derived from name")

        with connection.get_pool().connection() as conn:
            if ClientRepository.slug_exists(conn, slug):
                # Disambiguate with a short hash; keeps slugs human-readable.
                slug = f"{slug}-{uuid.uuid4().hex[:4]}"
                if ClientRepository.slug_exists(conn, slug):
                    raise ClientSlugTaken(slug)

            record = ClientRepository.insert(
                conn,
                client_id=_new_client_id(),
                name=name,
                slug=slug,
                industry=(payload.get("industry") or None),
                description=(payload.get("description") or None),
                brand_guidelines=(payload.get("brand_guidelines") or None),
                metadata=(payload.get("metadata") or {}),
                graph_id=(payload.get("graph_id") or None),
                is_default=False,
            )
            conn.commit()
        logger.info("Created client %s (slug=%s)", record["client_id"], record["slug"])
        return _serialise_record(record)

    @staticmethod
    def update_client(client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with connection.get_pool().connection() as conn:
            existing = ClientRepository.get(conn, client_id)
            if not existing:
                raise ClientNotFoundError(client_id)

            slug = payload.get("slug")
            if slug is not None:
                slug = _slugify(slug)
                if ClientRepository.slug_exists(conn, slug, exclude_client_id=client_id):
                    raise ClientSlugTaken(slug)

            record = ClientRepository.update(
                conn,
                client_id=client_id,
                name=payload.get("name"),
                slug=slug,
                industry=payload.get("industry"),
                description=payload.get("description"),
                brand_guidelines=payload.get("brand_guidelines"),
                metadata=payload.get("metadata"),
                graph_id=payload.get("graph_id"),
            )
            conn.commit()
        if not record:
            raise ClientNotFoundError(client_id)
        return _serialise_record(record)

    @staticmethod
    def delete_client(client_id: str) -> None:
        with connection.get_pool().connection() as conn:
            existing = ClientRepository.get(conn, client_id)
            if not existing:
                raise ClientNotFoundError(client_id)
            if existing.get("is_default"):
                raise ValueError("the default workspace cannot be deleted")
            ClientRepository.delete(conn, client_id)
            conn.commit()
        logger.info("Deleted client %s", client_id)
