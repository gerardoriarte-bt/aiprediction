"""
Ollama embedding client.

Talks to a local Ollama instance over HTTP. Default base URL is
http://localhost:11434. Default model is `nomic-embed-text` (768 dim);
override via EMBEDDING_MODEL / EMBEDDING_DIM if you pull a different
embed model (e.g. `mxbai-embed-large` -> 1024).
"""

from __future__ import annotations

import json
from typing import List, Optional
from urllib import error as urlerr
from urllib import request as urlreq

from ...config import Config
from .base import EmbeddingClient, EmbeddingError


class OllamaEmbeddingClient(EmbeddingClient):
    name = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        dim: Optional[int] = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or Config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or Config.EMBEDDING_MODEL
        self.dim = dim if dim is not None else Config.EMBEDDING_DIM
        self.timeout = timeout

    def embed(self, text: str) -> List[float]:
        return self._post_one(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Ollama's /api/embeddings endpoint takes a single 'prompt' per call.
        # Newer versions expose /api/embed which accepts batched input but
        # support varies by version, so we loop sequentially for portability.
        return [self._post_one(t) for t in texts]

    def _post_one(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        body = json.dumps({"model": self.model, "prompt": text}).encode("utf-8")
        req = urlreq.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlreq.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urlerr.HTTPError as e:
            raise EmbeddingError(f"Ollama HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}") from e
        except urlerr.URLError as e:
            raise EmbeddingError(
                f"Cannot reach Ollama at {self.base_url}. "
                f"Is `ollama serve` running? ({e.reason})"
            ) from e
        except Exception as e:
            raise EmbeddingError(f"Ollama embeddings call failed: {e}") from e

        embedding = payload.get("embedding")
        if not isinstance(embedding, list):
            raise EmbeddingError(f"Ollama response missing 'embedding': {payload}")
        return [float(x) for x in embedding]
