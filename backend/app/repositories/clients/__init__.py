"""Client repository (Entrega 2 — multi-cliente).

Always Postgres-backed: clients are the structural unit of the product
once the agency manages multiple accounts. The legacy graph stack
remains backend-agnostic (Zep | Postgres) but the clients table itself
lives in Postgres.
"""

from .repo import ClientRepository
from .errors import ClientNotFoundError, ClientSlugTaken

__all__ = ["ClientRepository", "ClientNotFoundError", "ClientSlugTaken"]
