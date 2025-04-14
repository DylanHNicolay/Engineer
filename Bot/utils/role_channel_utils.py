import discord
import logging

logger = logging.getLogger(__name__)

def is_role_at_top(guild: discord.Guild, role_id: int) -> bool:
    """
    Check if the specified role is at the top position in the guild.
    
    Args:
        guild: The Discord guild to check
        role_id: The ID of the role to check
        
    Returns:
        bool: True if the role is the single highest role, False otherwise
    """
    # Get the role object
    role = guild.get_role(role_id)
    if not role:
        logger.warning(f"Role {role_id} not found in guild {guild.id}")
        return False
    
    # Get all roles with position > 0 (excluding @everyone)
    sorted_roles = sorted([r for r in guild.roles if r.position > 0], 
                          key=lambda r: r.position, reverse=True)
    
    # Check if role is at the top (and the only one at that position)
    if not sorted_roles:
        return False
        
    highest_position = sorted_roles[0].position
    roles_at_top = [r for r in sorted_roles if r.position == highest_position]
    
    # True only if this is the only role at the highest position
    return len(roles_at_top) == 1 and roles_at_top[0].id == role_id

def get_roles_above_engineer(guild: discord.Guild, engineer_role_id: int) -> list:
    """
    Get a list of roles that are positioned above the Engineer role.
    
    Args:
        guild: The Discord guild
        engineer_role_id: The ID of the Engineer role
        
    Returns:
        list: List of role objects that are above the Engineer role
    """
    engineer_role = guild.get_role(engineer_role_id)
    if not engineer_role:
        return []
        
    return [role for role in guild.roles if role.position > engineer_role.position]

async def send_role_position_warning(bot, guild: discord.Guild, engineer_role_id: int, 
                                     channel_id: int = None, dm_admins: bool = True) -> bool:
    """
    Send warning messages about role position.
    
    Args:
        bot: The Discord bot instance
        guild: The Discord guild
        engineer_role_id: The ID of the Engineer role
        channel_id: Optional specific channel ID to send to
        dm_admins: Whether to DM server admins
        
    Returns:
        bool: True if warning was sent successfully, False otherwise
    """
    roles_above = get_roles_above_engineer(guild, engineer_role_id)
    roles_text = ""
    if roles_above:
        roles_text = "\n\nThe following roles are currently above Engineer:\n"
        roles_text += "\n".join([f"- {role.name}" for role in roles_above])
    
    channel_message_sent = False
    dm_message_sent = False
    
    try:
        # If channel_id is not provided, try to get it from the database
        if not channel_id:
            guild_data = await bot.db_interface.get_guild_setup(guild.id)
            if guild_data and guild_data.get('engineer_channel_id'):
                channel_id = guild_data['engineer_channel_id']
            else:
                logger.warning(f"Cannot send role position warning - no engineer channel found for guild {guild.id}")
                return False
        
        # Send warning to the engineer channel
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                await channel.send(
                    "⚠️ **Warning:** The Engineer role is no longer the top role in your server.\n\n"
                    "This can cause functionality issues. Please move the Engineer role back to the top position:\n"
                    "1. Go to Server Settings > Roles\n"
                    "2. Drag the 'Engineer' role to the top of the list\n"
                    "3. Click Save Changes\n\n"
                    "Failing to maintain Engineer as the top role may result in reduced functionality." + roles_text
                )
                logger.info(f"Sent role position warning to channel in guild {guild.id}")
                channel_message_sent = True
            except discord.Forbidden:
                logger.error(f"No permission to send message to engineer channel in guild {guild.id}")
            except Exception as e:
                logger.error(f"Error sending message to engineer channel: {e}")
        else:
            logger.error(f"Engineer channel {channel_id} not found in guild {guild.id}")
        
        # Send DMs to admins if requested
        if dm_admins:
            admin_dm_count = 0
            for member in guild.members:
                # Check if member is an admin (has administrator permission)
                if member.guild_permissions.administrator and not member.bot:
                    try:
                        # Send DM to admin with roles_text included
                        await member.send(
                            f"⚠️ **Important Notice for {guild.name}**\n\n"
                            "The Engineer role is no longer the top role in your server.\n"
                            "This can cause functionality issues with the Engineer bot.\n\n"
                            "Please move the Engineer role back to the top position in your server settings."
                            f"{roles_text}"
                        )
                        admin_dm_count += 1
                        logger.debug(f"Sent DM to admin {member.id} in guild {guild.id}")
                    except discord.Forbidden:
                        # Can't DM this user
                        logger.debug(f"Cannot send DM to admin {member.id} (DMs disabled)")
                    except Exception as e:
                        logger.error(f"Error sending DM to admin {member.id}: {e}")
            
            if admin_dm_count > 0:
                logger.info(f"Sent role position warning DMs to {admin_dm_count} admins in guild {guild.id}")
                dm_message_sent = True
            else:
                logger.warning(f"Found no admins to send DMs to in guild {guild.id}")
        
        # Return True if either channel message or DM was sent
        return channel_message_sent or dm_message_sent
    
    except Exception as e:
        logger.error(f"Error in send_role_position_warning: {e}")
        return False

async def send_role_setup_error(guild: discord.Guild, channel_id: int) -> None:
    """
    Send a detailed setup error message about role position.
    
    Args:
        guild: The Discord guild
        channel_id: The channel ID to send the message to
    """
    try:
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(
                "⚠️ **Setup Error:** Engineer must be the **top level role** in your server.\n\n"
                "1. Go to Server Settings > Roles\n"
                "2. Drag the 'Engineer' role to the top of the list\n"
                "3. Click Save Changes\n"
                "4. Run the `/setup` command again\n\n"
                "This is required to ensure proper permission management."
            )
            logger.info(f"Sent role setup error message to channel in guild {guild.id}")
    except Exception as e:
        logger.error(f"Error sending role setup error message: {e}")

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

async def get_channel_type(db_interface, guild_id: int, channel_id: int) -> str:
    """
    Get the type of a managed channel
    
    Args:
        db_interface: The database interface to use
        guild_id: The Discord guild ID
        channel_id: The channel ID to check
        
    Returns:
        str: The channel type ('engineer', etc.) or 'unknown' if not found
    """
    managed_channels = await get_managed_channels(db_interface, guild_id)
    return next((name for name, id in managed_channels.items() if id == channel_id), "unknown")

# Add utility function for managed roles
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

async def get_role_type(db_interface, guild_id: int, role_id: int) -> str:
    """
    Get the type of a managed role
    
    Args:
        db_interface: The database interface to use
        guild_id: The Discord guild ID
        role_id: The role ID to check
        
    Returns:
        str: The role type ('verified', 'student', etc.) or 'unknown' if not found
    """
    managed_roles = await get_managed_roles(db_interface, guild_id)
    return next((name for name, id in managed_roles.items() if id == role_id), "unknown")