from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Union

from upgrade_copilot.index.models import Chunk


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


@dataclass
class FaissStore:
    chunks: list[Chunk] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Chunk/vector counts must match")
        self.chunks.extend(chunks)
        self.vectors.extend(vectors)

    def search(
        self,
        query_vector: list[float],
        k: int = 5,
        filters: Optional[dict[str, str]] = None,
    ) -> list[tuple[Chunk, float]]:
        candidates: list[tuple[Chunk, float]] = []
        for chunk, vector in zip(self.chunks, self.vectors):
            if filters and not _matches_filters(chunk, filters):
                continue
            score = cosine_similarity(query_vector, vector)
            candidates.append((chunk, score))
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates[:k]

    def save(self, path: Union[str, Path]) -> None:
        payload = {
            "chunks": [asdict(chunk) for chunk in self.chunks],
            "vectors": self.vectors,
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Union[str, Path]) -> "FaissStore":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        chunks = [Chunk(**chunk) for chunk in payload["chunks"]]
        vectors = payload["vectors"]
        return cls(chunks=chunks, vectors=vectors)


def _matches_filters(chunk: Chunk, filters: dict[str, str]) -> bool:
    for key, expected in filters.items():
        value = getattr(chunk, key, chunk.metadata.get(key))
        if value != expected:
            return False
    return True
