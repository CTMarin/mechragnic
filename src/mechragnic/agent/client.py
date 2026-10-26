import json
import logging
from pathlib import Path

from mcp import Client, StdioServerParameters

from mechragnic.clients.ollama import chat

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parents[3]
SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=["--directory", str(PROJECT_DIR), "run", "python", "-m", "mechragnic.tools.server"],
)
MAX_ITERATIONS = 10


async def get_tools(client) -> list[dict]:
    tools = await client.list_tools()
    return [
        {
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema},
        }
        for tool in tools.tools
    ]


async def ask(messages: list[dict]) -> tuple[dict, list[dict]]:
    async with Client(SERVER_PARAMS) as client:
        tools = await get_tools(client)
        response = await chat(messages, tools)

        trace = []
        iteration = 0
        while "tool_calls" in response and iteration < MAX_ITERATIONS:
            messages.append(response)

            for tool_call in response["tool_calls"]:
                call = tool_call["function"]
                result = await client.call_tool(call["name"], call["arguments"])

                if result.is_error:
                    detail = result.content[0].text if result.content else "unknown error"
                    error = f"The tool failed: {detail}"
                    content = error
                    case_ids = []
                else:
                    error = None
                    cases = result.structured_content["result"]
                    content = json.dumps(cases)
                    case_ids = [case["id"] for case in cases]
                step = {
                    "iteration": iteration,
                    "tool": call["name"],
                    "arguments": call["arguments"],
                    "case_ids": case_ids,
                    "error": error,
                }
                trace.append(step)
                logger.info("step %s", step)

                messages.append({"role": "tool", "content": content})

            response = await chat(messages, tools)
            iteration += 1

        if "tool_calls" in response:
            messages.append(
                {
                    "role": "system",
                    "content": "You have reached the maximum number of searches. Answer now with the cases you already retrieved, and tell the user your answer may be incomplete.",
                }
            )
            response = await chat(messages, [])

        return response, trace
