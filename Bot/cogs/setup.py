import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.role_utils import is_role_at_top, send_role_setup_error

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="setup_cancel", description="Cancels setup, deletes the configured channel, and removes the bot from the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def exit_setup(self, interaction: discord.Interaction):
        # Defer response
        await interaction.response.defer()
        
        guild_id = interaction.guild_id
        db = self.bot.db_interface
        
        # Get guild data
        guild_data = await db.get_guild_setup(guild_id)
        
        if guild_data is None:
            await interaction.followup.send("This server is not configured in the database!")
            return
            
        # Get the engineer channel
        engineer_channel_id = guild_data['engineer_channel_id']
        
        # Try to send a message to the engineer channel before deleting it
        if engineer_channel_id:
            try:
                channel = interaction.guild.get_channel(engineer_channel_id)
                if channel:
                    await channel.send("Setup cancelled. I'll be leaving the server now.")
                    await asyncio.sleep(2)  # Give time for the message to be seen
                    await channel.delete(reason="Setup cancelled")
                else:
                    await interaction.followup.send("Engineer channel not found!")
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to delete the engineer channel.")
                return
            except Exception as e:
                await interaction.followup.send(f"Error deleting channel: {e}")
                return
        else:
            await interaction.followup.send("Setup cancelled. I'll be leaving the server now.")
        
        # Use safe_exit to remove guild data from the database
        success = await db.safe_exit(guild_id)
        if not success:
            await interaction.followup.send("Failed to clean up database entries properly.")
            return
        
        # Wait a short time to ensure the message is sent
        await asyncio.sleep(2)
        
        # Store a reference to the guild before leaving
        guild = interaction.guild
        await guild.leave()

    @app_commands.command(name="setup", description="Begins the setup process")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        # Defer the response
        await interaction.response.defer()
        
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

        # Get engineer channel ID
        engineer_channel_id = guild_data.get('engineer_channel_id')
        engineer_channel = None
        
        if engineer_channel_id:
            engineer_channel = guild.get_channel(engineer_channel_id)
            
        if not engineer_channel:
            await interaction.followup.send("Engineer channel not found. Please reinvite the bot.")
            return
            
        # Check if Engineer role is at the top using the utility function
        if is_role_at_top(guild, engineer_role_id):
            # Engineer is the top role, add this guild to the monitored guilds
            role_listener_cog = self.bot.get_cog("RoleChannelListener")
            if role_listener_cog:
                # Enable monitoring for this guild
                role_listener_cog.add_monitored_guild(guild_id, engineer_role_id)
                
                # Mark setup as complete in database
                await db.execute('''
                    UPDATE guilds SET setup = FALSE WHERE guild_id = $1
                ''', guild_id)
                
                # Send message to engineer channel
                await engineer_channel.send("Engineer is the top role. Setup is complete!")
            else:
                await engineer_channel.send("Failed to initialize role monitoring.")
        else:
            # Engineer is not the top role
            await engineer_channel.send("Engineer must be the **top level role** in your server. Please move it to the top and try again.")
            
            # Make sure setup flag is set to true
            await db.execute('''
                UPDATE guilds SET setup = TRUE WHERE guild_id = $1
            ''', guild_id)
            
            # Use the utility function to send the setup error message
            await send_role_setup_error(guild, engineer_channel_id)
    
async def setup(bot):
    await bot.add_cog(Setup(bot))
