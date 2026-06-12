from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


Metadata = dict[str, Any]


@dataclass
class SourceDocument:
    source_id: str
    library: str
    title: str
    url: str
    content: str
    metadata: Metadata = field(default_factory=dict)


@dataclass
class TextBlock:
    kind: str
    text: str
    level: Optional[int] = None


@dataclass
class CleanedDocument:
    source: SourceDocument
    title: str
    blocks: list[TextBlock]


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    library: str
    title: str
    text: str
    url: str
    heading_path: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass
class SearchResult:
    chunk: Chunk
    score: float
    semantic_score: float
    lexical_score: float


@dataclass
class Citation:
    label: str
    url: str
    chunk_id: str
    title: str


@dataclass
class Answer:
    question: str
    text: str
    supported: bool
    citations: list[Citation]
    results: list[SearchResult]


@dataclass
class RetrievalExample:
    question: str
    expected_chunk_ids: set[str] = field(default_factory=set)
    expected_source_ids: set[str] = field(default_factory=set)


@dataclass
class AnswerExample:
    question: str
    should_answer: bool
