from fastapi import APIRouter

from mechragnic.api.model.ask import AskRequest, AskResponse, TraceStep
from mechragnic.api.service import ask as ask_service

ask_router = APIRouter(prefix="/ask", tags=["ask"])


@ask_router.post("")
async def ask(ask_request: AskRequest) -> AskResponse:
    response: dict
    trace: list[dict]
    response, trace = await ask_service.ask(ask_request.messages)

    return AskResponse(
        answer=response["content"],
        trace=[TraceStep.model_validate(step) for step in trace],
    )
