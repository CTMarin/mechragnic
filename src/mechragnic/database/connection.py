import asyncpg

from mechragnic.config.settings import DATABASE_URL


async def connect() -> asyncpg.Connection:
    return await asyncpg.connect(DATABASE_URL)
