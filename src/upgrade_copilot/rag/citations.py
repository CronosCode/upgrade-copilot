from __future__ import annotations

from upgrade_copilot.index.models import Citation, SearchResult


def build_citations(results: list[SearchResult]) -> list[Citation]:
    citations: list[Citation] = []
    seen_chunk_ids: set[str] = set()
    for index, result in enumerate(results, start=1):
        if result.chunk.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(result.chunk.chunk_id)
        heading = " > ".join(result.chunk.heading_path)
        title = result.chunk.title if not heading else f"{result.chunk.title}: {heading}"
        citations.append(
            Citation(
                label=f"[{index}] {title}",
                url=result.chunk.url,
                chunk_id=result.chunk.chunk_id,
                title=title,
            )
        )
    return citations
