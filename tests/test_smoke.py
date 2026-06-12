from upgrade_copilot.api import UpgradeCopilot
from upgrade_copilot.eval.retrieval_eval import evaluate_retrieval
from upgrade_copilot.index.models import RetrievalExample, SourceDocument


def _documents() -> list[SourceDocument]:
    return [
        SourceDocument(
            source_id="pydantic-v2",
            library="pydantic",
            title="Pydantic Migration",
            url="https://example.test/pydantic",
            content="""
            <html><body>
              <h1>Continue using v1</h1>
              <p>The migration guide explains that the pydantic.v1 namespace is available while you migrate existing code.</p>
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
              <p>Use Ruff rule NPY201 to apply some automated migration fixes for NumPy 2.0.</p>
            </body></html>
            """,
        ),
    ]


def test_end_to_end_retrieval_first_flow() -> None:
    copilot = UpgradeCopilot()
    chunks = copilot.ingest_documents(_documents())

    assert len(chunks) >= 2

    results = copilot.search("keep using pydantic v1 while migrating")
    assert results[0].chunk.source_id == "pydantic-v2"

    answer = copilot.answer("Is there an automatic fix path for NumPy 2.0?")
    assert answer.supported is True
    assert any("NPY201" in result.chunk.text for result in answer.results)

    metrics = evaluate_retrieval(
        copilot.search_engine,
        [
            RetrievalExample(
                question="How do I keep using Pydantic v1 while migrating to v2?",
                expected_source_ids={"pydantic-v2"},
            ),
            RetrievalExample(
                question="automatic migration fixes for NumPy 2.0",
                expected_source_ids={"numpy-20"},
            ),
        ],
        k=3,
    )
    assert metrics.hit_rate_at_k == 1.0
