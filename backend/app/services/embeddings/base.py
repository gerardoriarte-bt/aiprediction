"""EmbeddingClient protocol + domain error."""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable


class EmbeddingError(Exception):
    """Raised when an embedding call fails in a recoverable way (rate limit,
    transient HTTP error). Callers should decide whether to retry."""


@runtime_checkable
class EmbeddingClient(Protocol):
    name: str  # 'openai' | 'ollama'
    model: str
    dim: int

    def embed(self, text: str) -> List[float]:
        """Single-text embedding."""
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding; same order as input."""
        ...
