from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from upgrade_copilot.index.models import SourceDocument
from upgrade_copilot.ingest.sources import SourceSpec


USER_AGENT = "upgrade-copilot/0.1"


def fetch_text(url: str, timeout: int = 20) -> str:
    parsed = urlparse(url)
    if parsed.scheme in {"", "file"}:
        path = Path(parsed.path if parsed.scheme else url)
        return path.read_text(encoding="utf-8")

    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _cache_path(cache_dir: Path, source_id: str) -> Path:
    return cache_dir / "{source_id}.html".format(source_id=source_id)


def fetch_source(
    spec: SourceSpec,
    timeout: int = 20,
    cache_dir: Optional[Path] = None,
    refresh: bool = False,
) -> SourceDocument:
    content = None
    if cache_dir is not None:
        cached = _cache_path(cache_dir, spec.source_id)
        if cached.exists() and not refresh:
            content = cached.read_text(encoding="utf-8")

    if content is None:
        content = fetch_text(spec.url, timeout=timeout)
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            _cache_path(cache_dir, spec.source_id).write_text(content, encoding="utf-8")

    metadata = {"tags": list(spec.tags), "fetched_from": spec.url}
    return SourceDocument(
        source_id=spec.source_id,
        library=spec.library,
        title=spec.title,
        url=spec.url,
        content=content,
        metadata=metadata,
    )


def fetch_sources(
    specs: list[SourceSpec],
    timeout: int = 20,
    cache_dir: Optional[Path] = None,
    refresh: bool = False,
) -> list[SourceDocument]:
    return [
        fetch_source(spec, timeout=timeout, cache_dir=cache_dir, refresh=refresh)
        for spec in specs
    ]
