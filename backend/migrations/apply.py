"""
Apply versioned SQL migrations against DATABASE_URL.

Phase 0 helper. Substitutes the :embedding_dim placeholder with
Config.EMBEDDING_DIM so the same SQL file can be reused across
embedding providers without editing it.

Usage:
    cd backend
    .venv/bin/python -m migrations.apply
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List

# Allow running as a module: `python -m migrations.apply`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config  # noqa: E402


_MIGRATIONS_DIR = Path(__file__).resolve().parent
_VERSION_RE = re.compile(r"^(\d+)_.*\.sql$")


def _list_migrations() -> List[Path]:
    files = sorted(p for p in _MIGRATIONS_DIR.glob("*.sql") if _VERSION_RE.match(p.name))
    return files


def _version_of(path: Path) -> str:
    m = _VERSION_RE.match(path.name)
    if not m:
        raise ValueError(f"Unexpected migration filename: {path.name}")
    return m.group(1)


def _render(sql: str, embedding_dim: int) -> str:
    # Replace ':embedding_dim' (used inside vector(:embedding_dim)).
    # We do not use psycopg parameter binding here because vector type
    # parameters cannot be bound — they must be present at parse time.
    return sql.replace(":embedding_dim", str(embedding_dim))


def main() -> int:
    if Config.GRAPH_BACKEND != "postgres":
        print(
            f"[apply.py] GRAPH_BACKEND={Config.GRAPH_BACKEND!r}. "
            "Migrations are only meaningful when GRAPH_BACKEND=postgres. "
            "Set the env var and retry."
        )
        return 1
    if not Config.DATABASE_URL:
        print("[apply.py] DATABASE_URL is not set. Cannot apply migrations.")
        return 1
    try:
        import psycopg  # type: ignore
    except ImportError:
        print(
            "[apply.py] psycopg is not installed. Add 'psycopg[binary]' to your "
            "environment (see backend/pyproject.toml [postgres] extra)."
        )
        return 1

    migrations = _list_migrations()
    if not migrations:
        print("[apply.py] No migrations found.")
        return 0

    print(
        f"[apply.py] Connecting to Postgres (embedding_dim={Config.EMBEDDING_DIM})..."
    )
    with psycopg.connect(Config.DATABASE_URL, autocommit=False) as conn:
        with conn.cursor() as cur:
            # Bootstrap the ledger separately so we can read it.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version       TEXT PRIMARY KEY,
                    applied_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    embedding_dim INTEGER NOT NULL
                );
                """
            )
            conn.commit()

            cur.execute("SELECT version FROM schema_migrations;")
            applied = {row[0] for row in cur.fetchall()}

            for path in migrations:
                version = _version_of(path)
                if version in applied:
                    print(f"[apply.py] {path.name}: already applied — skipping.")
                    continue

                sql = _render(path.read_text(encoding="utf-8"), Config.EMBEDDING_DIM)
                print(f"[apply.py] {path.name}: applying...")
                try:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (version, embedding_dim) VALUES (%s, %s);",
                        (version, Config.EMBEDDING_DIM),
                    )
                    conn.commit()
                    print(f"[apply.py] {path.name}: OK")
                except Exception as e:
                    conn.rollback()
                    print(f"[apply.py] {path.name}: FAILED — {e}")
                    return 2

    print("[apply.py] All migrations applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
