from discord.ext import commands
from discord import app_commands
import discord

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_team", description="Create a new team")
    async def create_team(self, interaction: discord.Interaction, team_name: str):
        """Creates a new team, role, and channel."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        # Create a role for the team
        try:
            team_role = await guild.create_role(name=team_name, mentionable=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to create roles.", ephemeral=True)
            return

        # Create a category for the team if it doesn't exist
        category_name = "Teams"
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            try:
                category = await guild.create_category(category_name)
            except discord.Forbidden:
                await interaction.response.send_message("I don't have permission to create categories.", ephemeral=True)
                return

        # Create a text channel for the team under the category
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                team_role: discord.PermissionOverwrite(read_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            team_channel = await guild.create_text_channel(name=team_name, category=category, overwrites=overwrites)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to create channels.", ephemeral=True)
            # Clean up created role
            await team_role.delete()
            return
        
        # Add captain to the team role
        captain = interaction.user
        if isinstance(captain, discord.Member):
            await captain.add_roles(team_role)

        # TODO: Add team to database

        await interaction.response.send_message(f"Team '{team_name}' created! You can find it at {team_channel.mention}")

    @app_commands.command(name="archive_team", description="Archive a team")
    async def archive_team(self, interaction: discord.Interaction, team_name: str):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="undo_create_team", description="Undo the creation of a team")
    async def undo_create_team(self, interaction: discord.Interaction, team_name: str):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="list_teams", description="List all teams")
    async def list_teams(self, interaction: discord.Interaction):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="add_player_to_team", description="Add a player to a team")
    async def add_player_to_team(self, interaction: discord.Interaction, team_name: str, player: discord.Member):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="remove_player_from_team", description="Remove a player from a team")
    async def remove_player_from_team(self, interaction: discord.Interaction, team_name: str, player: discord.Member):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Teams(bot))
