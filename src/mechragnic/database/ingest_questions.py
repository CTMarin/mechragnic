from asyncpg import Connection
from asyncpg.protocol.record import Record

from mechragnic.models.ingest_questions import IngestPendingReason, IngestStatus, PendingQuestion


async def get_processed_question_ids(db_connection: Connection, question_ids: list[int]) -> set[int]:
    db_result: list[Record] = await db_connection.fetch(
        "SELECT question_id FROM ingest_questions WHERE question_id = ANY($1::bigint[])", question_ids
    )

    return {row["question_id"] for row in db_result}


async def record_question(
    db_connection: Connection,
    question_id: int,
    creation_date: int,
    status: IngestStatus,
    reason: IngestPendingReason | None,
    answer_count: int,
) -> None:
    await db_connection.execute(
        """
        INSERT INTO ingest_questions (question_id, creation_date, status, reason, answer_count) 
        VALUES ($1, $2, $3, $4, $5) 
        ON CONFLICT (question_id) DO UPDATE 
        SET status = EXCLUDED.status, 
            reason = EXCLUDED.reason, 
            answer_count = EXCLUDED.answer_count,
            attempt_count = ingest_questions.attempt_count + 1,
            last_checked_at = NOW()
        """,
        question_id,
        creation_date,
        status,
        reason,
        answer_count,
    )


async def get_pending_questions(db_connection: Connection, max_attempts: int) -> list[PendingQuestion]:
    rows: list[Record] = await db_connection.fetch(
        """
         SELECT question_id, reason, answer_count 
         FROM ingest_questions 
         WHERE status = $1 AND attempt_count < $2
        """,
        IngestStatus.PENDING,
        max_attempts,
    )

    return [PendingQuestion.model_validate(dict(row)) for row in rows]
