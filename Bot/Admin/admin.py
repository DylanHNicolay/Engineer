import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    admin = app_commands.Group(name="admin", description="Admin commands")

    @admin.command(name="define", description="Define an admin role.")
    async def define(self, interaction: discord.Interaction, role: discord.Role):
        """Define an admin role."""
        # Defer the response to prevent the interaction from timing out
        await interaction.response.defer()
        try:
            # Check if the role already exists
            existing_role = await db.execute("SELECT * FROM admin_roles WHERE role_id = $1", role.id)
            if existing_role:
                await interaction.followup.send(f"Role {role.mention} is already an admin role.")
                return
            await db.execute("INSERT INTO admin_roles (role_id) VALUES ($1)", role.id)
            await interaction.followup.send(f"Role {role.mention} has been added as an admin role.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
