import discord
from discord.ext import commands
import logging
from utils.role_channel_utils import (
    is_role_at_top, send_role_position_warning, get_managed_channels, 
    is_managed_channel, get_channel_type, get_roles_above_engineer
)
import asyncio
import time

class RoleChannelListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.info("Role channel listener initialized - monitoring all guilds")
        # Add a debounce mechanism to prevent multiple rapid checks
        self.role_check_debounce = {}
        # Debounce time in seconds
        self.debounce_time = 5
        # Track channels that are allowed to be deleted (for setup_cancel)
        self.deletion_allowed = set()
    
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
                
                # Check Engineer role position first
                engineer_role_id = await self.get_engineer_role_id(guild.id)
                if engineer_role_id:
                    await self.check_engineer_role_position(guild, engineer_role_id)
                
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
                if not bot_member:
                    self.logger.warning(f"Bot not found in guild {guild.id}")
                    return
                    
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
                        except discord.Forbidden:
                            self.logger.error(f"No permission to update channel permissions in guild {guild.id}")
                            await self.notify_owner_about_permissions(guild)
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
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Attempting to recreate engineer channel in guild {guild.id}")
            
            # Get the engineer role ID
            engineer_role_id = await self.get_engineer_role_id(guild.id)
            engineer_role = guild.get_role(engineer_role_id) if engineer_role_id else None
            
            # Set up permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.owner: discord.PermissionOverwrite(read_messages=True)
            }
            
            # Add engineer role permissions if it exists
            if engineer_role:
                overwrites[engineer_role] = discord.PermissionOverwrite(read_messages=True)
            
            try:
                # Create a new engineer channel
                new_channel = await guild.create_text_channel('engineer', overwrites=overwrites)
            except discord.Forbidden:
                self.logger.error(f"Bot doesn't have permissions to create channels in guild {guild.id}")
                await self.notify_owner_about_channel_creation(guild)
                return False
            except Exception as e:
                self.logger.error(f"Failed to create engineer channel in guild {guild.id}: {e}")
                return False
                
            # Update the database with the new channel ID
            try:
                await self.bot.db_interface.execute('''
                    UPDATE guilds SET engineer_channel_id = $1 WHERE guild_id = $2
                ''', new_channel.id, guild.id)
            except Exception as e:
                self.logger.error(f"Failed to update database with new channel ID: {e}")
                try:
                    await new_channel.delete(reason="Failed to update database")
                except:
                    pass
                return False
            
            # Send a warning message
            try:
                await new_channel.send(
                    "⚠️ **Notice:** The Engineer channel was missing and has been recreated.\n\n"
                    "This channel is required for proper bot operation. Please do not delete it.\n"
                    "If you want to remove the bot, use `/setup_cancel` instead."
                )
            except Exception as e:
                self.logger.warning(f"Failed to send message in recreated channel: {e}")
                # Not critical, continue
                
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
    
    async def notify_owner_about_permissions(self, guild):
        """Notify the guild owner about permission issues"""
        try:
            await guild.owner.send(
                f"⚠️ **Important Notice for {guild.name}**\n\n"
                "Engineer bot doesn't have permission to manage its channel.\n"
                "Please ensure the bot has 'Manage Channels' and 'Manage Roles' permissions."
            )
            self.logger.info(f"Notified owner about permission issues in guild {guild.id}")
        except:
            self.logger.warning(f"Failed to notify owner about permission issues in guild {guild.id}")
            
    async def notify_owner_about_channel_creation(self, guild):
        """Notify the guild owner about channel creation issues"""
        try:
            await guild.owner.send(
                f"⚠️ **Important Notice for {guild.name}**\n\n"
                "Engineer bot couldn't create its required channel.\n"
                "Please ensure the bot has 'Manage Channels' permissions."
            )
            self.logger.info(f"Notified owner about channel creation issues in guild {guild.id}")
        except:
            self.logger.warning(f"Failed to notify owner about channel creation issues in guild {guild.id}")
    
    async def check_engineer_role_position(self, guild, engineer_role_id, force_warning=False):
        """
        Check if Engineer role is at the top and take appropriate action
        
        Args:
            guild: Discord guild
            engineer_role_id: ID of the Engineer role
            force_warning: If True, send warning regardless of cooldown
        """
        guild_id = guild.id
        
        # Check debounce to prevent multiple rapid checks
        current_time = time.time()
        last_check_time = self.role_check_debounce.get(guild_id, 0)
        
        # If we've checked recently, skip this check
        if not force_warning and current_time - last_check_time < self.debounce_time:
            self.logger.debug(f"Skipping role position check for guild {guild_id} (debounced)")
            return
            
        # Update the debounce timestamp
        self.role_check_debounce[guild_id] = current_time
        
        if not is_role_at_top(guild, engineer_role_id):
            self.logger.warning(f"Engineer role not at top in guild {guild.id}")
            
            # Get engineer channel to send warning
            guild_data = await self.bot.db_interface.get_guild_setup(guild.id)
            if not guild_data or not guild_data.get('engineer_channel_id'):
                self.logger.error(f"No engineer channel found for guild {guild.id}")
                return
                
            channel_id = guild_data['engineer_channel_id']
            
            # Get the current time for recording warning time
            current_db_time = int(time.time())
            
            # Get the roles above for debugging
            roles_above = get_roles_above_engineer(guild, engineer_role_id)
            roles_names = [role.name for role in roles_above]
            self.logger.info(f"Roles above Engineer in guild {guild.id}: {roles_names}")
            
            # Send warning to the engineer channel and admins
            try:
                # Check if channel exists
                channel = guild.get_channel(channel_id)
                if not channel:
                    self.logger.error(f"Engineer channel {channel_id} not found in guild {guild.id}")
                    return
                
                self.logger.info(f"Sending role position warning for guild {guild.id}")
                
                # Send warning
                warning_sent = await send_role_position_warning(self.bot, guild, engineer_role_id, channel_id)
                
                if warning_sent:
                    self.logger.info(f"Successfully sent role position warning for guild {guild.id}")
                    
                    # Update last warning time in database (for record keeping only)
                    try:
                        await self.bot.db_interface.execute(
                            "UPDATE guilds SET last_warning_time = $1 WHERE guild_id = $2",
                            current_db_time, guild.id
                        )
                    except Exception as e:
                        self.logger.error(f"Error updating last warning time for guild {guild.id}: {e}")
                else:
                    self.logger.warning(f"Failed to send warning messages for guild {guild.id}")
                
                # Check if role enforcement has been triggered before
                try:
                    role_triggered = await self.bot.db_interface.fetchval(
                        "SELECT role_enforcement_triggered FROM guilds WHERE guild_id = $1",
                        guild.id
                    )
                    
                    # Set role_enforcement_triggered to True if not already set
                    if not role_triggered:
                        await self.bot.db_interface.execute(
                            "UPDATE guilds SET role_enforcement_triggered = TRUE WHERE guild_id = $1",
                            guild.id
                        )
                        self.logger.info(f"Marked guild {guild.id} as role enforcement triggered in database")
                except Exception as e:
                    self.logger.error(f"Error updating role enforcement status for guild {guild.id}: {e}")
            except Exception as e:
                self.logger.error(f"Error in role position warning for guild {guild.id}: {e}")
    
    async def cleanup_guild(self, guild_id: int):
        """
        Clean up any monitoring or state tracking for a guild that's being removed
        Called before the bot leaves a guild or when setup is canceled
        
        Args:
            guild_id: The Discord guild ID to cleanup
        """
        self.logger.info(f"Cleaning up role and channel monitoring for guild {guild_id}")
        
        try:
            # No need to clean up in-memory state since we're using the database
            # The database records will be removed by safe_exit
            return True
        except Exception as e:
            self.logger.error(f"Error during guild cleanup for {guild_id}: {e}")
            return False
    
    async def allow_channel_deletion(self, channel_id: int, duration: int = 10) -> None:
        """
        Temporarily allow a channel to be deleted without triggering recreation
        
        Args:
            channel_id: The ID of the channel to allow deletion for
            duration: How long (in seconds) to allow deletion
        """
        self.logger.info(f"Allowing deletion of channel {channel_id} for {duration} seconds")
        self.deletion_allowed.add(channel_id)
        
        # Schedule removal of this permission after the duration
        async def remove_permission():
            await asyncio.sleep(duration)
            if channel_id in self.deletion_allowed:
                self.deletion_allowed.remove(channel_id)
                self.logger.debug(f"Deletion permission for channel {channel_id} has expired")
                
        # Start the task to remove the permission later
        asyncio.create_task(remove_permission())
            
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        """Monitor role position changes for all guilds"""
        guild_id = after.guild.id
        
        # Get engineer role ID from database
        engineer_role_id = await self.get_engineer_role_id(guild_id)
        
        # If no engineer role ID found, ignore
        if not engineer_role_id:
            return
            
        # Only check if positions actually changed
        if before.position == after.position:
            return
            
        # Check if our role was updated
        if before.id == engineer_role_id or after.id == engineer_role_id:
            await self.check_engineer_role_position(after.guild, engineer_role_id)
        # Or if any role was moved above Engineer
        else:
            engineer_role = after.guild.get_role(engineer_role_id)
            if engineer_role and after.position > engineer_role.position:
                await self.check_engineer_role_position(after.guild, engineer_role_id)
            
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Monitor for new roles that might be placed above Engineer"""
        guild_id = role.guild.id
        
        # Get engineer role ID from database
        engineer_role_id = await self.get_engineer_role_id(guild_id)
        
        # If no engineer role ID found, ignore
        if not engineer_role_id:
            return
            
        # Check Engineer position after new role creation
        await self.check_engineer_role_position(role.guild, engineer_role_id)
            
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Monitor for deletion of managed channels"""
        guild_id = channel.guild.id
        
        # Check if this is a managed channel
        if await is_managed_channel(self.bot.db_interface, guild_id, channel.id):
            # Check if deletion is explicitly allowed (for setup_cancel)
            if channel.id in self.deletion_allowed:
                self.logger.info(f"Channel {channel.id} deletion was allowed, not recreating")
                # Remove from allowed list immediately to prevent any race conditions
                self.deletion_allowed.remove(channel.id)
                return
                
            self.logger.warning(f"Managed channel {channel.id} was deleted in guild {guild_id}")
            
            # Get which type of managed channel it was
            channel_type = await get_channel_type(self.bot.db_interface, guild_id, channel.id)
            
            if channel_type == "engineer":
                # This was the engineer channel - recreate it
                success = await self.recreate_engineer_channel(channel.guild)
                
                if not success:
                    # Attempt to notify server owner via DM
                    try:
                        owner = channel.guild.owner
                        await owner.send(
                            f"⚠️ **Warning for {channel.guild.name}:**\n\n"
                            "The Engineer channel was deleted, and I was unable to recreate it.\n"
                            "This channel is required for proper bot operation.\n\n"
                            "Please ensure I have the Manage Channels permission and reinvite the bot if needed."
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
        if not bot_member:
            return
            
        # Compare bot permissions before and after
        before_perms = before.permissions_for(bot_member)
        after_perms = after.permissions_for(bot_member)
        
        # Get which type of managed channel it was
        channel_type = await get_channel_type(self.bot.db_interface, guild_id, before.id)
        
        # Check if the bot lost critical permissions
        if before_perms.read_messages and not after_perms.read_messages or \
           before_perms.send_messages and not after_perms.send_messages:
            
            self.logger.warning(f"Bot lost permissions in managed channel {before.id} in guild {guild_id}")
            
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
                
    # Run periodic role position check every 6 hours
    @commands.Cog.listener()
    async def on_ready(self):
        """Schedule periodic role position checks"""
        self.bot.loop.create_task(self.periodic_role_check())
        
    async def periodic_role_check(self):
        """Periodically check all guilds' Engineer role position"""
        await asyncio.sleep(600)  # Initial delay of 10 minutes after bot start
        
        while not self.bot.is_closed():
            self.logger.info("Running periodic role position check")
            
            # Clear the debounce map before doing periodic checks to ensure they run
            self.role_check_debounce.clear()
            
            for guild in self.bot.guilds:
                try:
                    engineer_role_id = await self.get_engineer_role_id(guild.id)
                    if engineer_role_id:
                        await self.check_engineer_role_position(guild, engineer_role_id)
                except Exception as e:
                    self.logger.error(f"Error in periodic role check for guild {guild.id}: {e}")
                    
            # Run every 6 hours
            await asyncio.sleep(6 * 60 * 60)
        
    # Add monitoring for managed roles
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Monitor for deletion of managed roles"""
        guild_id = role.guild.id
        
        # Check if this is a managed role
        if await is_managed_role(self.bot.db_interface, guild_id, role.id):
            self.logger.warning(f"Managed role {role.id} ({role.name}) was deleted in guild {guild_id}")
            
            # Get the role type to check if it's the Engineer role
            role_type = await get_role_type(self.bot.db_interface, guild_id, role.id)
            
            # Special handling for Engineer role deletion - don't try to send messages
            # as the bot will lose access to the guild when its role is deleted
            if role_type == "engineer":
                self.logger.info(f"Engineer role was deleted in guild {guild_id} - bot will be removed from guild")
                # We don't need to send warning or do anything else, as on_guild_remove will handle cleanup
                return
            
            # For other managed roles, send a warning to the engineer channel
            try:
                guild_data = await self.bot.db_interface.get_guild_setup(guild_id)
                if guild_data and guild_data.get('engineer_channel_id'):
                    # Check if the bot is still in the guild and has the required permissions
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        self.logger.warning(f"Cannot send role deletion warning - bot no longer in guild {guild_id}")
                        return
                    
                    # Get the channel and check permissions before trying to send message
                    channel = guild.get_channel(guild_data['engineer_channel_id'])
                    if channel:
                        # Verify that the bot can send messages to this channel
                        bot_member = guild.get_member(self.bot.user.id)
                        if bot_member and channel.permissions_for(bot_member).send_messages:
                            await channel.send(
                                f"⚠️ **Warning:** The managed role **{role.name}** was deleted.\n\n"
                                f"This role is required for proper bot operation. Please run `/setup` again to recreate it."
                            )
                        else:
                            self.logger.warning(f"Bot doesn't have permission to send messages in channel {channel.id} in guild {guild_id}")
                    else:
                        self.logger.warning(f"Engineer channel {guild_data['engineer_channel_id']} not found in guild {guild_id}")
            except Exception as e:
                self.logger.error(f"Error sending warning about deleted role: {e}")
        
async def get_managed_channels(db_interface, guild_id: int) -> dict:
    """
    Get all actively managed channel IDs for a guild
    
    Args:
        db_interface: The database interface to use
        guild_id: The Discord guild ID
        
    Returns:
        dict: {"channel_name": channel_id} mapping of managed channels
    """
    guild_data = await db_interface.get_guild_setup(guild_id)
    
    if not guild_data:
        return {}
        
    managed_channels = {}
    
    # Add engineer channel if it exists
    if guild_data.get('engineer_channel_id'):
        managed_channels['engineer'] = guild_data['engineer_channel_id']
        
    # Could add other managed channels here as they are added to the bot
    
    return managed_channels

# Add a new function to get managed roles
async def get_managed_roles(db_interface, guild_id: int) -> dict:
    """
    Get all actively managed role IDs for a guild
    
    Args:
        db_interface: The database interface to use
        guild_id: The Discord guild ID
        
    Returns:
        dict: {"role_name": role_id} mapping of managed roles
    """
    guild_data = await db_interface.get_guild_setup(guild_id)
    
    if not guild_data:
        return {}
        
    managed_roles = {}
    
    # Add all the managed roles if they exist
    role_mapping = {
        'verified_role_id': 'verified',
        'rpi_admin_role_id': 'rpi_admin',
        'student_role_id': 'student',
        'alumni_role_id': 'alumni',
        'friend_role_id': 'friend',
        'prospective_student_role_id': 'prospective_student',
        'engineer_role_id': 'engineer'
    }
    
    for db_field, role_name in role_mapping.items():
        if guild_data.get(db_field):
            managed_roles[role_name] = guild_data[db_field]
    
    return managed_roles

# Update the is_managed_channel function to use the map
async def is_managed_channel(db_interface, guild_id: int, channel_id: int) -> bool:
    """
    Check if a channel is actively managed by the bot
    
    Args:
        db_interface: The database interface to use
        guild_id: The Discord guild ID
        channel_id: The channel ID to check
        
    Returns:
        bool: True if the channel is managed, False otherwise
    """
    managed_channels = await get_managed_channels(db_interface, guild_id)
    return channel_id in managed_channels.values()

# Add a function to check if a role is managed
async def is_managed_role(db_interface, guild_id: int, role_id: int) -> bool:
    """
    Check if a role is actively managed by the bot
    
    Args:
        db_interface: The database interface to use
        guild_id: The Discord guild ID
        role_id: The role ID to check
        
    Returns:
        bool: True if the role is managed, False otherwise
    """
    managed_roles = await get_managed_roles(db_interface, guild_id)
    return role_id in managed_roles.values()
        
async def setup(bot):
    await bot.add_cog(RoleChannelListener(bot))