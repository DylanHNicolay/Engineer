import discord
from discord import app_commands
from discord.ext import commands
from typing import List
from utils.db import db

class ArchiveTeam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="archive_team", description="Archive an existing team.")
    @app_commands.describe(team_nick="The nickname of the team to archive", move_to_archives="Move the team channel to Archives category")
    async def archive_team(self, interaction: discord.Interaction, team_nick: str, move_to_archives: bool = True):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        admin_cog = interaction.client.get_cog("Admin")
        if admin_cog is None or not await admin_cog.is_admin(interaction.user):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Find team
        teams = await db.execute("SELECT * FROM teams WHERE team_nick = $1 AND archived = FALSE", team_nick)
        if not teams:
            await interaction.followup.send(f"Active team with nickname `{team_nick}` not found.")
            return
        
        if len(teams) > 1:
             await interaction.followup.send(f"Multiple active teams found with nickname `{team_nick}`. Please fix database manually.")
             return

        team = teams[0]
        team_id = team['team_id']
        channel_id = team['channel_id']
        role_id = team['role_id']

        # Archive in DB
        await db.execute("UPDATE teams SET archived = TRUE WHERE team_id = $1", team_id)

        msg = f"Team `{team_nick}` has been archived."

        channel = guild.get_channel(channel_id)
        role = guild.get_role(role_id)

        if channel and role:
            members_processed = 0
            for member in role.members:
                try:
                    # Grant channel access
                    overwrite = channel.overwrites_for(member)
                    overwrite.view_channel = True
                    await channel.set_permissions(member, overwrite=overwrite)
                    
                    # Remove role
                    await member.remove_roles(role)
                    members_processed += 1
                except Exception as e:
                    print(f"Failed to process {member}: {e}")
            msg += f" Updated permissions and removed role for {members_processed} members."

            try:
                await role.delete(reason=f"Team {team_nick} archived")
                msg += " Role deleted."
            except Exception as e:
                msg += f" Failed to delete role: {e}"

        if move_to_archives:
            if channel:
                try:
                    # Find or create Archives category
                    archives_cat = discord.utils.find(lambda c: c.name.lower() == "archives" and isinstance(c, discord.CategoryChannel), guild.categories)
                    if not archives_cat:
                        archives_cat = await guild.create_category("Archives")
                    
                    await channel.edit(category=archives_cat)
                    msg += f" Channel {channel.mention} moved to {archives_cat.mention}."
                except Exception as e:
                    msg += f" Failed to move channel to Archives: {e}"
            else:
                msg += " Channel not found, could not move."

        await interaction.followup.send(msg)

    @archive_team.autocomplete('team_nick')
    async def archive_team_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = "SELECT team_nick FROM teams WHERE team_nick ILIKE $1 AND archived = FALSE LIMIT 25"
        records = await db.execute(query, f"%{current}%")
        return [app_commands.Choice(name=r['team_nick'], value=r['team_nick']) for r in records]

async def setup(bot: commands.Bot):
    await bot.add_cog(ArchiveTeam(bot))
