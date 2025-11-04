import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def is_admin(self, member: discord.Member) -> bool:
        """Check if a member has an admin role."""
        try:
            admin_roles_records = await db.execute("SELECT role_id FROM admin_roles")
            if not admin_roles_records:
                return False

            admin_role_ids = {record['role_id'] for record in admin_roles_records}
            member_role_ids = {role.id for role in member.roles}

            return not admin_role_ids.isdisjoint(member_role_ids)
        except Exception as e:
            print(f"An error occurred in is_admin check: {e}")
            return False

    admin = app_commands.Group(name="admin", description="Admin commands")

    @admin.command(name="sync", description="Syncs the command tree. (Owner only)")
    async def sync(self, interaction: discord.Interaction):
        """Syncs the command tree."""
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            # Sync to the current guild
            self.bot.tree.copy_global_to(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)

            # Or sync globally
            # await self.bot.tree.sync()

            await interaction.followup.send("Commands synced!")
        except Exception as e:
            await interaction.followup.send(f"An error occurred while syncing: {e}")


    @admin.command(name="define", description="Define an admin role.")
    async def define(self, interaction: discord.Interaction, role: discord.Role):
        """Define an admin role."""
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return

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
