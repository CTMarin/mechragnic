from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str


class AskRequest(BaseModel):
    messages: list[ChatMessage]


class TraceStep(BaseModel):
    iteration: int
    tool: str
    arguments: dict[str, Any]
    case_ids: list[int]
    error: str | None = None


class AskResponse(BaseModel):
    answer: str
    trace: list[TraceStep]
