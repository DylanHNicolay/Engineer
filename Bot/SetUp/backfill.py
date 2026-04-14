import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db
from Admin.admin import Admin

async def add_user(user_id: int, years_remaining: int = None):
    """
    Adds or updates a user in the database.

    Args:
        user_id (int): The Discord ID of the user.
        years_remaining (int, optional): The number of years remaining for the user. Defaults to None.
    """
    await db.execute(
        """
        INSERT INTO users (discord_id, years_remaining)
        VALUES ($1, $2)
        ON CONFLICT (discord_id) DO UPDATE SET
        years_remaining = EXCLUDED.years_remaining;
        """,
        user_id,
        years_remaining
    )


async def _backfill_users(guild: discord.Guild, role_objects: dict, engineer_channel: discord.TextChannel, assign_verified_role=False):
    """
    Backfills the DB. If assign_verified_role is True, grants 'Verified' to users with no role.
    """
    logs = ["**Starting Database Backfill**\n---"]
    
    if not guild.chunked:
        try:
            await guild.chunk(cache=True)
        except discord.errors.ClientException:
            logs.append(f"⚠️ **Warning:** Could not chunk members. Please enable the Server Members Intent.")
    
    logs.append(f"Found `{len(guild.members)}` members in cache.")
    
    existing_users_records = await db.execute("SELECT discord_id FROM users")
    existing_user_ids = {record['discord_id'] for record in existing_users_records}
    logs.append(f"Found `{len(existing_user_ids)}` users in DB.")
    logs.append("---")
    
    backfill_count = 0
    verified_role = role_objects.get('Verified')
    managed_roles = {role for role in role_objects.values() if role is not None}

    for member in guild.members:
        if member.bot or member.id in existing_user_ids:
            continue

        member_has_managed_role = any(role in member.roles for role in managed_roles)

        if not member_has_managed_role:
            if assign_verified_role:
                if verified_role:
                    try:
                        await member.add_roles(verified_role)
                        await add_user(member.id, -2)
                        backfill_count += 1
                        logs.append(f"User `{member.name}` had no role. Granted **Verified**.")
                    except discord.Forbidden:
                        logs.append(f"Could not grant Verified to `{member.name}`. Check permissions.")
                else:
                    logs.append(f"Could not grant Verified to `{member.name}` (role not configured).")
        else:
            if role_objects.get('Student') in member.roles:
                await add_user(member.id, 1)
                logs.append(f"Found existing **Student** `{member.name}` and added to DB.")
                backfill_count += 1
            elif role_objects.get('Alumni') in member.roles:
                await add_user(member.id, 0)
                logs.append(f"Found existing **Alumni** `{member.name}` and added to DB.")
                backfill_count += 1
            elif role_objects.get('Friend') in member.roles:
                await add_user(member.id, -1)
                logs.append(f"Found existing **Friend** `{member.name}` and added to DB.")
                backfill_count += 1
            elif verified_role in member.roles:
                 await add_user(member.id, -2)
                 logs.append(f"Found existing **Verified** user `{member.name}` and added to DB.")
                 backfill_count += 1

    logs.append("---\n**Database backfill complete.**")
    logs.append(f"Processed and added `{backfill_count}` users to the database.")
    
    log_message = "\n".join(logs)
    if len(log_message) > 2000:
        await engineer_channel.send(log_message[:2000])
        await engineer_channel.send(log_message[2000:])
    else:
        await engineer_channel.send(log_message)


class Backfill(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="backfill", description="Manually backfill the database with existing members.")
    async def backfill(self, interaction: discord.Interaction):
        
        admin_cog = self.bot.get_cog("Admin")
        if (
            not isinstance(admin_cog, Admin)
            or not await admin_cog.is_admin(interaction.user)
        ):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)

        try:
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
            await interaction.followup.send( "Backfill process complete. Check the engineer channel for detailed logs.")
        
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")
        

async def setup(bot: commands.Bot):
    await bot.add_cog(Backfill(bot))