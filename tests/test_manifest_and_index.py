from pathlib import Path

from upgrade_copilot.api import UpgradeCopilot
from upgrade_copilot.ingest.sources import load_source_specs


def test_load_source_specs_from_manifest() -> None:
    specs = load_source_specs(Path("data/official_sources.json"))

    assert len(specs) >= 5
    assert specs[0].source_id == "pydantic-v2-migration"
    assert specs[1].library == "sqlalchemy"


def test_build_index_from_local_file_sources_and_reload(tmp_path: Path) -> None:
    pydantic_html = tmp_path / "pydantic.html"
    pydantic_html.write_text(
        """
        <html><body>
          <h1>Continue using v1</h1>
          <p>Import from pydantic.v1 during migration when you need compatibility.</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    numpy_html = tmp_path / "numpy.html"
    numpy_html.write_text(
        """
        <html><body>
          <h1>Automation</h1>
          <p>NumPy documents Ruff rule NPY201 for automated fixes.</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        """
        [
          {
            "source_id": "pydantic-v2-migration",
            "library": "pydantic",
            "title": "Pydantic V2 Migration Guide",
            "url": "%s",
            "tags": ["migration", "official"]
          },
          {
            "source_id": "numpy-20-migration",
            "library": "numpy",
            "title": "NumPy 2.0 Migration Guide",
            "url": "%s",
            "tags": ["migration", "official"]
          }
        ]
        """
        % (pydantic_html.as_uri(), numpy_html.as_uri()),
        encoding="utf-8",
    )

    copilot = UpgradeCopilot()
    specs = load_source_specs(manifest)
    chunks = copilot.build_index_from_sources(specs, cache_dir=tmp_path / "cache")
    index_path = tmp_path / "index.json"
    copilot.save_index(index_path)

    assert chunks
    assert index_path.exists()

    reloaded = UpgradeCopilot()
    reloaded.load_index(index_path)
    results = reloaded.search("How do I keep using pydantic v1 while migrating to v2?")

    assert results
    assert results[0].chunk.source_id == "pydantic-v2-migration"
