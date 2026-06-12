from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

from upgrade_copilot.index.models import SourceDocument


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    library: str
    title: str
    url: str
    tags: tuple[str, ...] = ()

    def to_placeholder_document(self) -> SourceDocument:
        return SourceDocument(
            source_id=self.source_id,
            library=self.library,
            title=self.title,
            url=self.url,
            content="",
            metadata={"tags": list(self.tags)},
        )


DEFAULT_SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        source_id="pydantic-v2-migration",
        library="pydantic",
        title="Pydantic V2 Migration Guide",
        url="https://docs.pydantic.dev/latest/migration/",
        tags=("migration", "official"),
    ),
    SourceSpec(
        source_id="sqlalchemy-20-migration",
        library="sqlalchemy",
        title="SQLAlchemy 2.0 Major Migration Guide",
        url="https://docs.sqlalchemy.org/en/14/changelog/migration_20.html",
        tags=("migration", "official"),
    ),
    SourceSpec(
        source_id="fastapi-pydantic-v2",
        library="fastapi",
        title="FastAPI How To: Migrate from Pydantic v1 to Pydantic v2",
        url="https://fastapi.tiangolo.com/how-to/migrate-from-pydantic-v1-to-pydantic-v2/",
        tags=("migration", "official"),
    ),
    SourceSpec(
        source_id="numpy-20-migration",
        library="numpy",
        title="NumPy 2.0 Migration Guide",
        url="https://numpy.org/doc/stable/numpy_2_0_migration_guide.html",
        tags=("migration", "official"),
    ),
    SourceSpec(
        source_id="pandas-20-whatsnew",
        library="pandas",
        title="What's New in pandas 2.0.0",
        url="https://pandas.pydata.org/docs/whatsnew/v2.0.0.html",
        tags=("breaking-changes", "official"),
    ),
)


def default_sources() -> list[SourceSpec]:
    return list(DEFAULT_SOURCES)


def load_source_specs(path: Union[str, Path]) -> list[SourceSpec]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [SourceSpec(**item) for item in payload]


def save_source_specs(path: Union[str, Path], specs: Iterable[SourceSpec]) -> None:
    payload = [
        {
            "source_id": spec.source_id,
            "library": spec.library,
            "title": spec.title,
            "url": spec.url,
            "tags": list(spec.tags),
        }
        for spec in specs
    ]
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def resolve_sources(manifest_path: Optional[Union[str, Path]] = None) -> list[SourceSpec]:
    if manifest_path is None:
        return default_sources()
    return load_source_specs(manifest_path)
