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

    async def get_guild_setup(self, guild_id: int) -> Optional[asyncpg.Record]:
        """Get guild setup information from the database."""
        return await self.fetchrow('''
            SELECT * FROM guilds WHERE guild_id = $1
        ''', guild_id)
    
    async def remove_guild(self, guild_id: int) -> None:
        """Remove a guild and related records from the database."""
        # First, remove any user_guilds entries (due to foreign key constraints)
        await self.execute('''
            DELETE FROM user_guilds WHERE guild_id = $1
        ''', guild_id)
        
        # Then, remove the guild itself
        await self.execute('''
            DELETE FROM guilds WHERE guild_id = $1
        ''', guild_id)
        
    async def safe_exit(self, guild_id: int) -> bool:
        """
        Safely removes guild and its associations from the database.
        Returns True if successful, False otherwise.
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # First, remove any user_guilds entries (due to foreign key constraints)
                    await conn.execute('DELETE FROM user_guilds WHERE guild_id = $1', guild_id)
                    
                    # Then, remove the guild itself
                    await conn.execute('DELETE FROM guilds WHERE guild_id = $1', guild_id)
                    
                    self.log.info(f"Successfully removed guild {guild_id} and its associations from database")
                    return True
        except Exception as e:
            self.log.error(f"Error during safe_exit for guild {guild_id}: {e}")
            return False

    # Guild-specific methods
    async def add_guild_setup(self, guild_id: int, engineer_channel_id: int, engineer_role_id: int = None) -> None:
        """Add a new guild to the database."""
        await self.execute('''
            INSERT INTO guilds (guild_id, engineer_channel_id, engineer_role_id, setup)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id) DO UPDATE
            SET engineer_channel_id = $2, engineer_role_id = $3, setup = $4
        ''', guild_id, engineer_channel_id, engineer_role_id, True)

    async def get_engineer_role_id(self, guild_id: int) -> Optional[int]:
        """Get the engineer role ID for a guild."""
        guild_data = await self.fetchrow('''
            SELECT engineer_role_id FROM guilds WHERE guild_id = $1
        ''', guild_id)
        
        return guild_data['engineer_role_id'] if guild_data else None
