"""Turn chunk text into embedding vectors.

Two implementations behind one small interface:
- OpenAIEmbedder: the real one (text-embedding-3-small, 1,536 numbers per text).
- FakeEmbedder: deterministic vectors from a hash. No network, no key, no cost.
  Used by the tests, and locally until you have an API key. Its vectors carry
  no meaning, so only keyword search is useful with it.
"""

import hashlib
import math
import random
from functools import lru_cache
from typing import Protocol

from openai import OpenAI

from app.config import get_settings
from app.models.chunk import EMBEDDING_DIM

BATCH_SIZE = 100  # texts per API call


class Embedder(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        # The SDK already retries rate limits and 5xx errors with backoff.
        self._client = OpenAI(api_key=api_key, max_retries=3, timeout=60)
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            response = self._client.embeddings.create(model=self.model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend(item.embedding for item in ordered)
        return vectors


class FakeEmbedder:
    model = "fake-hash-v1"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
        rng = random.Random(seed)
        raw = [rng.gauss(0, 1) for _ in range(EMBEDDING_DIM)]
        norm = math.sqrt(sum(x * x for x in raw))
        return [x / norm for x in raw]


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedding_backend == "fake":
        return FakeEmbedder()
    key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not key:
        raise RuntimeError("EMBEDDING_BACKEND=openai needs OPENAI_API_KEY to be set")
    return OpenAIEmbedder(key, settings.embedding_model)
