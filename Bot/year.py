import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db
from utils.role_utils import handle_role_change

class Year(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="year", description="Runs the database backfill process for existing members.")
    async def year_command_logic(self, interaction: discord.Interaction):
        """
        Admin command logic to update student years, graduate students, and clean up the database.
        """

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild  
              
        users_in_db = await db.execute("SELECT discord_id, years_remaining FROM users")
        settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", guild.id)
        
       

        if not settings_records:
            return interaction.followup.send(f"Server settings not found. Please run the setup.")
        
        settings = settings_records[0]
        engineer_channel = interaction.guild.get_channel(settings.get('engineer_channel_id'))

        student_role = guild.get_role(settings.get('student_id'))
        alumni_role = guild.get_role(settings.get('alumni_id'))

        if not student_role or not alumni_role:
            return interaction.followup.send(f"Student or Alumni role is not configured on this server.")

        all_status_roles = {
            'Student': student_role,
            'Alumni': alumni_role,
            'Friend': guild.get_role(settings.get('friend_id')),
            'Verified': guild.get_role(settings.get('verified_id')),
        }
        
        logs = []

        for user_record in users_in_db:
            member = guild.get_member(user_record['discord_id'])
            
            if not member:
                await db.execute("DELETE FROM users WHERE discord_id = $1", user_record['discord_id'])
                logs.append(f"Removed user `{user_record['discord_id']}` from database (not found in server).")
                continue
                
            years = user_record['years_remaining']
            
            if years > 1:
                await db.execute("UPDATE users SET years_remaining = $1 WHERE discord_id = $2", years - 1, member.id)
                logs.append(f"Decremented years for `{member.display_name}` to `{years - 1}`.")
                
            elif years == 1:
                await db.execute("UPDATE users SET years_remaining = 0 WHERE discord_id = $1", member.id)
                await handle_role_change(guild, member.id, alumni_role, all_status_roles)
                
                try:
                    dm_channel = await member.create_dm()
                    await dm_channel.send(
                        f"Congratulations! Your status in the `{guild.name}` server has been updated from Student to Alumni. "
                        "If this is a mistake, you can re-verify as a student at any time."
                    )
                    logs.append(f"Graduated `{member.display_name}`. Roles updated and DM sent.")
                except discord.Forbidden:
                    logs.append(f"Graduated `{member.display_name}`. Roles updated, but could not send DM.")
            
            elif years == 0:
                if alumni_role not in member.roles:
                    await handle_role_change(guild, member.id, alumni_role, all_status_roles)
                    logs.append(f"Ensured `{member.display_name}` has the Alumni role (and no other status roles).")

        if not logs:
             logs.append("Year-end process complete. No changes were made.")
        else:
             logs.insert(0,"Year-end process complete.\n\n**Log:**\n" + "\n")

        log_message = "\n".join(logs)

        if len(log_message) > 2000:
            await engineer_channel.send(log_message[:2000])
            await engineer_channel.send(log_message[2000:])
        else:
            await engineer_channel.send(log_message)
            
        return await interaction.followup.send("Year-end process complete. Check the engineer channel for details.")
    
async def setup(bot: commands.Bot):
    await bot.add_cog(Year(bot))