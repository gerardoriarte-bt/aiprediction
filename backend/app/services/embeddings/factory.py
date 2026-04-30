"""Embedding client factory: pick OpenAI or Ollama via Config.EMBEDDING_PROVIDER."""

from __future__ import annotations

import threading

from ...config import Config
from ...utils.logger import get_logger
from .base import EmbeddingClient


_logger = get_logger("mirofish.embeddings.factory")
_lock = threading.Lock()
_instance: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    """Return the singleton embedding client for the current process."""
    global _instance
    if _instance is not None:
        return _instance

    with _lock:
        if _instance is None:
            provider = (Config.EMBEDDING_PROVIDER or "openai").lower()
            if provider == "ollama":
                from .ollama_client import OllamaEmbeddingClient
                _logger.info(
                    "Selecting OllamaEmbeddingClient (model=%s, dim=%s)",
                    Config.EMBEDDING_MODEL,
                    Config.EMBEDDING_DIM,
                )
                _instance = OllamaEmbeddingClient()
            else:
                from .openai_client import OpenAIEmbeddingClient
                _logger.info(
                    "Selecting OpenAIEmbeddingClient (model=%s, dim=%s)",
                    Config.EMBEDDING_MODEL,
                    Config.EMBEDDING_DIM,
                )
                _instance = OpenAIEmbeddingClient()

    return _instance


def reset_embedding_client() -> None:
    global _instance
    with _lock:
        _instance = None
