"""
Main bot entry point - engineered for clarity and maintainability
"""

import discord
from discord.ext import commands
import asyncpg
import os
from utils.database import DatabaseInterface
from utils.startup import StartupManager
from utils.guild_setup import GuildSetupManager
import logging

class EngineerBot(commands.Bot):
    """
    Rep Invariant:
    - self.db_interface must be a valid DatabaseInterface instance after setup_hook
    - self.setup_manager must be a valid StartupManager instance after setup_hook
    - self.guild_manager must be a valid GuildSetupManager instance after setup_hook
    - Each guild the bot is in must have a corresponding entry in the guilds database table
    - For guilds in setup mode (setup=True), appropriate setup commands must be registered
    - Engineer role should be the top role in each guild for proper functionality
    - Role hierarchy and permissions are maintained in all guilds
    - The bot must have all required intents to function properly
    - Database connections must be properly maintained and transactions properly handled
    """
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.all(),
        )
        self.initial_extensions = []
        self.db_interface = None
        logging.basicConfig(level=logging.INFO)
        self.setup_manager = None
        self.guild_manager = None
    
    async def setup_hook(self):
        # Database connection
        pool = await asyncpg.create_pool(
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB'),
            host='postgres'
        )
        self.db_interface = DatabaseInterface(pool)
        
        # Initialize managers
        self.setup_manager = StartupManager(self)
        self.guild_manager = GuildSetupManager(self)
        
        # Run startup procedures
        await self.setup_manager.setup_bot()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
    
    async def on_guild_join(self, guild: discord.Guild):
        await self.guild_manager.handle_guild_join(guild)

    async def on_guild_remove(self, guild: discord.Guild):
        await self.guild_manager.handle_guild_remove(guild)

async def main():
    bot = EngineerBot()
    await bot.start(os.getenv('DISCORD_SECRET'))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
