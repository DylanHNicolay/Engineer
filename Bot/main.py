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
        await self.load_extension("Teams.create_team")
        await self.load_extension("Teams.archive_team")
        await self.load_extension("Teams.list_teams")
        await self.load_extension("Admin.admin")
        await self.load_extension("Admin.set_captain")
        await self.load_extension("Dues.set-dues")
        await self.load_extension("Dues.generate")
        await self.load_extension("Webscrape.webscrape")
        await self.load_extension("Rooms.rooms")
        await self.load_extension("Rooms.reservations")

        await self.load_extension("SetUp.backfill")
        await self.load_extension("year")
                

        
        print("All extensions loaded.")

    async def on_guild_join(self, guild: discord.Guild):
        print(f"Joined guild: {guild.name} (ID: {guild.id})")

        await setup_guild(guild=guild)
            
            
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})') # type: ignore
        print('------')

        for guild in self.guilds:
            print(f'Connected to target guild: {guild.name} (ID: {guild.id})')
            settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", guild.id)

            #Check if server settings exist for this guild, if not run setup
            if not settings_records:
                print ("Server settings not found. Setting up server.")
                try:
                    await setup_guild(guild=guild)
                except Exception as e:
                    print(f"An error occurred during setup: {e}")
            
        #Sync the commands for each guild 
        await self.tree.sync()     
        print("Command tree synced for all guilds.")
            


client = MyClient(intents=intents)
client.run(TOKEN)  # type: ignore
