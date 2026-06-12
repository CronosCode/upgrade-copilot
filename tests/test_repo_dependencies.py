from pathlib import Path

from upgrade_copilot.api import UpgradeCopilot
from upgrade_copilot.config import Settings
from upgrade_copilot.index.models import SourceDocument
from upgrade_copilot.repo import detect_dependencies_from_files, detect_repository_dependencies


def test_detect_repository_dependencies_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        dependencies = [
          "fastapi>=0.110",
          "pydantic>=2",
          "sqlalchemy>=2",
        ]
        """,
        encoding="utf-8",
    )

    dependencies = detect_repository_dependencies(tmp_path)

    assert [item.library for item in dependencies] == ["fastapi", "pydantic", "sqlalchemy"]
    assert all("pyproject.toml" in item.files for item in dependencies)


def test_detect_dependencies_from_uploaded_files() -> None:
    dependencies = detect_dependencies_from_files(
        {
            "services/api/pyproject.toml": 'dependencies = ["pydantic>=2", "numpy>=2"]',
            "requirements.txt": "sqlalchemy>=2\n",
        }
    )

    assert [item.library for item in dependencies] == ["numpy", "pydantic", "sqlalchemy"]
    assert dependencies[0].files == ["services/api/pyproject.toml"]


def test_search_biases_toward_detected_repo_libraries(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        dependencies = ["numpy>=2.0"]
        """,
        encoding="utf-8",
    )

    documents = [
        SourceDocument(
            source_id="pydantic-v2",
            library="pydantic",
            title="Pydantic V2 Migration Guide",
            url="https://example.test/pydantic",
            content="""
            <html><body>
              <h1>Automation</h1>
              <p>The bump-pydantic tool can automatically rewrite many common APIs during migration.</p>
            </body></html>
            """,
        ),
        SourceDocument(
            source_id="numpy-20",
            library="numpy",
            title="NumPy 2.0 Migration Guide",
            url="https://example.test/numpy",
            content="""
            <html><body>
              <h1>Automation</h1>
              <p>NumPy documents Ruff rule NPY201 for automated migration fixes in NumPy 2.0.</p>
            </body></html>
            """,
        ),
    ]

    copilot = UpgradeCopilot(settings=Settings(repo_root=tmp_path))
    copilot.ingest_documents(documents)

    results = copilot.search(
        "automatic migration fixes",
        preferred_libraries=copilot.preferred_libraries(),
    )

    assert results[0].chunk.library == "numpy"
