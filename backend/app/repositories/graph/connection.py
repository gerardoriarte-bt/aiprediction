"""
Lazy psycopg connection helpers for the Postgres graph backend.

Only imports psycopg when actually called, so installs that don't include
the optional [postgres] extra still fail gracefully.
"""

from __future__ import annotations

import threading
from typing import Optional

from ...config import Config
from ...utils.logger import get_logger


_logger = get_logger("mirofish.graph.postgres.connection")
_pool_lock = threading.Lock()
_pool = None  # type: ignore[assignment]


def _require_psycopg():
    try:
        import psycopg  # noqa: F401
        from psycopg_pool import ConnectionPool
        return ConnectionPool
    except ImportError as e:
        raise RuntimeError(
            "psycopg is not installed. Add the [postgres] extra to your "
            "backend env (pip install 'psycopg[binary]' psycopg-pool pgvector)."
        ) from e


def get_pool():
    """Return a process-wide ConnectionPool, initialising it on first use."""
    global _pool
    if _pool is not None:
        return _pool

    if not Config.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Required for the Postgres graph backend."
        )

    ConnectionPool = _require_psycopg()
    with _pool_lock:
        if _pool is None:
            _logger.info("Initialising Postgres connection pool")
            _pool = ConnectionPool(
                conninfo=Config.DATABASE_URL,
                min_size=1,
                max_size=8,
                kwargs={"autocommit": False},
            )
    return _pool


def close_pool() -> None:
    """Close the pool. Safe to call when no pool was created."""
    global _pool
    if _pool is None:
        return
    with _pool_lock:
        if _pool is not None:
            _logger.info("Closing Postgres connection pool")
            try:
                _pool.close()
            except Exception:
                _logger.exception("Error closing Postgres pool")
            _pool = None


def healthcheck() -> bool:
    """Return True iff a SELECT 1 round-trip succeeds. Never raises."""
    try:
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception:
        _logger.exception("Postgres healthcheck failed")
        return False
