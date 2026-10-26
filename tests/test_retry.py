import pytest

from mechragnic.ingest.pipeline import should_retry
from mechragnic.models.ingest_questions import IngestPendingReason, PendingQuestion
from mechragnic.models.stack_exchange import ApiQuestion


def pending(reason: IngestPendingReason, answer_count: int) -> PendingQuestion:
    return PendingQuestion(question_id=1, reason=reason, answer_count=answer_count)


def current(answer_count: int) -> ApiQuestion:
    return ApiQuestion(
        question_id=1,
        creation_date=0,
        title="title",
        body="body",
        tags=[],
        is_answered=answer_count > 0,
        answer_count=answer_count,
    )


@pytest.mark.parametrize("reason", [IngestPendingReason.OLLAMA_ERROR, IngestPendingReason.DB_ERROR])
def test_external_errors_are_always_retried(reason):
    assert should_retry(pending(reason, answer_count=2), current(answer_count=2))


@pytest.mark.parametrize("reason", [IngestPendingReason.NO_ANSWER, IngestPendingReason.INVALID_CASE])
def test_deterministic_failures_are_retried_when_new_answers_arrive(reason):
    assert should_retry(pending(reason, answer_count=0), current(answer_count=1))


@pytest.mark.parametrize("reason", [IngestPendingReason.NO_ANSWER, IngestPendingReason.INVALID_CASE])
@pytest.mark.parametrize("current_answer_count", [1, 0])
def test_deterministic_failures_are_not_retried_without_new_answers(reason, current_answer_count):
    assert not should_retry(pending(reason, answer_count=1), current(answer_count=current_answer_count))
