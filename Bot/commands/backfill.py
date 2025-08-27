import discord
from discord import app_commands
from utils.db import db
from utils.setup import _backfill_users

async def backfill_command_logic(interaction: discord.Interaction):
    """
    Manually runs the database backfill process for existing members.
    """
    # We need the role objects and the engineer channel to run the backfill
    settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", interaction.guild.id)
    if not settings_records:
        return "Server settings not found. Please ensure the bot has been set up correctly."
        
    settings = settings_records[0]
    engineer_channel = interaction.guild.get_channel(settings.get('engineer_channel_id'))
    
    if not engineer_channel:
        return "Could not find the engineer channel. Please ensure the bot has been set up correctly."

    # Create a dictionary of the role objects needed by the backfill function
    role_objects = {
        'Student': interaction.guild.get_role(settings.get('student_id')),
        'Alumni': interaction.guild.get_role(settings.get('alumni_id')),
        'Friend': interaction.guild.get_role(settings.get('friend_id')),
        'Verified': interaction.guild.get_role(settings.get('verified_id')),
    }
    
    await _backfill_users(interaction.guild, role_objects, engineer_channel, assign_verified_role=True)
    return "Backfill process complete. Check the engineer channel for detailed logs."
