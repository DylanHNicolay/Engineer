import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Callable
import re
from datetime import datetime
import asyncio

from .prompts import ask, get_input
from utils.db import db

def is_admin_check():
    """
    A check to see if the user is an admin.
    This check is meant to be used on app commands within a cog.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        admin_cog = interaction.client.get_cog('Admin')
        if not admin_cog:
            await interaction.response.send_message("Admin cog not found.", ephemeral=True)
            return False

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False

        if not await admin_cog.is_admin(interaction.user):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return False
        
        return True
    return app_commands.check(predicate)

class ConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

class SemesterSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Fall", value="Fall"),
            discord.SelectOption(label="Summer", value="Summer"),
            discord.SelectOption(label="Spring", value="Spring"),
        ]
        super().__init__(placeholder="Choose a semester...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.values[0]
        self.view.stop()
        await interaction.response.defer()

class SemesterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.value = None
        self.add_item(SemesterSelect())

class Teams(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _parse_role(self, message: discord.Message) -> discord.Role | str:
        if message.role_mentions:
            return message.role_mentions[0]
        return message.content

    async def _parse_category(self, message: discord.Message) -> discord.CategoryChannel | str:
        if message.channel_mentions:
            if isinstance(message.channel_mentions[0], discord.CategoryChannel):
                return message.channel_mentions[0]
            else:
                raise ValueError("Mentioned channel is not a category.")
        
        try:
            category_id = int(message.content)
            category = message.guild.get_channel(category_id)
            if isinstance(category, discord.CategoryChannel):
                return category
            else:
                raise ValueError(f"Channel with ID {category_id} is not a category.")
        except (ValueError, TypeError):
            return message.content # It's a string name

    async def _parse_channel(self, message: discord.Message) -> discord.TextChannel | str:
        if message.channel_mentions:
            if isinstance(message.channel_mentions[0], discord.TextChannel):
                return message.channel_mentions[0]
            else:
                raise ValueError("Mentioned channel is not a text channel.")
        
        try:
            channel_id = int(message.content)
            channel = message.guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                return channel
            else:
                raise ValueError(f"Channel with ID {channel_id} is not a text channel.")
        except (ValueError, TypeError):
            return message.content # It's a string name

    async def _parse_member(self, message: discord.Message) -> discord.Member:
        if message.mentions:
            return message.mentions[0]
        
        try:
            member_id = int(message.content)
            member = await message.guild.fetch_member(member_id)
            if member:
                return member
        except (ValueError, TypeError, discord.NotFound, discord.HTTPException):
            raise ValueError("Invalid user ID or user not found.")
        raise ValueError("No valid user mentioned or ID provided.")

    async def _parse_members(self, message: discord.Message) -> List[discord.Member]:
        if not message.content or message.content.upper() == 'N/A':
            return []
        
        members = []
        # Add mentioned members
        if message.mentions:
            members.extend(message.mentions)

        # Extract IDs from the message content
        ids = re.findall(r'\d{17,}', message.content)
        
        # Fetch members by ID, avoiding duplicates
        for member_id in ids:
            member_id = int(member_id)
            if member_id not in [m.id for m in members]:
                try:
                    member = await message.guild.fetch_member(member_id)
                    if member:
                        members.append(member)
                except (discord.NotFound, discord.HTTPException):
                    await message.channel.send(f"Warning: Could not find a member with ID {member_id}.", delete_after=10)
                    continue
        
        if not members:
            raise ValueError("No valid members mentioned or IDs provided. Please provide mentions or user IDs.")
        return members

    @app_commands.command(name="create-team", description="Create a new team via an interactive process.")
    @is_admin_check()
    async def create_team(self, interaction: discord.Interaction):
        """Interactively creates a new team, role, and channel."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return

        await interaction.response.send_message("Starting team creation process... You can type `(Exit)` at any time to cancel.", ephemeral=True)

        details = {
            "nick": None,
            "role": None,
            "category": None,
            "channel": None,
            "captain": None,
            "starters": [],
            "substitutes": [],
            "year": None,
            "semester": None
        }

        # Helper to get a specific detail
        async def get_detail(step: int, key: str, question: str, parser: Callable, followup: bool = True):
            while True:
                response = await get_input(interaction, f"**Step {step}/9: {question}**", parser, followup=followup)
                if response is None and response is not False: return "cancel"
                
                # Confirmation for creation of new entities
                if key in ["role", "category", "channel"] and isinstance(response, str):
                    confirm_view = ConfirmationView()
                    await interaction.followup.send(f"The {key} '{response}' does not exist. Do you want to create it?", view=confirm_view, ephemeral=True)
                    await confirm_view.wait()
                    if confirm_view.value:
                        details[key] = response
                        return "continue"
                    elif confirm_view.value is False:
                        await interaction.followup.send(f"Please provide an existing {key} or a new name.", ephemeral=True)
                        continue # Ask again
                    else: # Timeout
                        return "cancel"
                
                details[key] = response
                return "continue"

        # Helper parsers that work with the async get_input function
        async def parse_nick(m: discord.Message):
            return m.content if m.content.upper() != 'N/A' else None
        
        async def parse_year(m: discord.Message):
            return int(m.content)

        # --- Interactive Process ---
        if await get_detail(1, "nick", "Team Nickname (type N/A to skip)", parse_nick) == "cancel": return
        if await get_detail(2, "role", "Team Role (mention or provide name)", self._parse_role) == "cancel": return
        if await get_detail(3, "category", "Team Category (mention, ID, or name)", self._parse_category) == "cancel": return
        if await get_detail(4, "channel", "Team Channel (mention, ID, or name)", self._parse_channel) == "cancel": return
        if await get_detail(5, "captain", "Team Captain (mention or ID)", self._parse_member) == "cancel": return
        if await get_detail(6, "starters", "Starters (mention or ID, N/A for none)", self._parse_members) == "cancel": return
        if await get_detail(7, "substitutes", "Substitutes (mention or ID, N/A for none)", self._parse_members) == "cancel": return
        if await get_detail(8, "year", "Team Year (e.g., 2023)", parse_year) == "cancel": return
        
        # Semester
        semester_view = SemesterView()
        await interaction.followup.send("**Step 9/9: Team Semester**", view=semester_view, ephemeral=True)
        await semester_view.wait()
        if semester_view.value is None:
            await interaction.followup.send("Timed out. Process cancelled.", ephemeral=True)
            return
        details["semester"] = semester_view.value

        # --- Confirmation and Revision ---
        while True:
            summary = (
                f"**Team Creation Summary**\n"
                f"1. **Nickname**: {details['nick']}\n"
                f"2. **Role**: {details['role'].mention if isinstance(details['role'], discord.Role) else details['role']}\n"
                f"3. **Category**: {details['category'].name if isinstance(details['category'], discord.CategoryChannel) else details['category']}\n"
                f"4. **Channel**: {details['channel'].mention if isinstance(details['channel'], discord.TextChannel) else details['channel']}\n"
                f"5. **Captain**: {details['captain'].mention}\n"
                f"6. **Starters**: {', '.join([m.mention for m in details['starters']]) or 'None'}\n"
                f"7. **Substitutes**: {', '.join([m.mention for m in details['substitutes']]) or 'None'}\n"
                f"8. **Year**: {details['year']}\n"
                f"9. **Semester**: {details['semester']}\n"
            )
            
            confirm_view = ConfirmationView()
            await interaction.followup.send(f"Please review the details. To revise, type the number of the item you want to change. Otherwise, confirm.\n\n{summary}", view=confirm_view, ephemeral=True)
            await confirm_view.wait()

            if confirm_view.value:
                break # Confirmed
            elif confirm_view.value is False:
                await interaction.followup.send("Process cancelled.", ephemeral=True)
                return
            else: # Timed out, or wants to revise
                try:
                    response_msg = await self.bot.wait_for(
                        "message",
                        timeout=300.0,
                        check=lambda m: m.author == interaction.user and m.channel == interaction.channel and m.content.isdigit() and 1 <= int(m.content) <= 9
                    )
                    item_to_revise = int(response_msg.content)
                    await response_msg.delete()

                    if item_to_revise == 1: await get_detail(1, "nick", "Team Nickname (type N/A to skip)", parse_nick, False)
                    elif item_to_revise == 2: await get_detail(2, "role", "Team Role (mention or provide name)", self._parse_role, False)
                    elif item_to_revise == 3: await get_detail(3, "category", "Team Category (mention, ID, or name)", self._parse_category, False)
                    elif item_to_revise == 4: await get_detail(4, "channel", "Team Channel (mention, ID, or name)", self._parse_channel, False)
                    elif item_to_revise == 5: await get_detail(5, "captain", "Team Captain (mention or ID)", self._parse_member, False)
                    elif item_to_revise == 6: await get_detail(6, "starters", "Starters (mention or ID, N/A for none)", self._parse_members, False)
                    elif item_to_revise == 7: await get_detail(7, "substitutes", "Substitutes (mention or ID, N/A for none)", self._parse_members, False)
                    elif item_to_revise == 8: await get_detail(8, "year", "Team Year (e.g., 2023)", parse_year, False)
                    elif item_to_revise == 9:
                        semester_view = SemesterView()
                        await interaction.followup.send("**Step 9/9: Team Semester**", view=semester_view, ephemeral=True)
                        await semester_view.wait()
                        if semester_view.value: details["semester"] = semester_view.value

                except asyncio.TimeoutError:
                    await interaction.followup.send("Timed out. Process cancelled.", ephemeral=True)
                    return

        # --- Final Creation Logic ---
        await interaction.followup.send("Creating team...", ephemeral=True)

        # Handle Role
        role = details['role']
        if isinstance(role, str):
            try:
                role = await guild.create_role(name=role, mentionable=True)
                await interaction.followup.send(f"Role `{role.name}` created.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Failed to create role: {e}", ephemeral=True)
                return
        
        # Handle Category
        category = details['category']
        if isinstance(category, str):
            try:
                category = await guild.create_category(name=category)
                await interaction.followup.send(f"Category `{category.name}` created.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Failed to create category: {e}", ephemeral=True)
                return

        # Handle Channel
        channel = details['channel']
        if isinstance(channel, str):
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    role: discord.PermissionOverwrite(read_messages=True)
                }
                channel = await guild.create_text_channel(name=channel, category=category, overwrites=overwrites)
                await interaction.followup.send(f"Channel `{channel.name}` created.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Failed to create channel: {e}", ephemeral=True)
                return

        # Archive existing teams if necessary
        try:
            await db.execute(
                """
                UPDATE teams SET archived = TRUE 
                WHERE role_id = $1 AND category_id = $2 AND channel_id = $3 AND archived = FALSE
                """,
                role.id, category.id, channel.id
            )
        except Exception as e:
            await interaction.followup.send(f"Error archiving existing teams: {e}", ephemeral=True)
            return

        # Database insertion
        try:
            team_id = await db.execute(
                """
                INSERT INTO teams (team_nick, role_id, channel_id, category_id, captain_discord_id, year, semester)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING team_id
                """,
                details['nick'], role.id, channel.id, category.id, details['captain'].id, details['year'], details['semester']
            )
            team_id = team_id[0]['team_id']

            # Add members
            all_members = details['starters'] + details['substitutes']
            for member in all_members:
                is_starter = member in details['starters']
                await db.execute("INSERT INTO players (player_discord_id) VALUES ($1) ON CONFLICT DO NOTHING", member.id)
                await db.execute(
                    "INSERT INTO team_members (team_id, player_discord_id, is_starter) VALUES ($1, $2, $3)",
                    team_id, member.id, is_starter
                )
                await member.add_roles(role)

            await interaction.followup.send(f"Team `{details['nick'] or 'Unnamed'}` created successfully!", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"An error occurred during database insertion: {e}", ephemeral=True)
            # TODO: Add undo logic here
            return

    @app_commands.command(name="archive_team", description="Archive a team")
    @is_admin_check()
    async def archive_team(self, interaction: discord.Interaction, team_name: str):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="undo_create_team", description="Undo the creation of a team")
    @is_admin_check()
    async def undo_create_team(self, interaction: discord.Interaction, team_name: str):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="list_teams", description="List all teams")
    async def list_teams(self, interaction: discord.Interaction):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="add_player_to_team", description="Add a player to a team")
    @is_admin_check()
    async def add_player_to_team(self, interaction: discord.Interaction, team_name: str, player: discord.Member):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)

    @app_commands.command(name="remove_player_from_team", description="Remove a player from a team")
    @is_admin_check()
    async def remove_player_from_team(self, interaction: discord.Interaction, team_name: str, player: discord.Member):
        await interaction.response.send_message("This command is not yet implemented.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Teams(bot))
