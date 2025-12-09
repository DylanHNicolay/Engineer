import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db

class SetDues(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="set_dues_starters", description="Set the dues amount for starters.")
    @app_commands.describe(amount="The amount for starter dues")
    async def set_dues_starters(self, interaction: discord.Interaction, amount: int):
        admin_cog = interaction.client.get_cog("Admin")
        if admin_cog is None or not await admin_cog.is_admin(interaction.user):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Check if a row exists
            rows = await db.execute("SELECT * FROM dues LIMIT 1")
            if rows:
                await db.execute("UPDATE dues SET starters = $1", amount)
            else:
                # Note: 'substitues' is the column name in init.sql
                await db.execute("INSERT INTO dues (starters, substitues, non_player) VALUES ($1, 0, 0)", amount)
            
            await interaction.followup.send(f"Starter dues set to {amount}.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="set_dues_substitutes", description="Set the dues amount for substitutes.")
    @app_commands.describe(amount="The amount for substitute dues")
    async def set_dues_substitutes(self, interaction: discord.Interaction, amount: int):
        admin_cog = interaction.client.get_cog("Admin")
        if admin_cog is None or not await admin_cog.is_admin(interaction.user):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Check if a row exists
            rows = await db.execute("SELECT * FROM dues LIMIT 1")
            if rows:
                await db.execute("UPDATE dues SET substitues = $1", amount)
            else:
                await db.execute("INSERT INTO dues (starters, substitues, non_player) VALUES (0, $1, 0)", amount)
            
            await interaction.followup.send(f"Substitute dues set to {amount}.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SetDues(bot))
