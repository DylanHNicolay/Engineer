import asyncpg
import os
import asyncio  # added import
from typing import Optional

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.in_use = False  # Flag to indicate DB is busy

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'yourpassword'),
            database=os.getenv('POSTGRES_DB', 'engineerbot'),
            host=os.getenv('POSTGRES_HOST', 'postgres')
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def acquire_db(self):
        while self.in_use:
            await asyncio.sleep(0.1)
        self.in_use = True

    async def release_db(self):
        self.in_use = False

    async def add_user(self, discord_id: int):
        await self.acquire_db()
        try:
            await self.pool.execute(
                "INSERT INTO users(discord_id) VALUES($1) ON CONFLICT DO NOTHING",
                discord_id
            )
        finally:
            await self.release_db()

    async def add_guild(self, guild_id: int):
        await self.acquire_db()
        try:
            await self.pool.execute(
                "INSERT INTO guilds(guild_id) VALUES($1) ON CONFLICT DO NOTHING",
                guild_id
            )
        finally:
            await self.release_db()

    async def add_user_guild(self, discord_id: int, guild_id: int):
        await self.acquire_db()
        try:
            await self.pool.execute(
                "INSERT INTO user_guilds(discord_id, guild_id) VALUES($1, $2) ON CONFLICT DO NOTHING",
                discord_id, guild_id
            )
        finally:
            await self.release_db()