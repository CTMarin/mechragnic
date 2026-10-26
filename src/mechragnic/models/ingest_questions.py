from enum import StrEnum
from typing import NamedTuple

from pydantic import BaseModel, Field


class IngestStatus(StrEnum):
    INSERTED = "inserted"
    SKIPPED = "skipped"
    PENDING = "pending"


class IngestPendingReason(StrEnum):
    NO_ANSWER = "no_answer"
    INVALID_CASE = "invalid_case"
    OLLAMA_ERROR = "ollama_error"
    DB_ERROR = "db_error"


class QuestionOutcome(NamedTuple):
    status: IngestStatus
    reason: IngestPendingReason | None = None


class PendingQuestion(BaseModel):
    question_id: int
    reason: IngestPendingReason
    answer_count: int


class IngestSummary(BaseModel):
    already_processed: int = 0
    inserted: int = 0
    skipped: int = 0
    pending: dict[IngestPendingReason, int] = Field(default_factory=dict)
