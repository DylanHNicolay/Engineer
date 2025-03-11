import discord
from discord.ext import commands
from discord import app_commands

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="setup", description="Initial setup command for the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        # Example of using the database interface
        guild_data = await self.bot.db_interface.get_guild(interaction.guild_id)
        if guild_data:
            await interaction.response.send_message(
                f"Server is already set up! Engineer channel: <#{guild_data['engineer_channel_id']}>",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Setting up server...",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Setup(bot))
