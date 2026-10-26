import logging
from asyncio import run

from mechragnic.clients.ollama import create_embedding
from mechragnic.database.connection import connect
from mechragnic.embedding.text import text_for_embedding
from mechragnic.models.mechanic_case import MechanicCase

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def reembed():
    db_connection = await connect()
    try:
        db_response = await db_connection.fetch("SELECT id, symptoms, causes, solution FROM mechanic_cases")

        for index, row in enumerate(db_response, start=1):
            case: MechanicCase = MechanicCase.model_validate(dict(row))
            embedding_text: str = text_for_embedding(case.symptoms, case.causes, case.solution, include_solutions=False)
            embedding = await create_embedding(embedding_text)

            await db_connection.execute(
                """
                    UPDATE mechanic_cases SET embedding_v3 = $1::vector WHERE id = $2
                """,
                str(embedding),
                case.id,
            )
            logger.info("[%s/%s] case %s updated", index, len(db_response), case.id)

    finally:
        await db_connection.close()


run(reembed())
