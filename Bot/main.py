import os
import sys
import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db


TOKEN = os.getenv('DISCORD_TOKEN')

# Define the intents your bot needs
intents = discord.Intents.all()

class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix=None, intents=intents)

    async def setup_hook(self):
        await db.connect()
        await self.load_extension("Teams.teams")
        await self.load_extension("Admin.admin")
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})') # type: ignore
        print('------')


client = MyClient(intents=intents)
client.run(TOKEN) # type: ignore
