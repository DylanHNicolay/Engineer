"""
Bot entry point - initializes the EngineerBot and manages cog loading
"""

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
        self.initial_extensions = []
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

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
    
    async def on_guild_join(self, guild: discord.Guild):
        """
        Handles the bot joining a new guild
        - Creates an engineer channel
        - Sets up database entries
        - Loads the setup command
        """
        try:
            # Check if the bot still has access to the guild
            try:
                await guild.fetch_member(self.user.id)
            except discord.errors.Forbidden:
                logging.error(f"Bot doesn't have permissions in guild {guild.id}")
                return
            except discord.errors.NotFound:
                logging.error(f"Bot is no longer in guild {guild.id}")
                return

            # Create engineer channel with restricted permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.owner: discord.PermissionOverwrite(read_messages=True)
            }
            
            try:
                engineer_channel = await guild.create_text_channel('engineer', overwrites=overwrites)
            except discord.errors.Forbidden:
                logging.error(f"Bot doesn't have permissions to create channels in guild {guild.id}")
                return
            except Exception as e:
                logging.error(f"Failed to create engineer channel in guild {guild.id}: {e}")
                return

            # Verify the channel was created and is accessible
            try:
                # Try to fetch the channel to make sure it exists
                engineer_channel = await guild.fetch_channel(engineer_channel.id)
            except discord.errors.NotFound:
                logging.error(f"Created channel not found in guild {guild.id}")
                await self.db_interface.safe_exit(guild.id)
                return
            except discord.errors.Forbidden:
                logging.error(f"Bot can't access created channel in guild {guild.id}")
                await self.db_interface.safe_exit(guild.id)
                return

            # Find the bot's "Engineer" role
            engineer_role_id = None
            for role in guild.me.roles:
                if role.name == "Engineer":
                    engineer_role_id = role.id
                    break
            
            # If not found, fallback to the bot's highest role (excluding @everyone)
            if engineer_role_id is None and len(guild.me.roles) > 1:
                engineer_role_id = guild.me.roles[-1].id  # The bot's highest role

            # Clear the command tree on join
            self.tree.clear_commands(guild=discord.Object(id=guild.id))
            
            # Add guild to database using the new interface
            await self.db_interface.add_guild_setup(guild.id, engineer_channel.id, engineer_role_id)
            
            # Ensure the Setup cog and relevant commands are loaded
            # Only newly joined guilds can have access to the setup cog
            try:
                await self.load_extension("cogs.setup")
            except commands.ExtensionAlreadyLoaded:
                pass
            
            setup_cog = self.get_cog("Setup")
            for command in setup_cog.walk_app_commands():
                self.tree.add_command(command, guild=discord.Object(id=guild.id))
            
            await self.tree.sync(guild=discord.Object(id=guild.id))
            
            # Send a message in the engineer channel with setup instructions
            try:
                await engineer_channel.send(
                    "**Thank you for choosing Engineer!**\n\n"
                    ":warning: **Please read the following information carefully before proceeding.** :warning:\n"
                    "* Before begining setup, ensure Engineer is **the top level role**.\n"
                    "* To cancel the setup, use the **/setup_cancel** command.The bot will delete this channel and leave the server.\n"
                    "* To begin setup, use the **/setup** command.\n\n"
                    ":warning: **Data** will be **collected** on users including their :warning:\n"
                    "* **Discord ID**\n* **Relationship with RPI**\n* **Relationship with the club/community**.\n\n"
                    "This data will be used to provide a better experience for users, including \n* **Protecting against spam and harassment**\n* **Seamless integration with other RPI communities**\n* **Allowing for more personalized experiences**\n\n"
                    "You may begin the setup at any time, but it is important that **users are informed** about Engineer. We recommend waiting at least 7 - 31 days after notifying your users before setting up this bot depending on your server size. Some individuals are uncomfortable with data collection, and it is important to respect their privacy.\n\n"
                    "This project is open source and its source code can be found at https://github.com/DylanHNicolay/Engineer\n"
                    "If you have any questions or concerns, please reach out to the developer, Dylan Nicolay through Discord: **nico1ax**\n"
                )
            except discord.errors.NotFound:
                logging.error(f"Channel disappeared before sending welcome message in guild {guild.id}")
                await self.db_interface.safe_exit(guild.id)
                return
            except discord.errors.Forbidden:
                logging.error(f"Bot doesn't have permissions to send messages in guild {guild.id}")
                await self.db_interface.safe_exit(guild.id)
                return
            except Exception as e:
                logging.error(f"Failed to send welcome message in guild {guild.id}: {e}")
                await self.db_interface.safe_exit(guild.id)
                return
                
            logging.info(f"Successfully set up bot in guild {guild.id}")
            
        except Exception as e:
            logging.error(f"Error during guild join setup: {e}")
            # Try to clean up if something went wrong
            await self.db_interface.safe_exit(guild.id)
            try:
                await guild.leave()
            except:
                pass

    async def on_guild_remove(self, guild: discord.Guild):
        """
        Called when the bot is removed from a guild.
        Clean up database entries related to this guild.
        """
        logging.info(f"Bot was removed from guild {guild.id} ({guild.name})")
        
        # Use safe_exit to remove guild data from database
        success = await self.db_interface.safe_exit(guild.id)
        if success:
            logging.info(f"Successfully cleaned up database entries for guild {guild.id}")
        else:
            logging.error(f"Failed to clean up database entries for guild {guild.id}")

async def main():
    bot = EngineerBot()
    await bot.start(os.getenv('DISCORD_SECRET'))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
