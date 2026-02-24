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
        
<<<<<<< HEAD
        # Load extensions first so their commands are registered
        await self.load_extension("Teams.create-team")
        await self.load_extension("Teams.archive-team")
        await self.load_extension("Teams.list-teams")
        await self.load_extension("Admin.admin")
        await self.load_extension("Dues.set-dues")
        await self.load_extension("Dues.generate")

        # Then sync to the guild
        guild = discord.Object(id=1281629365939208233)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
=======
        # Load the setup cog for guilds that are still in setup
        try:
            await self.load_extension("cogs.setup")
        except commands.ExtensionAlreadyLoaded:
            pass
        
        # Load the role_channel_listener cog for all guilds
        try:
            await self.load_extension("cogs.role_channel_listener")
            logging.info("Role channel listener cog loaded successfully")
        except commands.ExtensionAlreadyLoaded:
            logging.info("Role channel listener cog was already loaded")
        except Exception as e:
            logging.error(f"Failed to load role_channel_listener cog: {e}")

        # Load the verification cog for guilds that are not in setup
        try:
            guilds_not_in_setup = await self.db_interface.fetch('''
                SELECT guild_id FROM guilds WHERE setup = FALSE
            ''')
            if guilds_not_in_setup:
                await self.load_extension("cogs.verification")
                logging.info("Verification cog loaded successfully")
        except commands.ExtensionAlreadyLoaded:
            logging.info("Verification cog was already loaded")
        except Exception as e:
            logging.error(f"Failed to load verification cog: {e}")
            
        # Initialize channel monitoring for all guilds
        role_channel_listener = self.get_cog("RoleChannelListener")
        if role_channel_listener:
            logging.info("Starting managed channel verification...")
            try:
                await role_channel_listener.initialize_channel_monitoring()
                logging.info("Managed channel verification complete")
            except Exception as e:
                logging.error(f"Error during managed channel verification: {e}")
        else:
            logging.warning("Could not initialize channel monitoring: RoleChannelListener cog not found")
        
        # Get all guilds that are in setup mode
        guilds_in_setup = await self.db_interface.fetch('''
            SELECT guild_id FROM guilds WHERE setup = TRUE
        ''')
        
        # Add setup commands to these guilds
        setup_cog = self.get_cog("Setup")
        if setup_cog:
            for guild_record in guilds_in_setup:
                guild_id = guild_record['guild_id']
                logging.info(f"Re-enabling setup for guild {guild_id} marked as setup=True")
                for command in setup_cog.walk_app_commands():
                    self.tree.add_command(command, guild=discord.Object(id=guild_id))
                
                # Sync the command tree for this guild
                await self.tree.sync(guild=discord.Object(id=guild_id))
>>>>>>> 4acfd9b (Verification Feature Reintegrate)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})') # type: ignore
        print('------')


client = MyClient(intents=intents)
client.run(TOKEN) # type: ignore
