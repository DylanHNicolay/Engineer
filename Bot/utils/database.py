import asyncpg
from typing import Optional, Any, List, Dict
import logging

class DatabaseInterface:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.log = logging.getLogger(__name__)

    async def execute(self, query: str, *args) -> str:
        """Execute a SQL query safely."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    return await conn.execute(query, *args)
        except Exception as e:
            self.log.error(f"Database execute error: {e}")
            raise

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch all results from a query."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
        except Exception as e:
            self.log.error(f"Database fetch error: {e}")
            raise

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row from a query."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            self.log.error(f"Database fetchrow error: {e}")
            raise

    # Guild-specific methods
    async def add_guild_setup(self, guild_id: int, engineer_channel_id: int) -> None:
        """Add a new guild to the database."""
        await self.execute('''
            INSERT INTO guilds (guild_id, engineer_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET engineer_channel_id = $2
        ''', guild_id, engineer_channel_id)
