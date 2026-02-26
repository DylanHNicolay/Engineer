import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db
from utils.setup import _backfill_users

class Backfill(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="Backfill", description="Runs the database backfill process for existing members.")
    async def Backfill(self, interaction: discord.Interaction):
        admin_cog = interaction.client.get_cog("Admin")
        if admin_cog is None or not await admin_cog.is_admin(interaction.user):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)


        try:
            """
            Manually runs the database backfill process for existing members.
            """
            # We need the role objects and the engineer channel to run the backfill
            settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", interaction.guild.id)
            if not settings_records:
                await interaction.followup.send(f"Server settings not found. Please ensure the bot has been set up correctly.")
                
            settings = settings_records[0]
            engineer_channel = interaction.guild.get_channel(settings.get('engineer_channel_id'))
            
            if not engineer_channel:
                await interaction.followup.send(f"Could not find the engineer channel. Please ensure the bot has been set up correctly.")

            # Create a dictionary of the role objects needed by the backfill function
            role_objects = {
                'Student': interaction.guild.get_role(settings.get('student_id')),
                'Alumni': interaction.guild.get_role(settings.get('alumni_id')),
                'Friend': interaction.guild.get_role(settings.get('friend_id')),
                'Verified': interaction.guild.get_role(settings.get('verified_id')),
            }
            
            await _backfill_users(interaction.guild, role_objects, engineer_channel, assign_verified_role=True)
            await interaction.followup.send(f"Backfill process complete. Check the engineer channel for detailed logs.") 
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Backfill(bot))