"""SQL repository for the `clients` table."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _row(cursor, row) -> Dict[str, Any]:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


class ClientRepository:
    @staticmethod
    def insert(
        conn,
        client_id: str,
        name: str,
        slug: str,
        industry: Optional[str] = None,
        description: Optional[str] = None,
        brand_guidelines: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        graph_id: Optional[str] = None,
        is_default: bool = False,
    ) -> Dict[str, Any]:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clients
                    (client_id, name, slug, industry, description,
                     brand_guidelines, metadata, graph_id, is_default)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                RETURNING client_id, name, slug, industry, description,
                          brand_guidelines, metadata, graph_id, is_default,
                          created_at, updated_at;
                """,
                (
                    client_id,
                    name,
                    slug,
                    industry,
                    description,
                    brand_guidelines,
                    json.dumps(metadata or {}),
                    graph_id,
                    is_default,
                ),
            )
            return _row(cur, cur.fetchone())

    @staticmethod
    def get(conn, client_id: str) -> Optional[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT client_id, name, slug, industry, description,
                       brand_guidelines, metadata, graph_id, is_default,
                       created_at, updated_at
                FROM clients WHERE client_id = %s;
                """,
                (client_id,),
            )
            row = cur.fetchone()
            return _row(cur, row) if row else None

    @staticmethod
    def get_by_slug(conn, slug: str) -> Optional[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT client_id, name, slug, industry, description,
                       brand_guidelines, metadata, graph_id, is_default,
                       created_at, updated_at
                FROM clients WHERE slug = %s;
                """,
                (slug,),
            )
            row = cur.fetchone()
            return _row(cur, row) if row else None

    @staticmethod
    def slug_exists(conn, slug: str, exclude_client_id: Optional[str] = None) -> bool:
        with conn.cursor() as cur:
            if exclude_client_id is None:
                cur.execute("SELECT 1 FROM clients WHERE slug = %s LIMIT 1;", (slug,))
            else:
                cur.execute(
                    "SELECT 1 FROM clients WHERE slug = %s AND client_id <> %s LIMIT 1;",
                    (slug, exclude_client_id),
                )
            return cur.fetchone() is not None

    @staticmethod
    def list_all(conn, limit: int = 200) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT client_id, name, slug, industry, description,
                       brand_guidelines, metadata, graph_id, is_default,
                       created_at, updated_at
                FROM clients
                ORDER BY is_default DESC, name ASC
                LIMIT %s;
                """,
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def update(
        conn,
        client_id: str,
        *,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        industry: Optional[str] = None,
        description: Optional[str] = None,
        brand_guidelines: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        graph_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        # Build dynamic SET only for the fields actually provided.
        sets: List[str] = []
        params: List[Any] = []
        if name is not None:
            sets.append("name = %s")
            params.append(name)
        if slug is not None:
            sets.append("slug = %s")
            params.append(slug)
        if industry is not None:
            sets.append("industry = %s")
            params.append(industry)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
        if brand_guidelines is not None:
            sets.append("brand_guidelines = %s")
            params.append(brand_guidelines)
        if metadata is not None:
            sets.append("metadata = %s::jsonb")
            params.append(json.dumps(metadata))
        if graph_id is not None:
            sets.append("graph_id = %s")
            params.append(graph_id)

        if not sets:
            return ClientRepository.get(conn, client_id)

        sets.append("updated_at = NOW()")
        params.append(client_id)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE clients SET {', '.join(sets)} WHERE client_id = %s "
                "RETURNING client_id, name, slug, industry, description, "
                "brand_guidelines, metadata, graph_id, is_default, "
                "created_at, updated_at;",
                params,
            )
            row = cur.fetchone()
            return _row(cur, row) if row else None

    @staticmethod
    def delete(conn, client_id: str) -> int:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE client_id = %s;", (client_id,))
            return cur.rowcount
