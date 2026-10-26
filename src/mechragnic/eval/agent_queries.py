"""Record the search query the agent writes for each evaluation question.

The agent does not search with the user's question but with a query it writes itself,
usually a few keywords. This asks the model, with the agent's system prompt and tools,
what it would search for, and saves the result so retrieval can be evaluated on the
queries search actually receives. The model is not deterministic, so the queries are
generated once and frozen in agent_queries.json.

Run from the repository root with:

    uv run python -m mechragnic.eval.agent_queries
"""

import asyncio
import json
import logging
from pathlib import Path

from mcp import Client

from mechragnic.agent.client import SERVER_PARAMS, get_tools
from mechragnic.agent.prompts import SYSTEM_PROMPT
from mechragnic.clients.ollama import chat
from mechragnic.eval.run import load_cases

logging.getLogger("httpx").setLevel(logging.WARNING)

QUERIES_FILE = Path(__file__).resolve().parent / "agent_queries.json"


async def first_search_query(question: str, tools: list[dict]) -> str | None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    response = await chat(messages, tools)
    for tool_call in response.get("tool_calls", []):
        call = tool_call["function"]
        if call["name"] == "search_cases":
            return call["arguments"].get("query")
    return None


async def main():
    cases = load_cases()
    queries: dict[str, str] = {}

    async with Client(SERVER_PARAMS) as client:
        tools = await get_tools(client)
        for index, case in enumerate(cases, start=1):
            query = await first_search_query(case.question, tools)
            if query is None:
                # The model answered without searching: fall back to the question itself
                print(f"{index}/{len(cases)} no search, using the question")
                query = case.question
            else:
                print(f"{index}/{len(cases)} {query}")
            queries[case.question] = query

    QUERIES_FILE.write_text(json.dumps(queries, indent=2, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(queries)} queries to {QUERIES_FILE.name}")


if __name__ == "__main__":
    asyncio.run(main())
