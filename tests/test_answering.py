from upgrade_copilot.api import UpgradeCopilot
from upgrade_copilot.index.models import AnswerExample, SourceDocument
from upgrade_copilot.eval.answer_eval import evaluate_answers


def _documents() -> list[SourceDocument]:
    return [
        SourceDocument(
            source_id="fastapi-v2",
            library="fastapi",
            title="FastAPI Pydantic v2 Migration",
            url="https://example.test/fastapi",
            content="""
            <html><body>
              <h1>Before you migrate</h1>
              <p>FastAPI recommends upgrading FastAPI itself to a version that supports Pydantic v2 before changing application models.</p>
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
              <p>NumPy documents a Ruff migration rule named NPY201 to help automate some updates for NumPy 2.0.</p>
            </body></html>
            """,
        ),
    ]


def test_answer_contains_citations_for_supported_question() -> None:
    copilot = UpgradeCopilot()
    copilot.ingest_documents(_documents())

    answer = copilot.answer("What does FastAPI recommend before moving to Pydantic v2?")

    assert answer.supported is True
    assert "[1]" in answer.text
    assert answer.citations
    assert answer.citations[0].url == "https://example.test/fastapi"


def test_answer_abstains_when_docs_do_not_support_question() -> None:
    copilot = UpgradeCopilot()
    copilot.ingest_documents(_documents())

    answer = copilot.answer("How should I migrate Django models to async ORM?")

    assert answer.supported is False
    assert "cannot answer" in answer.text.lower()


def test_answer_evaluation_tracks_citations_and_abstention() -> None:
    copilot = UpgradeCopilot()
    copilot.ingest_documents(_documents())

    metrics = evaluate_answers(
        copilot.search_engine,
        [
            AnswerExample(
                question="Is there an automatic fix path for NumPy 2.0?",
                should_answer=True,
            ),
            AnswerExample(
                question="How do I upgrade Terraform state files?",
                should_answer=False,
            ),
        ],
    )

    assert metrics.citation_rate >= 0.5
    assert metrics.abstention_accuracy >= 0.5
