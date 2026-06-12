from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


def _env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


@dataclass
class Settings:
    repo_root: Path = field(default_factory=lambda: _env_path("UPGRADE_COPILOT_REPO_ROOT", str(Path.cwd())))
    data_dir: Path = field(default_factory=lambda: _env_path("UPGRADE_COPILOT_DATA_DIR", "data"))
    cache_dir: Path = field(default_factory=lambda: _env_path("UPGRADE_COPILOT_CACHE_DIR", "data/cache"))
    index_path: Path = field(default_factory=lambda: _env_path("UPGRADE_COPILOT_INDEX_PATH", "data/index.json"))
    chunk_size: int = field(default_factory=lambda: _env_int("UPGRADE_COPILOT_CHUNK_SIZE", 420))
    chunk_overlap: int = field(default_factory=lambda: _env_int("UPGRADE_COPILOT_CHUNK_OVERLAP", 80))
    embedding_dimension: int = field(default_factory=lambda: _env_int("UPGRADE_COPILOT_EMBEDDING_DIMENSION", 192))
    search_top_k: int = field(default_factory=lambda: _env_int("UPGRADE_COPILOT_SEARCH_TOP_K", 5))
    min_answer_score: float = field(default_factory=lambda: _env_float("UPGRADE_COPILOT_MIN_ANSWER_SCORE", 0.28))
    preferred_library_boost: float = field(default_factory=lambda: _env_float("UPGRADE_COPILOT_PREFERRED_LIBRARY_BOOST", 0.12))


DEFAULT_SETTINGS = Settings()
