from upgrade_copilot.api import UpgradeCopilot
from upgrade_copilot.index.models import SourceDocument


def _documents() -> list[SourceDocument]:
    return [
        SourceDocument(
            source_id="pydantic-v2",
            library="pydantic",
            title="Pydantic V2 Migration Guide",
            url="https://example.test/pydantic",
            content="""
            <html><body>
              <h1>Continue using v1</h1>
              <p>You can keep using Pydantic V1 features by importing through the pydantic.v1 namespace during migration.</p>
              <h2>Automation</h2>
              <p>The bump-pydantic tool can automatically rewrite many common APIs.</p>
            </body></html>
            """,
        ),
        SourceDocument(
            source_id="sqlalchemy-20",
            library="sqlalchemy",
            title="SQLAlchemy 2.0 Migration Guide",
            url="https://example.test/sqlalchemy",
            content="""
            <html><body>
              <h1>Migration strategy</h1>
              <p>The safest path is to run on SQLAlchemy 1.4 with all 2.0 deprecation warnings enabled before moving to 2.0.</p>
            </body></html>
            """,
        ),
    ]


def test_search_returns_relevant_official_section() -> None:
    copilot = UpgradeCopilot()
    copilot.ingest_documents(_documents())

    results = copilot.search("How do I keep using Pydantic v1 while migrating to v2?", k=3)

    assert results
    assert results[0].chunk.source_id == "pydantic-v2"
    assert "pydantic.v1 namespace" in results[0].chunk.text


def test_search_can_find_sqlalchemy_upgrade_path() -> None:
    copilot = UpgradeCopilot()
    copilot.ingest_documents(_documents())

    results = copilot.search("safest migration path from sqlalchemy 1.4 to 2.0", k=3)

    assert results[0].chunk.source_id == "sqlalchemy-20"
    assert "1.4" in results[0].chunk.text
