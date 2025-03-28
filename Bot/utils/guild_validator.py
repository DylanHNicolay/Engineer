import discord
import logging

logger = logging.getLogger(__name__)

class GuildValidator:
    """Utility class to validate guild memberships and resources"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_interface = bot.db_interface
    
    async def validate_guilds_in_database(self):
        """
        Checks if the bot is in any guilds that are not recorded in the database.
        If found, the bot will leave those guilds.
        """
        logger.info("Checking for guilds not in database...")
        
        # Get all guilds from database using the utility method
        db_guild_ids = set(await self.db_interface.get_all_guild_ids())
        
        # Compare with the guilds the bot is currently in
        for guild in self.bot.guilds:
            if guild.id not in db_guild_ids:
                logger.warning(f"Bot is in guild {guild.id} ({guild.name}) but it's not in the database. Leaving.")
                try:
                    await guild.leave()
                    logger.info(f"Successfully left guild {guild.id} ({guild.name})")
                except Exception as e:
                    logger.error(f"Failed to leave guild {guild.id}: {e}")
    
    async def validate_guild_memberships(self):
        """
        Validates that the bot is still a member of all guilds in the database.
        Also verifies that required channels and roles still exist.
        Cleans up database for guilds where the bot is no longer a member.
        Handles cases where engineer channel or role was deleted while bot was offline.
        """
        logger.info("Validating guild memberships and resources...")
        
        # Get all guilds from database using the utility method
        all_guild_records = await self.db_interface.get_all_guilds()
        
        for guild_record in all_guild_records:
            guild_id = guild_record['guild_id']
            try:
                # Try to fetch the guild
                guild = self.bot.get_guild(guild_id)
                
                # If guild is None, the bot is no longer in the guild
                if guild is None:
                    logger.warning(f"Bot is no longer in guild {guild_id}, cleaning up database entries")
                    await self.db_interface.safe_exit(guild_id)
                    continue
                
                # Bot is in the guild, verify engineer channel exists
                engineer_channel_id = guild_record['engineer_channel_id']
                engineer_role_id = guild_record['engineer_role_id']
                
                channel_exists = False
                role_exists = False
                
                if engineer_channel_id:
                    channel = guild.get_channel(engineer_channel_id)
                    channel_exists = channel is not None
                
                if engineer_role_id:
                    role = guild.get_role(engineer_role_id)
                    role_exists = role is not None
                
                # If resources are missing, handle appropriately
                if not channel_exists or not role_exists:
                    logger.warning(f"Resources missing in guild {guild_id}: channel={channel_exists}, role={role_exists}")
                    
                    # Create a new engineer channel if the original one was deleted
                    if not channel_exists:
                        try:
                            # Create new engineer channel with restricted permissions
                            overwrites = {
                                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                guild.me: discord.PermissionOverwrite(read_messages=True),
                                guild.owner: discord.PermissionOverwrite(read_messages=True)
                            }
                            
                            # Get current engineer role if it exists
                            engineer_role = None
                            if role_exists:
                                engineer_role = guild.get_role(engineer_role_id)
                                overwrites[engineer_role] = discord.PermissionOverwrite(read_messages=True)
                                
                            new_channel = await guild.create_text_channel('engineer', overwrites=overwrites)
                            
                            # Update database with new channel using the utility method
                            await self.db_interface.update_guild_channel(guild_id, new_channel.id)
                            
                            # Send notification about the channel recreation
                            await new_channel.send(
                                "**Engineer Channel Recreation Notice**\n\n"
                                "I detected that the previous engineer channel was deleted while I was offline.\n"
                                "I've created a new channel to continue operations.\n\n"
                                "If you wish to set up the bot again, please use the **/setup** command.\n"
                                "If you want to remove the bot, use the **/setup_cancel** command."
                            )
                            
                            logger.info(f"Created new engineer channel in guild {guild_id}")
                        except Exception as e:
                            logger.error(f"Failed to create new engineer channel in guild {guild_id}: {e}")
                    
                    # If the Engineer role was deleted
                    if not role_exists:
                        # Try to find the bot's highest role
                        bot_member = await guild.fetch_member(self.bot.user.id)
                        highest_role = None
                        
                        if len(bot_member.roles) > 1:  # Skip @everyone
                            highest_role = bot_member.roles[-1]  # Highest role
                        
                        if highest_role:
                            # Update the engineer_role_id in the database using the utility method
                            await self.db_interface.update_guild_role(guild_id, highest_role.id)
                            
                            # Notify in the engineer channel (if it exists now)
                            channel = guild.get_channel(engineer_channel_id) or new_channel if 'new_channel' in locals() else None
                            if channel:
                                await channel.send(
                                    "**Engineer Role Notice**\n\n"
                                    "I detected that the Engineer role was deleted or renamed.\n"
                                    "I've updated my configuration to use my highest role instead.\n\n"
                                    "For optimal functionality, please ensure my role is at the top of the role hierarchy."
                                )
                            
                            logger.info(f"Updated engineer role in guild {guild_id} to {highest_role.id}")
                    
                    # Reset the guild to setup mode using the utility method
                    await self.db_interface.set_guild_setup_required(guild_id)
            
            except Exception as e:
                logger.error(f"Error validating guild {guild_id}: {e}")
        
        logger.info("Guild validation complete")