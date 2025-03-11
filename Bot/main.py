import os
import discord
from discord import app_commands
from discord.ext import commands
from utils.db import Database

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class MyClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.db_manager = Database()  # Initialize the database manager

    async def setup_hook(self):
        await self.db_manager.connect()  # Connect to the database

        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        await self.tree.sync()  # Sync all slash commands

client = MyClient()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

client.run(os.getenv("DISCORD_SECRET"))