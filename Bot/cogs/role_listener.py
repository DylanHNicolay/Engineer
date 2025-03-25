import discord
from discord.ext import commands
import logging
from utils.role_utils import is_role_at_top, send_role_position_warning

class RoleListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitored_guilds = {}  # {guild_id: engineer_role_id}
        self.logger = logging.getLogger(__name__)
        
    def add_monitored_guild(self, guild_id: int, role_id: int):
        """Add a guild to be monitored for role position"""
        self.logger.info(f"Adding guild {guild_id} to role position monitoring with role {role_id}")
        self.monitored_guilds[guild_id] = role_id
        
    def remove_monitored_guild(self, guild_id: int):
        """Remove a guild from monitoring"""
        if guild_id in self.monitored_guilds:
            self.logger.info(f"Removing guild {guild_id} from role position monitoring")
            del self.monitored_guilds[guild_id]
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        """Monitor role position changes"""
        guild_id = after.guild.id
        
        # Check if this guild is being monitored
        if guild_id not in self.monitored_guilds:
            return
            
        engineer_role_id = self.monitored_guilds[guild_id]
        
        # If our role was updated and is no longer at the top
        if after.id == engineer_role_id and not is_role_at_top(after.guild, engineer_role_id):
            await send_role_position_warning(self.bot, after.guild, engineer_role_id)
            
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Monitor for new roles that might be placed above Engineer"""
        guild_id = role.guild.id
        
        # Check if this guild is being monitored
        if guild_id not in self.monitored_guilds:
            return
            
        engineer_role_id = self.monitored_guilds[guild_id]
        
        # Check if Engineer is still at the top after new role creation
        if not is_role_at_top(role.guild, engineer_role_id):
            await send_role_position_warning(self.bot, role.guild, engineer_role_id)
        
async def setup(bot):
    await bot.add_cog(RoleListener(bot))
