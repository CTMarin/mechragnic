from collections import Counter
from datetime import datetime
from logging import INFO, WARNING, basicConfig, getLogger

from asyncpg import Connection, PostgresError
from httpx import ConnectError, HTTPError
from pydantic import ValidationError

from mechragnic.clients.ollama import create_embedding
from mechragnic.database.cases import insert_case
from mechragnic.database.connection import connect
from mechragnic.database.ingest_questions import get_pending_questions, get_processed_question_ids, record_question
from mechragnic.embedding.text import text_for_embedding
from mechragnic.ingest.stackexchange import build_cases, fetch_answers, fetch_questions, fetch_questions_by_ids
from mechragnic.ingest.synthesis import synthesize
from mechragnic.models.ingest_questions import (
    IngestPendingReason,
    IngestStatus,
    IngestSummary,
    PendingQuestion,
    QuestionOutcome,
)
from mechragnic.models.mechanic_case import SynthesizedCase
from mechragnic.models.stack_exchange import ApiAnswer, ApiQuestion, QuestionWithAnswers

logger = getLogger(__name__)

EXTERNAL_REASONS: set[IngestPendingReason] = {IngestPendingReason.DB_ERROR, IngestPendingReason.OLLAMA_ERROR}


class QuestionPending(Exception):
    def __init__(self, reason: IngestPendingReason):
        super().__init__(reason)
        self.reason = reason


async def build_case(question: QuestionWithAnswers) -> tuple[SynthesizedCase, list[float]] | None:
    if not question.answers:
        raise QuestionPending(IngestPendingReason.NO_ANSWER)

    try:
        case = await synthesize(question)
    except ValidationError as error:
        raise QuestionPending(IngestPendingReason.INVALID_CASE) from error
    except ConnectError:
        raise
    except HTTPError as error:
        raise QuestionPending(IngestPendingReason.OLLAMA_ERROR) from error

    if not case.is_fault_diagnosis:
        return None

    text = text_for_embedding(case.symptoms, case.causes, case.solution, include_solutions=False)
    try:
        embedding = await create_embedding(text)
    except ConnectError:
        raise
    except HTTPError as error:
        raise QuestionPending(IngestPendingReason.OLLAMA_ERROR) from error

    return case, embedding


async def process_question(db_connection: Connection, question: QuestionWithAnswers) -> QuestionOutcome:
    try:
        built_case: tuple[SynthesizedCase, list[float]] | None = await build_case(question)
    except QuestionPending as pending:
        await _record(db_connection, question, IngestStatus.PENDING, pending.reason)
        return QuestionOutcome(IngestStatus.PENDING, pending.reason)

    if built_case is None:
        await _record(db_connection, question, IngestStatus.SKIPPED, None)
        return QuestionOutcome(IngestStatus.SKIPPED, None)

    case, embedding = built_case
    try:
        async with db_connection.transaction():
            await _record(db_connection, question, IngestStatus.INSERTED, None)
            await insert_case(db_connection, question.question_id, case, embedding)
    except PostgresError:
        await _record(db_connection, question, IngestStatus.PENDING, IngestPendingReason.DB_ERROR)
        return QuestionOutcome(IngestStatus.PENDING, IngestPendingReason.DB_ERROR)

    return QuestionOutcome(IngestStatus.INSERTED, None)


async def ingest_window(start: datetime, end: datetime) -> IngestSummary:
    summary = IngestSummary()

    questions: list[ApiQuestion] = await fetch_questions(start, end)
    db_connection: Connection = await connect()
    try:
        processed_question_ids: set[int] = await get_processed_question_ids(
            db_connection, [question.question_id for question in questions]
        )
        summary.already_processed = len(processed_question_ids)
        remaining_questions: list[ApiQuestion] = [
            question for question in questions if question.question_id not in processed_question_ids
        ]

        summary = await _process_questions(db_connection, remaining_questions, summary)

    finally:
        await db_connection.close()

    logger.info("window %s..%s: %s", start, end, summary)
    return summary


def should_retry(pending: PendingQuestion, current: ApiQuestion) -> bool:
    # External failures may succeed on a new attempt. Synthesis is deterministic, so
    # no_answer and invalid_case are only worth retrying when the thread has new answers.
    return pending.reason in EXTERNAL_REASONS or pending.answer_count < current.answer_count


async def retry_pending(max_attempts: int) -> IngestSummary:
    summary: IngestSummary = IngestSummary()

    db_connection: Connection = await connect()
    try:
        pending_questions: list[PendingQuestion] = await get_pending_questions(db_connection, max_attempts)
        pending_questions_by_id: dict[int, PendingQuestion] = {
            question.question_id: question for question in pending_questions
        }
        api_pending_questions: list[ApiQuestion] = await fetch_questions_by_ids(list(pending_questions_by_id))

        questions_for_reprocessing: list[ApiQuestion] = [
            question
            for question in api_pending_questions
            if should_retry(pending_questions_by_id[question.question_id], question)
        ]

        _log_retry_pending(questions_for_reprocessing, api_pending_questions, pending_questions, max_attempts)
        await _process_questions(db_connection, questions_for_reprocessing, summary)

    finally:
        await db_connection.close()

    return summary


def _log_retry_pending(
    questions_for_reprocessing: list[ApiQuestion],
    api_pending_questions: list[ApiQuestion],
    pending_questions: list[PendingQuestion],
    max_attempts: int,
) -> None:
    selected_ids = {question.question_id for question in questions_for_reprocessing}
    returned_ids = {question.question_id for question in api_pending_questions}
    decisions = Counter(
        "missing from API"
        if pending.question_id not in returned_ids
        else f"retry: {pending.reason}"
        if pending.question_id in selected_ids
        else f"unchanged: {pending.reason}"
        for pending in pending_questions
    )
    logger.info(
        "retry pending: %s pending under %s attempts -> %s",
        len(pending_questions),
        max_attempts,
        dict(decisions),
    )


async def _record(
    db_connection: Connection, question: QuestionWithAnswers, status: IngestStatus, reason: IngestPendingReason | None
) -> None:
    await record_question(
        db_connection, question.question_id, question.creation_date, status, reason, len(question.answers)
    )


async def _process_questions(
    db_connection: Connection, questions: list[ApiQuestion], summary: IngestSummary
) -> IngestSummary:
    remaining_answers: list[ApiAnswer] = await fetch_answers([question.question_id for question in questions])
    cases: list[QuestionWithAnswers] = build_cases(questions, remaining_answers)

    for case in cases:
        question_outcome: QuestionOutcome = await process_question(db_connection, case)
        logger.info("question %s -> %s %s", case.question_id, question_outcome.status, question_outcome.reason or "")

        match question_outcome.status:
            case IngestStatus.INSERTED:
                summary.inserted += 1
            case IngestStatus.SKIPPED:
                summary.skipped += 1
            case IngestStatus.PENDING:
                summary.pending[question_outcome.reason] = summary.pending.get(question_outcome.reason, 0) + 1

    return summary


if __name__ == "__main__":
    import asyncio

    basicConfig(level=INFO)
    getLogger("httpx").setLevel(WARNING)

    async def main():
        summary = await retry_pending(max_attempts=3)
        print(summary)

        connection = await connect()
        try:
            rows = await connection.fetch(
                "SELECT question_id, reason, answer_count, attempt_count FROM ingest_questions "
                "WHERE status = 'pending' ORDER BY question_id"
            )
            for row in rows:
                print(dict(row))
        finally:
            await connection.close()

    asyncio.run(main())
