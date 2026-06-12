from upgrade_copilot.index.models import SourceDocument
from upgrade_copilot.ingest.chunk import chunk_document
from upgrade_copilot.ingest.clean import clean_document


def test_clean_and_chunk_preserve_heading_path() -> None:
    document = SourceDocument(
        source_id="pydantic-doc",
        library="pydantic",
        title="fallback title",
        url="https://example.test/pydantic",
        content="""
        <html>
          <head><title>Pydantic Migration Guide</title></head>
          <body>
            <h1>Migrating to V2</h1>
            <p>Use the pydantic.v1 namespace if you need a compatibility bridge.</p>
            <h2>Automation</h2>
            <p>The bump-pydantic tool can help rewrite common patterns automatically.</p>
          </body>
        </html>
        """,
    )

    cleaned = clean_document(document)

    assert cleaned.title == "Pydantic Migration Guide"
    chunks = chunk_document(cleaned, chunk_size=120, chunk_overlap=20)

    assert len(chunks) == 2
    assert chunks[0].heading_path == ("Migrating to V2",)
    assert "compatibility bridge" in chunks[0].text
    assert chunks[1].heading_path == ("Migrating to V2", "Automation")
    assert "bump-pydantic" in chunks[1].text


def test_chunk_document_splits_long_blocks() -> None:
    text = " ".join(["session"] * 120)
    document = SourceDocument(
        source_id="sqlalchemy-doc",
        library="sqlalchemy",
        title="SQLAlchemy Migration",
        url="https://example.test/sqlalchemy",
        content=f"<html><body><h1>Sessions</h1><p>{text}</p></body></html>",
    )

    chunks = chunk_document(clean_document(document), chunk_size=160, chunk_overlap=32)

    assert len(chunks) > 1
    assert all(chunk.heading_path == ("Sessions",) for chunk in chunks)
