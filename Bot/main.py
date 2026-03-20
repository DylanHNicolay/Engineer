import os
import sys
import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db
from SetUp.setup import setup_guild

TOKEN = os.getenv("DISCORD_TOKEN")

# Define the intents your bot needs
intents = discord.Intents.all()


class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await db.connect()

        # Load extensions first so their commands are registered
        await self.load_extension("Teams.create-team")
        await self.load_extension("Teams.archive-team")
        await self.load_extension("Teams.list-teams")
        await self.load_extension("Admin.admin")
        await self.load_extension("Dues.set-dues")
        await self.load_extension("Dues.generate")
        await self.load_extension("Webscrape.webscrape")

        # Then sync to the guild
        guild = discord.Object(id=1481037920499400704) # Replace with your specific server's ID
        # self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_guild_join(self, guild: discord.Guild):
        print(f"Joined guild: {guild.name} (ID: {guild.id})")

        settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", guild.id)
        if not settings_records:
            print ("Server settings not found. Setting up server.")
            try:
                await setup_guild(guild=guild)
            except Exception as e:
                print(f"An error occurred during setup: {e}")
            
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})') # type: ignore
        print('------')

        target_guild_id = 1481037920499400704  # Replace with your specific server's ID
        target_guild = discord.utils.get(client.guilds, id=target_guild_id)
        
        if target_guild:
            print(f'Connected to target guild: {target_guild.name} (ID: {target_guild.id})')
            settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", 1483512259144712245)
            if not settings_records:
                print ("Server settings not found. Setting up server.")
                try:
                    await setup_guild(target_guild)
                except Exception as e:
                    print(f"An error occurred during setup: {e}")
            
        else:
            print("Target guild not found.")


client = MyClient(intents=intents)
client.run(TOKEN)  # type: ignore
