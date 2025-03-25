import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.role_utils import is_role_at_top, send_role_setup_error

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ping", description="Simple ping command")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")
    
    @app_commands.command(name="setup_cancel", description="Cancels setup, deletes the configured channel, and removes the bot from the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def exit_setup(self, interaction: discord.Interaction):
        # Defer response in case this takes a while
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        db = self.bot.db_interface
        
        # Get guild data
        guild_data = await db.get_guild_setup(guild_id)
        
        if guild_data is None:
            await interaction.followup.send("This server is not configured in the database!")
            return
            
        # Get the engineer channel
        engineer_channel_id = guild_data['engineer_channel_id']
        
        # Try to delete the channel
        if engineer_channel_id:
            try:
                channel = interaction.guild.get_channel(engineer_channel_id)
                if channel:
                    await channel.delete(reason="Setup cancelled")
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to delete the engineer channel.")
                return
            except Exception as e:
                await interaction.followup.send(f"Error deleting channel: {e}")
                return
        
        # Use safe_exit to remove guild data from the database
        success = await db.safe_exit(guild_id)
        if not success:
            await interaction.followup.send("Failed to clean up database entries properly.")
            return
        
        await interaction.followup.send("Setup cancelled. I'll be leaving the server now.")
        
        # Wait a short time to ensure the message is sent
        await asyncio.sleep(2)
        
        # Store a reference to the guild before leaving
        guild = interaction.guild
        await guild.leave()

    @app_commands.command(name="setup", description="Begins the setup process")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        # Defer the response while we check things
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        guild = interaction.guild
        db = self.bot.db_interface
        
        # Get guild data to find the engineer role ID
        guild_data = await db.get_guild_setup(guild_id)
        
        if guild_data is None:
            await interaction.followup.send("This server is not configured in the database!")
            return
            
        # Get the engineer role ID
        engineer_role_id = guild_data['engineer_role_id']
        
        if engineer_role_id is None:
            await interaction.followup.send("Engineer role not found in the database. Please reinvite the bot.")
            return
            
        # Get the actual role object
        engineer_role = guild.get_role(engineer_role_id)
        
        if not engineer_role:
            await interaction.followup.send("Engineer role not found in the server. Please reinvite the bot.")
            return
            
        # Check if Engineer role is at the top using the utility function
        if is_role_at_top(guild, engineer_role_id):
            # Engineer is the top role, enable simplified role listener cog
            try:
                # Try to load the role_listener cog if not already loaded
                try:
                    await self.bot.load_extension("cogs.role_listener")
                except commands.ExtensionAlreadyLoaded:
                    pass
                
                # Get the role_listener cog
                role_listener_cog = self.bot.get_cog("RoleListener")
                if role_listener_cog:
                    # Enable monitoring for this guild
                    role_listener_cog.add_monitored_guild(guild_id, engineer_role_id)
                    
                    # Continue with setup
                    await interaction.followup.send("Engineer is the top role. Setup is proceeding.")
                else:
                    await interaction.followup.send("Failed to initialize role monitoring.")
            except Exception as e:
                await interaction.followup.send(f"Error enabling role monitoring: {str(e)}")
        else:
            # Engineer is not the top role
            await interaction.followup.send("Engineer must be the **top level role** in your server. Please move it to the top and try again.")
            
            # If we have a channel_id in the database, send a detailed message there
            if 'engineer_channel_id' in guild_data and guild_data['engineer_channel_id']:
                # Use the utility function to send the setup error message
                await send_role_setup_error(guild, guild_data['engineer_channel_id'])
    
async def setup(bot):
    await bot.add_cog(Setup(bot))
