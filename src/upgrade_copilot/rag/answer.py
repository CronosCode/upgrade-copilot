from __future__ import annotations

import re

from upgrade_copilot.index.models import Answer, SearchResult
from upgrade_copilot.rag.citations import build_citations
from typing import Optional, Set

from upgrade_copilot.retrieval.search import _tokenize
from upgrade_copilot.retrieval.search import SearchEngine


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _best_sentences(question: str, results: list[SearchResult], limit: int = 3) -> list[tuple[str, int]]:
    query_tokens = _tokenize(question)
    scored: list[tuple[float, str, int]] = []

    for citation_index, result in enumerate(results, start=1):
        for sentence in SENTENCE_SPLIT_RE.split(result.chunk.text):
            sentence = sentence.strip()
            if len(sentence) < 24:
                continue
            overlap = len(query_tokens & _tokenize(sentence))
            score = overlap + result.score
            scored.append((score, sentence, citation_index))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[str, int]] = []
    seen_sentences: set[str] = set()
    for _, sentence, citation_index in scored:
        if sentence in seen_sentences:
            continue
        seen_sentences.add(sentence)
        selected.append((sentence, citation_index))
        if len(selected) == limit:
            break
    return selected


def answer_question(
    question: str,
    search_engine: SearchEngine,
    k: int = 4,
    min_score: float = 0.28,
    preferred_libraries: Optional[Set[str]] = None,
    library_filter: Optional[Set[str]] = None,
) -> Answer:
    results = search_engine.search(
        question,
        k=k,
        preferred_libraries=preferred_libraries,
        library_filter=library_filter,
    )
    if not results or results[0].score < min_score or results[0].lexical_score < 0.2:
        return Answer(
            question=question,
            text="I cannot answer from the indexed official migration docs with enough confidence.",
            supported=False,
            citations=[],
            results=results,
        )

    supporting_results = [
        result
        for result in results
        if result.lexical_score >= max(0.2, results[0].lexical_score * 0.5)
    ]
    citations = build_citations(supporting_results)

    selected = _best_sentences(question, supporting_results)
    if not selected:
        return Answer(
            question=question,
            text="I found relevant documents, but not enough explicit evidence to answer safely.",
            supported=False,
            citations=citations,
            results=results,
        )

    parts = [f"{sentence} [{citation_index}]" for sentence, citation_index in selected]
    answer_text = " ".join(parts)
    return Answer(
        question=question,
        text=answer_text,
        supported=True,
        citations=citations[: len(selected)],
        results=results,
    )
