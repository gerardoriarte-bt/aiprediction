"""Embedding clients for the Postgres graph backend.

Phase 0: define the abstraction and ship two concrete clients (OpenAI
and Ollama). Higher-level services (ingest, retrieval) will pull the
concrete client through `get_embedding_client()` so swapping providers
is a config change.
"""

from .base import EmbeddingClient, EmbeddingError
from .factory import get_embedding_client

__all__ = ["EmbeddingClient", "EmbeddingError", "get_embedding_client"]
