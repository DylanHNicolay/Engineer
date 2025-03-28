import discord
import logging

logger = logging.getLogger(__name__)

class GuildSetupManager:
    """Utility class for managing guild setup and removal operations"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_interface = bot.db_interface

    async def handle_guild_join(self, guild: discord.Guild):
        """
        Handle when the bot joins a new guild.
        Creates engineer channel, finds engineer role, and sets up the guild.
        """
        try:
            # Check if the bot still has access to the guild
            try:
                await guild.fetch_member(self.bot.user.id)
            except discord.errors.Forbidden:
                logger.error(f"Bot doesn't have permissions in guild {guild.id}")
                return
            except discord.errors.NotFound:
                logger.error(f"Bot is no longer in guild {guild.id}")
                return

            # Create engineer channel with restricted permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                guild.owner: discord.PermissionOverwrite(read_messages=True)
            }
            
            try:
                engineer_channel = await guild.create_text_channel('engineer', overwrites=overwrites)
            except discord.errors.Forbidden:
                logger.error(f"Bot doesn't have permissions to create channels in guild {guild.id}")
                return
            except Exception as e:
                logger.error(f"Failed to create engineer channel in guild {guild.id}: {e}")
                return

            # Verify the channel was created and is accessible
            try:
                # Try to fetch the channel to make sure it exists
                engineer_channel = await guild.fetch_channel(engineer_channel.id)
            except discord.errors.NotFound:
                logger.error(f"Created channel not found in guild {guild.id}")
                await self.db_interface.safe_exit(guild.id)
                return
            except discord.errors.Forbidden:
                logger.error(f"Bot can't access created channel in guild {guild.id}")
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
            self.bot.tree.clear_commands(guild=discord.Object(id=guild.id))
            
            # Add guild to database using the new interface
            await self.db_interface.add_guild_setup(guild.id, engineer_channel.id, engineer_role_id)
            
            # Ensure the Setup cog and relevant commands are loaded
            # Only newly joined guilds can have access to the setup cog
            try:
                await self.bot.load_extension("cogs.setup")
            except discord.ext.commands.ExtensionAlreadyLoaded:
                pass
            
            setup_cog = self.bot.get_cog("Setup")
            for command in setup_cog.walk_app_commands():
                self.bot.tree.add_command(command, guild=discord.Object(id=guild.id))
            
            await self.bot.tree.sync(guild=discord.Object(id=guild.id))
            
            await self.send_welcome_message(engineer_channel, guild)
                
            logger.info(f"Successfully set up bot in guild {guild.id}")
            
        except Exception as e:
            logger.error(f"Error during guild join setup: {e}")
            # Try to clean up if something went wrong
            await self.db_interface.safe_exit(guild.id)
            try:
                await guild.leave()
            except:
                pass

    async def send_welcome_message(self, channel, guild):
        """Send the welcome message to a new guild"""
        try:
            await channel.send(
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
            logger.error(f"Channel disappeared before sending welcome message in guild {guild.id}")
            await self.db_interface.safe_exit(guild.id)
            raise
        except discord.errors.Forbidden:
            logger.error(f"Bot doesn't have permissions to send messages in guild {guild.id}")
            await self.db_interface.safe_exit(guild.id)
            raise
        except Exception as e:
            logger.error(f"Failed to send welcome message in guild {guild.id}: {e}")
            await self.db_interface.safe_exit(guild.id)
            raise

    async def handle_guild_remove(self, guild: discord.Guild):
        """
        Called when the bot is removed from a guild.
        Clean up database entries related to this guild.
        """
        logger.info(f"Bot was removed from guild {guild.id} ({guild.name})")
        
        # Use safe_exit to remove guild data from database
        success = await self.db_interface.safe_exit(guild.id)
        if success:
            logger.info(f"Successfully cleaned up database entries for guild {guild.id}")
        else:
            logger.error(f"Failed to clean up database entries for guild {guild.id}")