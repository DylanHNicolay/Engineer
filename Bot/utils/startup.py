import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class StartupManager:
    """Utility class for managing bot startup operations"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_interface = bot.db_interface

    async def setup_bot(self):
        """
        Perform all necessary setup operations when the bot starts.
        - Validate guilds in database
        - Validate guild memberships and resources
        - Load setup commands for guilds in setup mode
        """
        # Handle guild validation
        await self.validate_guilds()
        
        # Load setup commands
        await self.load_setup_commands()
        
    async def validate_guilds(self):
        """Run guild validation procedures"""
        from utils.guild_validator import GuildValidator
        
        # Create validator and run validations
        validator = GuildValidator(self.bot)
        await validator.validate_guilds_in_database()
        await validator.validate_guild_memberships()
        
    async def load_setup_commands(self):
        """Load setup commands for guilds that are in setup mode"""
        # Always load the role_channel_listener cog first
        try:
            await self.bot.load_extension("cogs.role_channel_listener")
        except commands.ExtensionAlreadyLoaded:
            pass
            
        # Load the setup cog for guilds that are still in setup
        try:
            await self.bot.load_extension("cogs.setup")
        except commands.ExtensionAlreadyLoaded:
            pass
        
        # Get all guilds that are in setup mode
        guilds_in_setup = await self.db_interface.fetch('''
            SELECT guild_id FROM guilds WHERE setup = TRUE
        ''')
        
        # Add setup commands to these guilds
        setup_cog = self.bot.get_cog("Setup")
        if setup_cog:
            for guild_record in guilds_in_setup:
                guild_id = guild_record['guild_id']
                logger.info(f"Re-enabling setup for guild {guild_id} marked as setup=True")
                for command in setup_cog.walk_app_commands():
                    self.bot.tree.add_command(command, guild=discord.Object(id=guild_id))
                
                # Sync the command tree for this guild
                await self.bot.tree.sync(guild=discord.Object(id=guild_id))