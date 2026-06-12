from __future__ import annotations

import hashlib
import importlib.util
import math
import re
from dataclasses import dataclass
from typing import Protocol


TOKEN_RE = re.compile(r"[a-z0-9_]+")


class Embedder(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]:
        ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        ...


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


@dataclass
class HashingEmbedder:
    dimension: int = 192

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        return _normalize(vector)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


@dataclass
class SentenceTransformerEmbedder:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384

    def __post_init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)

    def embed(self, text: str) -> list[float]:
        return list(self._model.encode(text, normalize_embeddings=True))

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [list(vector) for vector in self._model.encode(texts, normalize_embeddings=True)]


def default_embedder(prefer_sentence_transformers: bool = False, dimension: int = 192) -> Embedder:
    if prefer_sentence_transformers and importlib.util.find_spec("sentence_transformers"):
        return SentenceTransformerEmbedder()
    return HashingEmbedder(dimension=dimension)
