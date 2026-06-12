from __future__ import annotations

from hashlib import sha1

from upgrade_copilot.index.models import Chunk, CleanedDocument, TextBlock


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]

    parts: list[str] = []
    start = 0
    step = max(1, size - overlap)
    while start < len(text):
        end = min(len(text), start + size)
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        if end == len(text):
            break
        start += step
    return parts


def _chunk_id(source_id: str, heading_path: tuple[str, ...], text: str) -> str:
    digest = sha1(f"{source_id}|{' > '.join(heading_path)}|{text}".encode("utf-8")).hexdigest()
    return digest[:12]


def _make_chunk(document: CleanedDocument, heading_path: tuple[str, ...], text: str) -> Chunk:
    return Chunk(
        chunk_id=_chunk_id(document.source.source_id, heading_path, text),
        source_id=document.source.source_id,
        library=document.source.library,
        title=document.title,
        text=text,
        url=document.source.url,
        heading_path=heading_path,
        metadata=dict(document.source.metadata),
    )


def chunk_document(
    document: CleanedDocument,
    chunk_size: int = 420,
    chunk_overlap: int = 80,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading_stack: list[str] = []
    current_parts: list[str] = []
    current_heading_path: tuple[str, ...] = ()

    def flush_current() -> None:
        nonlocal current_parts, current_heading_path
        if not current_parts:
            return

        joined = " ".join(current_parts).strip()
        for piece in _split_text(joined, chunk_size, chunk_overlap):
            chunks.append(_make_chunk(document, current_heading_path, piece))
        current_parts = []

    for block in document.blocks:
        if block.kind == "heading":
            flush_current()
            assert block.level is not None
            heading_stack = heading_stack[: block.level - 1]
            heading_stack.append(block.text)
            current_heading_path = tuple(heading_stack)
            continue

        assert isinstance(block, TextBlock)
        if not block.text:
            continue

        candidate = " ".join([*current_parts, block.text]).strip()
        if current_parts and len(candidate) > chunk_size:
            flush_current()
        current_parts.append(block.text)

    flush_current()
    return chunks
