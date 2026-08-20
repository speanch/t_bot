import asyncpg
import logging

from config import config

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None


async def init_db() -> None:
    global pool
    pool = await asyncpg.create_pool(config.db_url, min_size=1, max_size=5)
    logger.info("Database pool created")

    async with pool.acquire() as conn:
        for table in ("users", "transactions", "generations", "payments"):
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=$1)",
                table,
            )
            if not exists:
                logger.warning("Table '%s' not found. Run migrations.", table)

    logger.info("Database initialized")


async def close_db() -> None:
    global pool
    if pool:
        await pool.close()
        logger.info("Database pool closed")
