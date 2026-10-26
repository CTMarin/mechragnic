from pydantic import BaseModel


class ApiQuestion(BaseModel):
    question_id: int
    creation_date: int
    title: str
    body: str
    tags: list[str]
    is_answered: bool
    answer_count: int


class QuestionsPage(BaseModel):
    items: list[ApiQuestion]
    has_more: bool
    quota_remaining: int
    backoff: int | None = None


class ApiAnswer(BaseModel):
    answer_id: int
    question_id: int
    body: str
    score: int
    is_accepted: bool


class AnswersPage(BaseModel):
    items: list[ApiAnswer]
    has_more: bool
    quota_remaining: int
    backoff: int | None = None


class QuestionWithAnswers(BaseModel):
    question_id: int
    creation_date: int
    title: str
    body: str
    tags: list[str]
    answers: list[ApiAnswer]
