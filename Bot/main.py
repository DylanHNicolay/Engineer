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
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await db.connect()
        
        # Load extensions first so their commands are registered
        await self.load_extension("Teams.create-team")
        await self.load_extension("Teams.archive-team")
        await self.load_extension("Teams.list-teams")
        await self.load_extension("Admin.admin")
        await self.load_extension("Dues.set-dues")

        # Then sync to the guild
        guild = discord.Object(id=1281629365939208233)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})') # type: ignore
        print('------')


client = MyClient(intents=intents)
client.run(TOKEN) # type: ignore
