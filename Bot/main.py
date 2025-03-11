import discord
from discord.ext import commands
import asyncpg
import os
from utils.database import DatabaseInterface
import logging

class EngineerBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.all(),
        )
        self.initial_extensions = [
            'cogs.setup' 
        ]
        self.db_interface = None
        logging.basicConfig(level=logging.INFO)
    
    async def setup_hook(self):
        # Database connection
        pool = await asyncpg.create_pool(
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB'),
            host='postgres'
        )
        self.db_interface = DatabaseInterface(pool)
        
        # Clear all global commands
        self.tree.clear_commands(guild=None)
        
        # Sync the command tree with no commands initially
        await self.tree.sync(guild=None)
        
        # Load extensions
        for ext in self.initial_extensions:
            await self.load_extension(ext)
    
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
    
    async def on_guild_join(self, guild: discord.Guild):
        # Create engineer channel with restricted permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
            guild.owner: discord.PermissionOverwrite(read_messages=True)
        }
        engineer_channel = await guild.create_text_channel('engineer', overwrites=overwrites)
        
        # Add guild to database using the new interface
        await self.db_interface.add_guild_setup(guild.id, engineer_channel.id)
        
        # sync the setup cog for the specific guild
        await self.tree.sync(guild=guild)

async def main():
    bot = EngineerBot()
    await bot.start(os.getenv('DISCORD_SECRET'))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
