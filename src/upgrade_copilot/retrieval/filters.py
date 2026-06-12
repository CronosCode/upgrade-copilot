from __future__ import annotations

from typing import Optional

from upgrade_copilot.index.models import Chunk


def apply_filters(chunks: list[Chunk], filters: Optional[dict[str, str]] = None) -> list[Chunk]:
    if not filters:
        return chunks

    filtered: list[Chunk] = []
    for chunk in chunks:
        include = True
        for key, expected in filters.items():
            value = getattr(chunk, key, chunk.metadata.get(key))
            if value != expected:
                include = False
                break
        if include:
            filtered.append(chunk)
    return filtered
