from mechragnic.agent import client
from mechragnic.agent.prompts import SYSTEM_PROMPT
from mechragnic.api.model.ask import ChatMessage


async def ask(messages: list[ChatMessage]) -> tuple[dict, list[dict]]:
    messages_to_ask: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(message.model_dump(mode="json") for message in messages),
    ]

    return await client.ask(messages_to_ask)
