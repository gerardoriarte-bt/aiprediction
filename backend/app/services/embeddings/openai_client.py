"""
OpenAI-compatible embedding client.

Reuses Config.LLM_API_KEY and Config.LLM_BASE_URL by default so a single
key powers both chat completions and embeddings. Independent overrides
are accepted for setups where embeddings come from a different provider
(e.g. Azure OpenAI for chat + OpenAI for embeddings).
"""

from __future__ import annotations

import os
from typing import List, Optional

from ...config import Config
from .base import EmbeddingClient, EmbeddingError


class OpenAIEmbeddingClient(EmbeddingClient):
    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        dim: Optional[int] = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("EMBEDDING_API_KEY")
            or Config.LLM_API_KEY
        )
        self.base_url = (
            base_url
            or os.environ.get("EMBEDDING_BASE_URL")
            or Config.LLM_BASE_URL
        )
        self.model = model or Config.EMBEDDING_MODEL
        self.dim = dim if dim is not None else Config.EMBEDDING_DIM
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise EmbeddingError(
                "OpenAI embedding client requires LLM_API_KEY (or EMBEDDING_API_KEY)."
            )
        try:
            from openai import OpenAI
        except ImportError as e:
            raise EmbeddingError("openai package is not installed") from e
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._ensure_client()
        try:
            resp = client.embeddings.create(model=self.model, input=texts)
        except Exception as e:
            raise EmbeddingError(f"OpenAI embeddings call failed: {e}") from e
        return [item.embedding for item in resp.data]
