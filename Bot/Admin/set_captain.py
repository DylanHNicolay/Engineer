import discord
from discord import app_commands
from discord.ext import commands
from typing import List, cast
from utils.db import db
from Admin.admin import Admin


class SetCaptain(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="set_captain", description="(Admin) Set the captain of an existing team.")
    @app_commands.describe(
        team_nick="Nickname of the team",
        member="The new captain",
    )
    async def set_captain(
        self,
        interaction: discord.Interaction,
        team_nick: str,
        member: discord.Member,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        admin_cog = cast(Admin, self.bot.get_cog("Admin"))
        if (
            not isinstance(interaction.user, discord.Member)
            or admin_cog is None
            or not await admin_cog.is_admin(interaction.user)
        ):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            teams = await db.execute(
                "SELECT team_id FROM teams WHERE team_nick = $1 AND archived = FALSE",
                team_nick,
            )
            if not teams:
                await interaction.followup.send(
                    f"Active team `{team_nick}` not found."
                )
                return

            team_id = teams[0]["team_id"]

            # Ensure the new captain is in the players table
            await db.execute(
                "INSERT INTO players (player_discord_id) VALUES ($1) ON CONFLICT DO NOTHING",
                member.id,
            )

            await db.execute(
                "UPDATE teams SET captain_discord_id = $1 WHERE team_id = $2",
                member.id,
                team_id,
            )
            await interaction.followup.send(
                f"{member.mention} is now the captain of **{team_nick}**."
            )
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @set_captain.autocomplete("team_nick")
    async def team_nick_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        records = await db.execute(
            "SELECT team_nick FROM teams WHERE team_nick ILIKE $1 AND archived = FALSE LIMIT 25",
            f"%{current}%",
        )
        return [
            app_commands.Choice(name=r["team_nick"], value=r["team_nick"])
            for r in records
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(SetCaptain(bot))
