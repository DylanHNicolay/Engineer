import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db
import re

class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    roles = app_commands.Group(name="roles", description="Role reaction commands")

    @roles.command(name="create_message", description="Create a message for role reactions.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_message(self, interaction: discord.Interaction, title: str, description: str):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        try:
            message = await interaction.channel.send(embed=embed)
            await db.execute("INSERT INTO role_reaction_messages (message_id) VALUES ($1)", message.id)
            await interaction.followup.send(f"Role reaction message created with ID `{message.id}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to create role reaction message. Error: {e}", ephemeral=True)

    @roles.command(name="add", description="Add a role reaction to a message.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: discord.Interaction, message_id: str, role: discord.Role, emoji: str):
        await interaction.response.defer(ephemeral=True)
        try:
            message_id_int = int(message_id)
            message = await interaction.channel.fetch_message(message_id_int)
        except (ValueError, discord.NotFound):
            await interaction.followup.send("Invalid Message ID or message not found in this channel.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("I don't have permissions to see that message.", ephemeral=True)
            return

        # Check for custom emoji format
        custom_emoji_match = re.match(r'<a?:(\w+):(\d+)>', emoji)
        if custom_emoji_match:
            # It's a custom emoji, add it to the message
            emoji_to_react = self.bot.get_emoji(int(custom_emoji_match.group(2)))
            if not emoji_to_react:
                await interaction.followup.send("I can't use that custom emoji, I'm likely not in the server it belongs to.", ephemeral=True)
                return
        else:
            # It's a standard Unicode emoji
            emoji_to_react = emoji

        try:
            await db.execute(
                "INSERT INTO role_reactions (message_id, guild_id, role_id, emoji) VALUES ($1, $2, $3, $4)",
                message.id, interaction.guild.id, role.id, emoji
            )
            await message.add_reaction(emoji_to_react)
            await interaction.followup.send(f"Role reaction added. Users who react with {emoji} will get the {role.name} role.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to add role reaction. It might already exist for this message and emoji. Error: {e}", ephemeral=True)

    @roles.command(name="remove", description="Remove a role reaction from a message.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction, message_id: str, emoji: str):
        await interaction.response.defer(ephemeral=True)
        try:
            message_id_int = int(message_id)
        except ValueError:
            await interaction.followup.send("Invalid Message ID.", ephemeral=True)
            return

        deleted_records = await db.execute(
            "DELETE FROM role_reactions WHERE message_id = $1 AND emoji = $2 RETURNING role_id",
            message_id_int, emoji
        )

        if deleted_records:
            try:
                message = await interaction.channel.fetch_message(message_id_int)
                await message.clear_reaction(emoji)
            except (discord.NotFound, discord.Forbidden):
                pass  # Message might be deleted or bot lacks perms, but DB entry is gone.
            await interaction.followup.send(f"Role reaction for {emoji} removed.", ephemeral=True)
        else:
            await interaction.followup.send("No role reaction found for that message and emoji.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        reaction_info = await db.execute(
            "SELECT role_id FROM role_reactions WHERE message_id = $1 AND emoji = $2",
            payload.message_id, str(payload.emoji)
        )

        if reaction_info:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            role = guild.get_role(reaction_info[0]['role_id'])
            member = guild.get_member(payload.user_id)

            if role and member:
                await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        reaction_info = await db.execute(
            "SELECT role_id FROM role_reactions WHERE message_id = $1 AND emoji = $2",
            payload.message_id, str(payload.emoji)
        )

        if reaction_info:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return

            role = guild.get_role(reaction_info[0]['role_id'])
            member = guild.get_member(payload.user_id)

            if role and member:
                await member.remove_roles(role)

async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))
