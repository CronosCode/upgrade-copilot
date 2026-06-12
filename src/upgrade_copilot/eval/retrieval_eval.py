from __future__ import annotations

from dataclasses import dataclass

from upgrade_copilot.index.models import RetrievalExample
from upgrade_copilot.retrieval.search import SearchEngine


@dataclass
class RetrievalMetrics:
    hit_rate_at_k: float
    mean_reciprocal_rank: float


def evaluate_retrieval(
    search_engine: SearchEngine,
    examples: list[RetrievalExample],
    k: int = 5,
) -> RetrievalMetrics:
    if not examples:
        return RetrievalMetrics(hit_rate_at_k=0.0, mean_reciprocal_rank=0.0)

    hits = 0
    reciprocal_ranks = 0.0

    for example in examples:
        results = search_engine.search(example.question, k=k)
        ranked_chunk_ids = [result.chunk.chunk_id for result in results]
        ranked_source_ids = [result.chunk.source_id for result in results]

        matched_rank = None
        for rank, (chunk_id, source_id) in enumerate(zip(ranked_chunk_ids, ranked_source_ids), start=1):
            if example.expected_chunk_ids and chunk_id in example.expected_chunk_ids:
                matched_rank = rank
                break
            if example.expected_source_ids and source_id in example.expected_source_ids:
                matched_rank = rank
                break

        if matched_rank is not None:
            hits += 1
            reciprocal_ranks += 1.0 / matched_rank

    total = len(examples)
    return RetrievalMetrics(
        hit_rate_at_k=hits / total,
        mean_reciprocal_rank=reciprocal_ranks / total,
    )
