import discord
from discord.ext import commands
import logging
from utils.role_channel_utils import is_role_at_top, send_role_position_warning

class RoleChannelListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.info("Role channel listener initialized - monitoring all guilds")
    
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

    """
    TODO
    - As we add more features, we can remove the cogs/other functionality if a role is moved.
    """
        
async def setup(bot):
    await bot.add_cog(RoleChannelListener(bot))