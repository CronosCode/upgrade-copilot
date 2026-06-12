from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


SUPPORTED_LIBRARY_ALIASES = {
    "fastapi": ("fastapi",),
    "numpy": ("numpy",),
    "pandas": ("pandas",),
    "pydantic": ("pydantic", "pydantic-settings", "pydantic-extra-types"),
    "sqlalchemy": ("sqlalchemy", "sqlmodel", "alembic"),
}

DEPENDENCY_FILENAMES = (
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.in",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
)


@dataclass
class RepositoryDependency:
    library: str
    matches: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)


def detect_repository_dependencies(repo_root: Path) -> list[RepositoryDependency]:
    repo_root = repo_root.resolve()
    candidates = _dependency_files(repo_root)
    return detect_dependencies_from_files(
        {str(path.relative_to(repo_root)): path.read_text(encoding="utf-8", errors="replace") for path in candidates}
    )


def detect_dependencies_from_files(files: Mapping[str, str]) -> list[RepositoryDependency]:
    detected: list[RepositoryDependency] = []

    for library, aliases in SUPPORTED_LIBRARY_ALIASES.items():
        matched_aliases: set[str] = set()
        matched_files: set[str] = set()
        for filename, content in files.items():
            text = content.lower()
            for alias in aliases:
                if _contains_dependency_name(text, alias):
                    matched_aliases.add(alias)
                    matched_files.add(filename)
        if matched_aliases:
            detected.append(
                RepositoryDependency(
                    library=library,
                    matches=sorted(matched_aliases),
                    files=sorted(matched_files),
                )
            )

    detected.sort(key=lambda item: item.library)
    return detected


def preferred_libraries_for_repo(repo_root: Path) -> set[str]:
    return {dependency.library for dependency in detect_repository_dependencies(repo_root)}


def _dependency_files(repo_root: Path) -> list[Path]:
    return [path for path in (repo_root / name for name in DEPENDENCY_FILENAMES) if path.exists()]


def _contains_dependency_name(text: str, name: str) -> bool:
    pattern = r"(?<![a-z0-9_-]){name}(?![a-z0-9_-])".format(name=re.escape(name.lower()))
    return re.search(pattern, text) is not None
