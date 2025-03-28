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

    async def get_all_guild_ids(self) -> List[int]:
        """Get all guild IDs from the database."""
        records = await self.fetch('SELECT guild_id FROM guilds')
        return [record['guild_id'] for record in records]

    async def get_all_guilds(self) -> List[asyncpg.Record]:
        """Get all guild records from the database."""
        return await self.fetch('SELECT * FROM guilds')
        
    async def update_guild_channel(self, guild_id: int, channel_id: int) -> None:
        """Update the engineer channel ID for a guild."""
        await self.execute(
            'UPDATE guilds SET engineer_channel_id = $1 WHERE guild_id = $2',
            channel_id, guild_id
        )
        
    async def update_guild_role(self, guild_id: int, role_id: int) -> None:
        """Update the engineer role ID for a guild."""
        await self.execute(
            'UPDATE guilds SET engineer_role_id = $1 WHERE guild_id = $2',
            role_id, guild_id
        )
        
    async def set_guild_setup_required(self, guild_id: int) -> None:
        """Reset a guild to setup mode."""
        await self.execute(
            'UPDATE guilds SET setup = TRUE WHERE guild_id = $1',
            guild_id
        )
