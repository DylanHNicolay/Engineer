import asyncio
import asyncpg
import os

class Database:
    def __init__(self):
        self._pool = None
        self.queue = asyncio.Queue()

    async def connect(self):
        self._pool = await asyncpg.create_pool(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB"),
            host='db'
        )
        asyncio.create_task(self._worker())

    async def _worker(self):
        while True:
            try:
                future, query, params = await self.queue.get()
                async with self._pool.acquire() as connection:
                    async with connection.transaction():
                        try:
                            result = await connection.fetch(query, *params)
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)
            except Exception as e:
                print(f"Error in DB worker: {e}")
            finally:
                self.queue.task_done()

    async def execute(self, query, *params):
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((future, query, params))
        return await future

    async def close(self):
        await self.queue.join()
        await self._pool.close()

db = Database()
