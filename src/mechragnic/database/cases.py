from asyncpg import Connection

from mechragnic.database.connection import connect
from mechragnic.models.mechanic_case import SynthesizedCase


async def get_case(case_id: int):
    db_connection: Connection = await connect()
    db_response = await db_connection.fetchrow(
        "SELECT id, symptoms, causes, solution FROM mechanic_cases WHERE id = $1", case_id
    )
    await db_connection.close()

    return dict(db_response) if db_response else None


async def get_cases_by_ids_ordered(case_ids: list[int], embedding: list[float]) -> list[dict]:
    db_connection: Connection = await connect()
    db_responses = await db_connection.fetch(
        """
        SELECT id, symptoms, causes, solution, embedding <-> $1::vector AS distance 
        FROM mechanic_cases 
        WHERE id = ANY($2::bigint[])
        ORDER BY array_position($2::bigint[], id)
    """,
        str(embedding),
        case_ids,
    )
    await db_connection.close()

    return [dict(row) for row in db_responses]


async def search_by_embedding(embedding: list[float], top_k: int) -> list[dict]:
    db_connection: Connection = await connect()
    db_responses = await db_connection.fetch(
        """
        SELECT id, symptoms, causes, solution, embedding <-> $1::vector AS distance
        FROM mechanic_cases
        ORDER BY embedding <-> $1::vector
        LIMIT $2
    """,
        str(embedding),
        top_k,
    )

    await db_connection.close()
    return [dict(row) for row in db_responses]


async def search_by_keywords(query: str, limit: int) -> list[int]:
    db_connection: Connection = await connect()
    db_responses = await db_connection.fetch(
        """
        SELECT id
        FROM mechanic_cases, to_tsquery('simple', replace(plainto_tsquery('english', $1)::text, ' & ', ' | '))
        AS keywords
        WHERE search_text @@ keywords
        ORDER BY ts_rank(search_text, keywords) DESC
        LIMIT $2
    """,
        query,
        limit,
    )

    await db_connection.close()
    return [row["id"] for row in db_responses]


async def insert_case(
    db_connection: Connection, question_id: int, case: SynthesizedCase, embedding: list[float]
) -> None:
    await db_connection.execute(
        """
        INSERT INTO mechanic_cases (id, symptoms, causes, solution, embedding)
        VALUES ($1, $2, $3, $4, $5::vector)
        """,
        question_id,
        case.symptoms,
        case.causes,
        case.solution,
        str(embedding),
    )
