from __future__ import annotations

from pathlib import Path
from typing import Optional, Set

from upgrade_copilot.config import Settings
from upgrade_copilot.index.embeddings import default_embedder
from upgrade_copilot.index.faiss_store import FaissStore
from upgrade_copilot.index.models import Answer, Chunk, SearchResult, SourceDocument
from upgrade_copilot.ingest.chunk import chunk_document
from upgrade_copilot.ingest.clean import clean_document
from upgrade_copilot.ingest.fetch import fetch_sources
from upgrade_copilot.ingest.sources import SourceSpec
from upgrade_copilot.rag.answer import answer_question
from upgrade_copilot.repo import (
    RepositoryDependency,
    detect_dependencies_from_files,
    detect_repository_dependencies,
    preferred_libraries_for_repo,
)
from upgrade_copilot.retrieval.search import SearchEngine


class UpgradeCopilot:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self.embedder = default_embedder(dimension=self.settings.embedding_dimension)
        self.store = FaissStore()
        self.search_engine = SearchEngine(
            store=self.store,
            embedder=self.embedder,
            preferred_library_boost=self.settings.preferred_library_boost,
        )

    def ingest_documents(self, documents: list[SourceDocument]) -> list[Chunk]:
        self.store = FaissStore()
        self.search_engine = SearchEngine(
            store=self.store,
            embedder=self.embedder,
            preferred_library_boost=self.settings.preferred_library_boost,
        )
        cleaned = [clean_document(document) for document in documents]
        chunks = [
            chunk
            for document in cleaned
            for chunk in chunk_document(
                document,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
        ]
        vectors = self.embedder.embed_many([chunk.text for chunk in chunks])
        self.store.add(chunks, vectors)
        return chunks

    def build_index_from_sources(
        self,
        specs: list[SourceSpec],
        cache_dir: Optional[Path] = None,
        refresh: bool = False,
        timeout: int = 20,
    ) -> list[Chunk]:
        documents = fetch_sources(specs, timeout=timeout, cache_dir=cache_dir, refresh=refresh)
        return self.ingest_documents(documents)

    def save_index(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.store.save(path)

    def load_index(self, path: Path) -> None:
        self.store = FaissStore.load(path)
        self.search_engine = SearchEngine(
            store=self.store,
            embedder=self.embedder,
            preferred_library_boost=self.settings.preferred_library_boost,
        )

    def detect_repository_dependencies(self, repo_root: Optional[Path] = None) -> list[RepositoryDependency]:
        return detect_repository_dependencies((repo_root or self.settings.repo_root).resolve())

    def preferred_libraries(self, repo_root: Optional[Path] = None) -> set[str]:
        return preferred_libraries_for_repo((repo_root or self.settings.repo_root).resolve())

    def scan_repository(
        self,
        repo_root: Optional[Path] = None,
        dependency_files: Optional[dict[str, str]] = None,
        k: Optional[int] = None,
    ) -> dict:
        dependencies = (
            detect_dependencies_from_files(dependency_files)
            if dependency_files is not None
            else self.detect_repository_dependencies(repo_root)
        )
        guidance = []
        for dependency in dependencies:
            question = _scan_question_for_library(dependency.library)
            answer = self.answer(
                question,
                k=k or self.settings.search_top_k,
                preferred_libraries={dependency.library},
                library_filter={dependency.library},
            )
            guidance.append(
                {
                    "library": dependency.library,
                    "question": question,
                    "supported": answer.supported,
                    "summary": answer.text,
                    "citations": [
                        {
                            "label": citation.label,
                            "title": citation.title,
                            "url": citation.url,
                            "chunk_id": citation.chunk_id,
                        }
                        for citation in answer.citations
                    ],
                    "top_results": [
                        {
                            "score": result.score,
                            "source_id": result.chunk.source_id,
                            "title": result.chunk.title,
                            "heading_path": list(result.chunk.heading_path),
                            "url": result.chunk.url,
                        }
                        for result in answer.results[:3]
                    ],
                }
            )
        return {
            "repo_root": str((repo_root or self.settings.repo_root).resolve()) if dependency_files is None else None,
            "dependency_count": len(dependencies),
            "dependencies": [
                {
                    "library": dependency.library,
                    "matches": dependency.matches,
                    "files": dependency.files,
                }
                for dependency in dependencies
            ],
            "guidance": guidance,
        }

    def search(
        self,
        query: str,
        k: Optional[int] = None,
        preferred_libraries: Optional[Set[str]] = None,
        library_filter: Optional[Set[str]] = None,
    ) -> list[SearchResult]:
        return self.search_engine.search(
            query,
            k=k or self.settings.search_top_k,
            preferred_libraries=preferred_libraries,
            library_filter=library_filter,
        )

    def answer(
        self,
        question: str,
        k: Optional[int] = None,
        preferred_libraries: Optional[Set[str]] = None,
        library_filter: Optional[Set[str]] = None,
    ) -> Answer:
        return answer_question(
            question,
            self.search_engine,
            k=k or self.settings.search_top_k,
            min_score=self.settings.min_answer_score,
            preferred_libraries=preferred_libraries,
            library_filter=library_filter,
        )


def _scan_question_for_library(library: str) -> str:
    questions = {
        "fastapi": "What should I check before upgrading FastAPI projects that use Pydantic v2?",
        "numpy": "What are the key migration steps and automated checks for NumPy 2.0?",
        "pandas": "What should I review before upgrading to pandas 2.0?",
        "pydantic": "How do I keep using Pydantic v1 while migrating to Pydantic v2?",
        "sqlalchemy": "What are the key steps for migrating SQLAlchemy projects to 2.0?",
    }
    return questions.get(library, "What should I check before upgrading {library}?".format(library=library))
