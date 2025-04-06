import discord
from discord.ext import commands
import logging
from utils.role_channel_utils import (
    is_role_at_top, send_role_position_warning, get_managed_channels, 
    is_managed_channel, get_channel_type
)

class RoleChannelListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.info("Role channel listener initialized - monitoring all guilds")
    
    async def initialize_channel_monitoring(self):
        """
        Initialize channel monitoring for all guilds the bot is in
        Verifies that all managed channels exist and have correct permissions
        Called during bot startup
        """
        self.logger.info("Starting managed channel monitoring initialization")
        
        # Process all guilds the bot is in
        for guild in self.bot.guilds:
            try:
                self.logger.debug(f"Verifying managed channels for guild {guild.id}")
                
                # Get all managed channels for this guild
                managed_channels = await get_managed_channels(self.bot.db_interface, guild.id)
                
                if not managed_channels:
                    self.logger.debug(f"No managed channels found for guild {guild.id}")
                    continue
                    
                # Check each managed channel
                for channel_type, channel_id in managed_channels.items():
                    await self.verify_managed_channel(guild, channel_id, channel_type)
                    
                self.logger.debug(f"Managed channel verification complete for guild {guild.id}")
            except Exception as e:
                self.logger.error(f"Error verifying managed channels for guild {guild.id}: {e}")
                
        self.logger.info("Managed channel monitoring initialization complete")
            
    async def verify_managed_channel(self, guild, channel_id, channel_type):
        """
        Verify that a managed channel exists and has correct permissions
        Attempts to recover the channel if it's missing or fix permissions if needed
        
        Args:
            guild: The Discord guild
            channel_id: The ID of the channel to verify
            channel_type: The type of channel ('engineer', etc.)
        """
        try:
            # Check if channel exists
            channel = guild.get_channel(channel_id)
            
            if not channel:
                self.logger.warning(f"Managed channel {channel_id} ({channel_type}) not found in guild {guild.id}")
                
                # Handle different channel types
                if channel_type == 'engineer':
                    await self.recreate_engineer_channel(guild)
                # Add other channel types here as they're implemented
            else:
                # Channel exists, verify permissions
                bot_member = guild.get_member(self.bot.user.id)
                channel_perms = channel.permissions_for(bot_member)
                
                # Check if bot has required permissions
                if not (channel_perms.read_messages and channel_perms.send_messages):
                    self.logger.warning(f"Bot missing permissions in channel {channel_id} in guild {guild.id}")
                    
                    # Try to fix permissions
                    if channel_type == 'engineer':
                        try:
                            await channel.set_permissions(bot_member, read_messages=True, send_messages=True,
                                                        reason="Restoring required bot permissions")
                            self.logger.info(f"Restored permissions in {channel_type} channel in guild {guild.id}")
                        except Exception as e:
                            self.logger.error(f"Failed to restore permissions: {e}")
                
                # For Engineer channel, ensure it has the correct name
                if channel_type == 'engineer' and channel.name != 'engineer':
                    self.logger.warning(f"Engineer channel has wrong name in guild {guild.id}: {channel.name}")
                    try:
                        await channel.edit(name="engineer", reason="Restoring required channel name")
                        self.logger.info(f"Restored engineer channel name in guild {guild.id}")
                    except Exception as e:
                        self.logger.error(f"Failed to restore engineer channel name: {e}")
        
        except Exception as e:
            self.logger.error(f"Error verifying channel {channel_id} in guild {guild.id}: {e}")
    
    async def recreate_engineer_channel(self, guild):
        """
        Recreate the engineer channel in a guild
        
        Args:
            guild: The Discord guild
        """
        try:
            self.logger.info(f"Attempting to recreate engineer channel in guild {guild.id}")
            
            # Get the engineer role ID
            engineer_role_id = await self.get_engineer_role_id(guild.id)
            engineer_role = guild.get_role(engineer_role_id) if engineer_role_id else None
            
            # Set up permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                guild.owner: discord.PermissionOverwrite(read_messages=True)
            }
            
            # Add engineer role permissions if it exists
            if engineer_role:
                overwrites[engineer_role] = discord.PermissionOverwrite(read_messages=True)
                
            # Create a new engineer channel
            new_channel = await guild.create_text_channel('engineer', overwrites=overwrites)
            
            # Update the database with the new channel ID
            await self.bot.db_interface.execute('''
                UPDATE guilds SET engineer_channel_id = $1 WHERE guild_id = $2
            ''', new_channel.id, guild.id)
            
            # Send a warning message
            await new_channel.send(
                "⚠️ **Notice:** The Engineer channel was missing and has been recreated.\n\n"
                "This channel is required for proper bot operation. Please do not delete it.\n"
                "If you want to remove the bot, use `/setup_cancel` instead."
            )
            
            self.logger.info(f"Successfully recreated engineer channel in guild {guild.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to recreate engineer channel in guild {guild.id}: {e}")
            return False

    async def get_engineer_role_id(self, guild_id: int) -> int:
        """Get the engineer role ID from the database for the specified guild"""
        guild_data = await self.bot.db_interface.get_guild_setup(guild_id)
        
        if guild_data and guild_data.get('engineer_role_id'):
            return guild_data['engineer_role_id']
        return None
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        """Monitor role position changes for all guilds"""
        guild_id = after.guild.id
        
        # Get engineer role ID from database
        engineer_role_id = await self.get_engineer_role_id(guild_id)
        
        # If no engineer role ID found or this isn't the engineer role, ignore
        if not engineer_role_id or after.id != engineer_role_id:
            return
            
        # If our role was updated and is no longer at the top
        if not is_role_at_top(after.guild, engineer_role_id):
            self.logger.warning(f"Engineer role no longer at top in guild {guild_id}")
            await send_role_position_warning(self.bot, after.guild, engineer_role_id)
            
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Monitor for new roles that might be placed above Engineer"""
        guild_id = role.guild.id
        
        # Get engineer role ID from database
        engineer_role_id = await self.get_engineer_role_id(guild_id)
        
        # If no engineer role ID found, ignore
        if not engineer_role_id:
            return
            
        # Check if Engineer is still at the top after new role creation
        if not is_role_at_top(role.guild, engineer_role_id):
            self.logger.warning(f"Engineer role no longer at top after role creation in guild {guild_id}")
            await send_role_position_warning(self.bot, role.guild, engineer_role_id)
            
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Monitor for deletion of managed channels"""
        guild_id = channel.guild.id
        
        # Check if this is a managed channel
        if await is_managed_channel(self.bot.db_interface, guild_id, channel.id):
            self.logger.warning(f"Managed channel {channel.id} was deleted in guild {guild_id}")
            
            # Get which type of managed channel it was
            channel_type = await get_channel_type(self.bot.db_interface, guild_id, channel.id)
            
            if channel_type == "engineer":
                # This was the engineer channel - recreate it
                try:
                    # Get the engineer role ID
                    engineer_role_id = await self.get_engineer_role_id(guild_id)
                    engineer_role = channel.guild.get_role(engineer_role_id) if engineer_role_id else None
                    
                    # Set up permissions
                    overwrites = {
                        channel.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        channel.guild.me: discord.PermissionOverwrite(read_messages=True),
                        channel.guild.owner: discord.PermissionOverwrite(read_messages=True)
                    }
                    
                    # Add engineer role permissions if it exists
                    if engineer_role:
                        overwrites[engineer_role] = discord.PermissionOverwrite(read_messages=True)
                        
                    # Create a new engineer channel
                    new_channel = await channel.guild.create_text_channel('engineer', overwrites=overwrites)
                    
                    # Update the database with the new channel ID
                    await self.bot.db_interface.execute('''
                        UPDATE guilds SET engineer_channel_id = $1 WHERE guild_id = $2
                    ''', new_channel.id, guild_id)
                    
                    # Send a warning message
                    await new_channel.send(
                        "⚠️ **Warning:** The Engineer channel was deleted and has been recreated.\n\n"
                        "This channel is required for proper bot operation. Please do not delete it.\n"
                        "If you want to remove the bot, use `/setup_cancel` instead."
                    )
                    
                    self.logger.info(f"Recreated engineer channel in guild {guild_id}")
                except Exception as e:
                    self.logger.error(f"Failed to recreate engineer channel in guild {guild_id}: {e}")
                    # Attempt to notify server owner via DM
                    try:
                        owner = channel.guild.owner
                        await owner.send(
                            f"⚠️ **Warning for {channel.guild.name}:**\n\n"
                            "The Engineer channel was deleted, and I was unable to recreate it.\n"
                            "This channel is required for proper bot operation.\n\n"
                            "Please reinvite the bot or contact support."
                        )
                    except:
                        pass
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        """Monitor for changes to managed channels"""
        guild_id = before.guild.id
        
        # Check if this is a managed channel
        if not await is_managed_channel(self.bot.db_interface, guild_id, before.id):
            return
            
        # Check for permission changes that would affect the bot
        bot_member = before.guild.get_member(self.bot.user.id)
        
        # Compare bot permissions before and after
        before_perms = before.permissions_for(bot_member)
        after_perms = after.permissions_for(bot_member)
        
        # Check if the bot lost critical permissions
        if before_perms.read_messages and not after_perms.read_messages or \
           before_perms.send_messages and not after_perms.send_messages:
            
            self.logger.warning(f"Bot lost permissions in managed channel {before.id} in guild {guild_id}")
            
            # Get which type of managed channel it was
            channel_type = await get_channel_type(self.bot.db_interface, guild_id, before.id)
            
            if channel_type == "engineer":
                # Try to notify server owner via DM about the issue
                try:
                    owner = before.guild.owner
                    await owner.send(
                        f"⚠️ **Warning for {before.guild.name}:**\n\n"
                        "The Engineer channel permissions were modified, and I no longer have proper access.\n"
                        "This can prevent proper bot operation.\n\n"
                        "Please restore my permissions to view and send messages in the Engineer channel."
                    )
                    self.logger.info(f"Notified owner about permission changes in guild {guild_id}")
                except Exception as e:
                    self.logger.error(f"Failed to notify owner about permission changes in guild {guild_id}: {e}")
                    
                # Also try to fix the permissions if we can
                try:
                    # Update permissions for the bot
                    await after.set_permissions(bot_member, read_messages=True, send_messages=True,
                                              reason="Restoring required bot permissions")
                    self.logger.info(f"Restored permissions in engineer channel in guild {guild_id}")
                except:
                    pass
                    
        # Check if the channel was renamed from 'engineer'
        if channel_type == "engineer" and before.name == "engineer" and after.name != "engineer":
            self.logger.warning(f"Engineer channel was renamed in guild {guild_id}")
            
            try:
                # Rename it back to 'engineer'
                await after.edit(name="engineer", reason="Restoring required channel name")
                
                # Send a warning message
                await after.send(
                    "⚠️ **Notice:** The Engineer channel must be named 'engineer' for proper bot operation.\n"
                    "I've restored the original name."
                )
                self.logger.info(f"Restored engineer channel name in guild {guild_id}")
            except Exception as e:
                self.logger.error(f"Failed to restore engineer channel name in guild {guild_id}: {e}")

    """
    TODO
    - As we add more features, we can remove the cogs/other functionality if a role is moved.
    """
        
async def setup(bot):
    await bot.add_cog(RoleChannelListener(bot))