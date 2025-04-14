import asyncpg
from typing import Optional, Any, List, Dict
import logging
import asyncio
from collections import deque

class DatabaseInterface:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.log = logging.getLogger(__name__)
        # Queue for database operations
        self.operation_queue = deque()
        # Lock to ensure queue operations are thread-safe
        self.queue_lock = asyncio.Lock()
        # Flag for the queue processor
        self.queue_running = False

    async def _process_queue(self):
        """Process operations from the queue sequentially"""
        if self.queue_running:
            return
            
        try:
            self.queue_running = True
            while self.operation_queue:
                # Get the next operation from the queue
                future, operation, args, kwargs = self.operation_queue.popleft()
                
                try:
                    # Execute the operation
                    result = await operation(*args, **kwargs)
                    # Set the result in the future
                    future.set_result(result)
                except Exception as e:
                    # If there's an error, set the exception in the future
                    future.set_exception(e)
        finally:
            self.queue_running = False
            # If new items were added while processing, restart the processor
            if self.operation_queue:
                asyncio.create_task(self._process_queue())

    async def _queue_operation(self, operation, *args, **kwargs):
        """Queue a database operation and return a future for the result"""
        future = asyncio.get_event_loop().create_future()
        
        # Add the operation to the queue
        async with self.queue_lock:
            self.operation_queue.append((future, operation, args, kwargs))
            # Start the queue processor if it's not running
            if not self.queue_running:
                asyncio.create_task(self._process_queue())
                
        # Wait for and return the result
        return await future

    async def _execute_direct(self, query: str, *args) -> str:
        """Execute a SQL query directly without queueing (for internal use)"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    return await conn.execute(query, *args)
        except Exception as e:
            self.log.error(f"Database direct execute error: {e}")
            raise

    async def _fetch_direct(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch results directly without queueing (for internal use)"""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
        except Exception as e:
            self.log.error(f"Database direct fetch error: {e}")
            raise

    async def _fetchrow_direct(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row directly without queueing (for internal use)"""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            self.log.error(f"Database direct fetchrow error: {e}")
            raise

    async def _fetchval_direct(self, query: str, *args) -> Any:
        """Fetch a single value directly without queueing (for internal use)"""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchval(query, *args)
        except Exception as e:
            self.log.error(f"Database direct fetchval error: {e}")
            raise

    async def execute(self, query: str, *args) -> str:
        """Execute a SQL query safely, in order."""
        return await self._queue_operation(self._execute_direct, query, *args)

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch all results from a query, in order."""
        return await self._queue_operation(self._fetch_direct, query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row from a query, in order."""
        return await self._queue_operation(self._fetchrow_direct, query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value from a query, in order."""
        return await self._queue_operation(self._fetchval_direct, query, *args)

    async def execute_transaction(self, operations):
        """Execute multiple operations in a single transaction"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    results = []
                    for query, args in operations:
                        result = await conn.execute(query, *args)
                        results.append(result)
                    return results
        except Exception as e:
            self.log.error(f"Transaction error: {e}")
            raise

    async def safe_transaction(self, operations) -> bool:
        """
        Execute multiple operations in a transaction with error handling
        Returns True if successful, False otherwise
        """
        try:
            await self._queue_operation(self.execute_transaction, operations)
            return True
        except Exception as e:
            self.log.error(f"Safe transaction error: {e}")
            return False

    async def get_guild_setup(self, guild_id: int) -> Optional[asyncpg.Record]:
        """Get guild setup information from the database."""
        return await self.fetchrow('''
            SELECT * FROM guilds WHERE guild_id = $1
        ''', guild_id)
    
    async def remove_guild(self, guild_id: int) -> None:
        """Remove a guild and related records from the database."""
        # Queue these operations to ensure they execute in order
        operations = [
            ('DELETE FROM user_guilds WHERE guild_id = $1', [guild_id]),
            ('DELETE FROM guilds WHERE guild_id = $1', [guild_id])
        ]
        await self.execute_transaction(operations)
        
    async def safe_exit(self, guild_id: int) -> bool:
        """
        Safely removes guild and its associations from the database.
        Returns True if successful, False otherwise.
        """
        operations = [
            ('DELETE FROM user_guilds WHERE guild_id = $1', [guild_id]),
            ('DELETE FROM guilds WHERE guild_id = $1', [guild_id])
        ]
        success = await self.safe_transaction(operations)
        
        if success:
            self.log.info(f"Successfully removed guild {guild_id} and its associations from database")
        
        return success

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
        
    async def complete_setup(self, guild_id: int) -> bool:
        """
        Mark a guild as having completed setup.
        Returns True if successful, False otherwise.
        """
        try:
            await self.execute('''
                UPDATE guilds SET setup = FALSE WHERE guild_id = $1
            ''', guild_id)
            self.log.info(f"Marked guild {guild_id} as setup complete")
            return True
        except Exception as e:
            self.log.error(f"Error marking guild {guild_id} as setup complete: {e}")
            return False
