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
        bool: True if the role is at the top, False otherwise
    """
    # Get all roles with position > 0 (excluding @everyone)
    sorted_roles = sorted([role for role in guild.roles if role.position > 0], 
                          key=lambda r: r.position, reverse=True)
    
    # Check if role is at the top
    return sorted_roles and sorted_roles[0].id == role_id

async def send_role_position_warning(bot, guild: discord.Guild, engineer_role_id: int, 
                                     channel_id: int = None, dm_admins: bool = True) -> None:
    """
    Send warning messages about role position.
    
    Args:
        bot: The Discord bot instance
        guild: The Discord guild
        engineer_role_id: The ID of the Engineer role
        channel_id: Optional specific channel ID to send to
        dm_admins: Whether to DM server admins
    """
    try:
        # If channel_id is not provided, try to get it from the database
        if not channel_id:
            guild_data = await bot.db_interface.get_guild_setup(guild.id)
            if guild_data and guild_data.get('engineer_channel_id'):
                channel_id = guild_data['engineer_channel_id']
            else:
                logger.warning(f"Cannot send role position warning - no engineer channel found for guild {guild.id}")
                return
        
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
                    "Failing to maintain Engineer as the top role may result in reduced functionality."
                )
                logger.info(f"Sent role position warning to channel in guild {guild.id}")
            except discord.Forbidden:
                logger.error(f"No permission to send message to engineer channel in guild {guild.id}")
            except Exception as e:
                logger.error(f"Error sending message to engineer channel: {e}")
        
        # Send DMs to admins if requested
        if dm_admins:
            admin_dm_count = 0
            for member in guild.members:
                # Check if member is an admin (has administrator permission)
                if member.guild_permissions.administrator and not member.bot:
                    try:
                        # Send DM to admin
                        await member.send(
                            f"⚠️ **Important Notice for {guild.name}**\n\n"
                            "The Engineer role is no longer the top role in your server.\n"
                            "This can cause functionality issues with the Engineer bot.\n\n"
                            "Please move the Engineer role back to the top position in your server settings."
                        )
                        admin_dm_count += 1
                    except discord.Forbidden:
                        # Can't DM this user
                        pass
                    except Exception as e:
                        logger.error(f"Error sending DM to admin {member.id}: {e}")
            
            if admin_dm_count > 0:
                logger.info(f"Sent role position warning DMs to {admin_dm_count} admins in guild {guild.id}")
    
    except Exception as e:
        logger.error(f"Error in send_role_position_warning: {e}")

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