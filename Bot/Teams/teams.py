# import discord
# from discord import app_commands
# from discord.ext import commands

# from Teams.commands.create_team import build_create_team_command

# def is_admin_check():
#     """
#     A check to see if the user is an admin.
#     This check is meant to be used on app commands within a cog.
#     """
#     async def predicate(interaction: discord.Interaction) -> bool:
#         admin_cog = interaction.client.get_cog('Admin')
#         if not admin_cog:
#             await interaction.response.send_message("Admin cog not found.", ephemeral=True)
#             return False

#         if not await admin_cog.is_admin(interaction.user):
#             await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
#             return False
        
#         return True
#     return app_commands.check(predicate)

# class Teams(commands.Cog):
#     def __init__(self, bot: commands.Bot):
#         self.bot = bot

#     create_team = build_create_team_command(is_admin_check)

#     # @app_commands.command(name="archive_team", description="Archive a team")
#     # @is_admin_check()
#     # async def archive_team(self, interaction: discord.Interaction, team_name: str):
#     #     await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

#     # @app_commands.command(name="undo_create_team", description="Undo the creation of a team")
#     # @is_admin_check()
#     # async def undo_create_team(self, interaction: discord.Interaction, team_name: str):
#     #     await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

#     # @app_commands.command(name="list_teams", description="List all teams")
#     # async def list_teams(self, interaction: discord.Interaction):
#     #     await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

#     # @app_commands.command(name="add_player_to_team", description="Add a player to a team")
#     # @is_admin_check()
#     # async def add_player_to_team(self, interaction: discord.Interaction, team_name: str, player: discord.Member):
#     #     await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

#     # @app_commands.command(name="remove_player_from_team", description="Remove a player from a team")
#     # @is_admin_check()
#     # async def remove_player_from_team(self, interaction: discord.Interaction, team_name: str, player: discord.Member):
#     #     await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)


# async def setup(bot: commands.Bot):
#     await bot.add_cog(Teams(bot))
