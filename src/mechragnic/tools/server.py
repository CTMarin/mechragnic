from logging import WARNING, getLogger
from typing import Annotated

from mcp.server import MCPServer
from pydantic import Field

from mechragnic.database import cases
from mechragnic.retrieval import search

getLogger("httpx").setLevel(WARNING)

server = MCPServer(
    name="vehicle-diagnostics",
    instructions="""
        ALWAYS call search_cases before answering any vehicle question — including
        questions you believe you can answer from general knowledge. Cases contain
        real mechanic diagnoses that supersede model priors. Never answer from
        memory alone.
        Vague symptoms ("weird noise", "strange smell") are VALID input — pass the
        user's words verbatim. Do not ask clarifying questions before searching.
        Search first, then use results to ask better follow-ups if needed.
    """,
)

TOP_K = 5


@server.tool()
async def get_case(
    case_id: Annotated[int, Field(description="the id of a case returned by a previous search")],
) -> dict | None:
    """
    Fetch the complete diagnostic case for a known id.

    Call this after search_cases, to expand a case whose id appeared in the results.
    Do not guess ids.

    Returns the full case with symptoms, causes and solution, or None if no case has that id
    """
    return await cases.get_case(case_id)


@server.tool()
async def search_cases(
    query: Annotated[
        str,
        Field(
            description="keyword-style symptom terms described by the user, not the user's full question. For 'my car makes a weird noise when I brake', search 'brake noise grinding'"
        ),
    ],
    # top_k: Annotated[int, Field(ge=1, le=5, description="how many top cases to return")] = 5
) -> list[dict]:
    """
    This tool is for searching diagnosis cases of mechanics, from Stack Exchange.

    ALWAYS call search_cases before answering any vehicle question — including
    questions you believe you can answer from general knowledge. Cases contain
    real mechanic diagnoses that supersede model priors. Never answer from
    memory alone.

    Vague symptoms ("weird noise", "strange smell") are VALID input — pass the
    user's words verbatim. Do not ask clarifying questions before searching.
    Search first, then use results to ask better follow-ups if needed.

    This tool must be called when the user is making a question about mechanics.
    Questions can be for car, motorbikes, or anything that has an engine (petrol, diesel,
    electric, gas, etc...)

    Returns a list of cases, each with symptoms, causes, solution, and a distance, found in
    the database. The distance is how close each result is to the query, less is better.
    """
    return await search.search_cases(query, TOP_K)


if __name__ == "__main__":
    server.run(transport="stdio")
