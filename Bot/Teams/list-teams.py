import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db

class ListTeams(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="list_teams", description="List all active teams.")
    async def list_teams(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            teams = await db.execute("SELECT team_nick, year, semester, seniority FROM teams WHERE archived = FALSE ORDER BY year DESC, semester DESC, seniority DESC, team_nick ASC")
            
            if not teams:
                await interaction.followup.send("No active teams found.")
                return

            embed = discord.Embed(title="Active Teams", color=discord.Color.blue())
            
            description = ""
            for team in teams:
                description += f"• **{team['team_nick']}** ({team['semester']} {team['year']}) - Seniority: {team['seniority']}\n"
            
            embed.description = description
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ListTeams(bot))
