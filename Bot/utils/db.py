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

    async def add_guild(self, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO guilds (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
                guild_id
            )

    async def start_setup_transaction(self, guild_id: int):
        while self.in_use:
            await asyncio.sleep(0.1)
        self.in_use = True
        self._conn = await self.pool.acquire()
        self._tx = self._conn.transaction()
        await self._tx.start()
        self._setup_guild_id = guild_id  # track which guild is in setup

    async def commit_setup_transaction(self):
        if hasattr(self, '_tx'):
            await self._tx.commit()
        await self.pool.release(self._conn)
        self.in_use = False

    async def rollback_setup_transaction(self):
        if hasattr(self, '_tx'):
            await self._tx.rollback()
        await self.pool.release(self._conn)
        self.in_use = False

    async def insert_guild_data(self, guild_id: int, role_id: int, channel_id: int):
        await self._conn.execute(
            "INSERT INTO guilds (guild_id, engineer_role_id, engineer_channel_id)"
            " VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO NOTHING",
            guild_id, role_id, channel_id
        )

    async def update_guild_roles(self, guild_id: int, verified_role_id: int, rpi_staff_role_id: int, student_role_id: int,
                                 alumni_role_id: int, prospective_role_id: int, friend_role_id: int):
        # This expects that a transaction has already started
        await self._conn.execute(
            """
            UPDATE guilds
            SET verified_role_id = $2,
                rpi_admin_role_id = $3,
                student_role_id = $4,
                alumni_role_id = $5,
                prospective_student_role_id = $6,
                friend_role_id = $7
            WHERE guild_id = $1
            """,
            guild_id,
            verified_role_id,
            rpi_staff_role_id,
            student_role_id,
            alumni_role_id,
            prospective_role_id,
            friend_role_id
        )