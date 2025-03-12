import discord
from discord.ext import commands
from discord import app_commands
import asyncio  # Add this import for the sleep function

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
        
        # Delete guild from the database
        await db.remove_guild(guild_id)
        
        # Wait a short time to ensure the message is sent
        await asyncio.sleep(2)
        
        # Store a reference to the guild before leaving
        guild = interaction.guild

        await guild.leave()

    @app_commands.command(name="setup", description="Begins the setup process")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Setup process initiated. Please follow the instructions.", ephemeral=True)
    
async def setup(bot):
    await bot.add_cog(Setup(bot))
