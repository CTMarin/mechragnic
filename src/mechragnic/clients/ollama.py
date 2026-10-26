from logging import getLogger

from httpx import AsyncClient

from mechragnic.config.settings import CHAT_MODEL, EMBEDDING_MODEL, OLLAMA_URL

logger = getLogger(__name__)

NUM_CTX = 8192


async def create_embedding(text: str) -> list[float]:
    async with AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": text})
        response.raise_for_status()
        return response.json()["embedding"]


async def chat(messages: list[dict], tools: list[dict]) -> dict:
    async with AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat", json={"model": CHAT_MODEL, "messages": messages, "tools": tools, "stream": False}
        )

        return response.json()["message"]


async def chat_with_format(messages: list[dict], schema: dict) -> str:
    async with AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": messages,
                "format": schema,
                "stream": False,
                "options": {"temperature": 0, "num_ctx": NUM_CTX},
            },
        )

        response.raise_for_status()
        data = response.json()
        if data["prompt_eval_count"] > NUM_CTX * 0.9:
            logger.warning("prompt may have been truncated: %s/%s tokens", data["prompt_eval_count"], NUM_CTX)

        return data["message"]["content"]
