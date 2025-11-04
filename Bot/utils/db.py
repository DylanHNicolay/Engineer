import asyncio
import asyncpg
import os

class Database:
    def __init__(self):
        self._pool = None
        self.queue = asyncio.Queue()

    async def connect(self):
        retries = 5
        delay = 3
        for i in range(retries):
            try:
                self._pool = await asyncpg.create_pool(
                    user=os.getenv("POSTGRES_USER"),
                    password=os.getenv("POSTGRES_PASSWORD"),
                    database=os.getenv("POSTGRES_DB"),
                    host='db'
                )
                asyncio.create_task(self._worker())
                print("Database connection successful.")
                return
            except (ConnectionRefusedError, asyncpg.exceptions.CannotConnectNowError) as e:
                if i < retries - 1:
                    print(f"Database connection failed. Retrying in {delay} seconds... ({i+1}/{retries})")
                    await asyncio.sleep(delay)
                else:
                    print("Database connection failed after multiple retries.")
                    raise e

    async def _worker(self):
        while True:
            future, query, params = await self.queue.get()
            try:
                if self._pool is None:
                    await asyncio.sleep(0.1) # Wait for pool to be initialized
                    # Re-queue the item if the pool is not ready
                    await self.queue.put((future, query, params))
                    self.queue.task_done()
                    continue

                async with self._pool.acquire() as connection:
                    async with connection.transaction():
                        try:
                            result = await connection.fetch(query, *params)
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)
            except Exception as e:
                print(f"Error in DB worker: {e}")
                if not future.done():
                    future.set_exception(e)
            finally:
                self.queue.task_done()

    async def execute(self, query, *params):
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((future, query, params))
        return await future

    async def close(self):
        await self.queue.join()
        if self._pool:
            await self._pool.close()

db = Database()
