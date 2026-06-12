from __future__ import annotations

from dataclasses import dataclass

from upgrade_copilot.index.models import AnswerExample
from upgrade_copilot.rag.answer import answer_question
from upgrade_copilot.retrieval.search import SearchEngine


@dataclass
class AnswerMetrics:
    citation_rate: float
    abstention_accuracy: float


def evaluate_answers(
    search_engine: SearchEngine,
    examples: list[AnswerExample],
    k: int = 4,
) -> AnswerMetrics:
    if not examples:
        return AnswerMetrics(citation_rate=0.0, abstention_accuracy=0.0)

    answers = [answer_question(example.question, search_engine, k=k) for example in examples]
    citation_rate = sum(1 for answer in answers if answer.citations) / len(answers)
    abstention_accuracy = (
        sum(1 for answer, example in zip(answers, examples) if answer.supported == example.should_answer)
        / len(answers)
    )
    return AnswerMetrics(citation_rate=citation_rate, abstention_accuracy=abstention_accuracy)
