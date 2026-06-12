from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Set

from upgrade_copilot.index.embeddings import Embedder
from upgrade_copilot.index.faiss_store import FaissStore
from upgrade_copilot.index.models import SearchResult


TOKEN_RE = re.compile(r"[a-z0-9_]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "the",
    "to",
    "what",
    "while",
}


def _tokenize(text: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS}


def _lexical_score(query: str, text: str, heading_path: tuple[str, ...]) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0
    body_tokens = _tokenize(text) | _tokenize(" ".join(heading_path))
    overlap = query_tokens & body_tokens
    return len(overlap) / len(query_tokens)


@dataclass
class SearchEngine:
    store: FaissStore
    embedder: Embedder
    preferred_library_boost: float = 0.12

    def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[dict[str, str]] = None,
        preferred_libraries: Optional[Set[str]] = None,
        library_filter: Optional[Set[str]] = None,
    ) -> list[SearchResult]:
        query_vector = self.embedder.embed(query)
        initial = self.store.search(query_vector, k=max(k * 4, 10), filters=filters)

        reranked: list[SearchResult] = []
        for chunk, semantic_score in initial:
            if library_filter and chunk.library not in library_filter:
                continue
            lexical = _lexical_score(query, chunk.text, chunk.heading_path)
            score = semantic_score * 0.7 + lexical * 0.3
            if preferred_libraries and chunk.library in preferred_libraries:
                score += self.preferred_library_boost
            reranked.append(
                SearchResult(
                    chunk=chunk,
                    score=score,
                    semantic_score=semantic_score,
                    lexical_score=lexical,
                )
            )

        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:k]
