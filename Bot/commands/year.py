import discord
from discord import app_commands
from utils.db import db
from utils.role_utils import handle_role_change

async def year_command_logic(guild: discord.Guild):
    """
    Admin command logic to update student years, graduate students, and clean up the database.
    """
    users_in_db = await db.execute("SELECT discord_id, years_remaining FROM users")
    settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", guild.id)
    
    if not settings_records:
        return "Server settings not found. Please run the setup."
    
    settings = settings_records[0]
    student_role = guild.get_role(settings.get('student_id'))
    alumni_role = guild.get_role(settings.get('alumni_id'))

    if not student_role or not alumni_role:
        return "Student or Alumni role is not configured on this server."

    all_status_roles = {
        'Student': student_role,
        'Alumni': alumni_role,
        'Friend': guild.get_role(settings.get('friend_id')),
        'Verified': guild.get_role(settings.get('verified_id')),
    }
    
    log = []
    
    for user_record in users_in_db:
        member = guild.get_member(user_record['discord_id'])
        
        if not member:
            await db.execute("DELETE FROM users WHERE discord_id = $1", user_record['discord_id'])
            log.append(f"Removed user `{user_record['discord_id']}` from database (not found in server).")
            continue
            
        years = user_record['years_remaining']
        
        if years > 1:
            await db.execute("UPDATE users SET years_remaining = $1 WHERE discord_id = $2", years - 1, member.id)
            log.append(f"Decremented years for `{member.display_name}` to `{years - 1}`.")
            
        elif years == 1:
            await db.execute("UPDATE users SET years_remaining = 0 WHERE discord_id = $1", member.id)
            await handle_role_change(guild, member.id, alumni_role, all_status_roles)
            
            try:
                dm_channel = await member.create_dm()
                await dm_channel.send(
                    f"Congratulations! Your status in the `{guild.name}` server has been updated from Student to Alumni. "
                    "If this is a mistake, you can re-verify as a student at any time."
                )
                log.append(f"Graduated `{member.display_name}`. Roles updated and DM sent.")
            except discord.Forbidden:
                log.append(f"Graduated `{member.display_name}`. Roles updated, but could not send DM.")
        
        elif years == 0:
            if alumni_role not in member.roles:
                await handle_role_change(guild, member.id, alumni_role, all_status_roles)
                log.append(f"Ensured `{member.display_name}` has the Alumni role (and no other status roles).")

    if not log:
        return "Year-end process complete. No changes were made."
        
    return "Year-end process complete.\n\n**Log:**\n" + "\n".join(log)
