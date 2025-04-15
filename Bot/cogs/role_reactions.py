import discord
from discord.ext import commands
from discord import app_commands
import logging

class RoleReactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.guild_id is None:
            return
        db = self.bot.db_interface
        record = await db.fetchrow(
            """
            SELECT role_id FROM role_reactions
            WHERE guild_id = $1 AND message_id = $2 AND emoji = $3
            """, payload.guild_id, payload.message_id, str(payload.emoji)
        )
        if record:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            member = guild.get_member(payload.user_id)
            if not member or member.bot:
                return
            role = guild.get_role(record['role_id'])
            if role:
                try:
                    await member.add_roles(role, reason="Role reaction add")
                except Exception as e:
                    self.logger.error(f"Failed to add role: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.guild_id is None:
            return
        db = self.bot.db_interface
        record = await db.fetchrow(
            """
            SELECT role_id FROM role_reactions
            WHERE guild_id = $1 AND message_id = $2 AND emoji = $3
            """, payload.guild_id, payload.message_id, str(payload.emoji)
        )
        if record:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            member = guild.get_member(payload.user_id)
            if not member or member.bot:
                return
            role = guild.get_role(record['role_id'])
            if role:
                try:
                    await member.remove_roles(role, reason="Role reaction remove")
                except Exception as e:
                    self.logger.error(f"Failed to remove role: {e}")

    @app_commands.command(name="addrolereaction", description="Create a role reaction on a message.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_role_reaction(self, interaction: discord.Interaction, channel: discord.TextChannel, message_id: str, emoji: str, role: discord.Role):
        """Admins: Add a role reaction to a message."""
        db = self.bot.db_interface
        try:
            await db.execute(
                """
                INSERT INTO role_reactions (guild_id, channel_id, message_id, emoji, role_id)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (guild_id, message_id, emoji) DO UPDATE SET role_id = $5
                """,
                interaction.guild.id, channel.id, int(message_id), emoji, role.id
            )
            msg = await channel.fetch_message(int(message_id))
            await msg.add_reaction(emoji)
            await interaction.response.send_message(f"Role reaction added: {emoji} → {role.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to add role reaction: {e}", ephemeral=True)

    @app_commands.command(name="editrolereaction", description="Edit a role reaction.")
    @app_commands.checks.has_permissions(administrator=True)
    async def edit_role_reaction(self, interaction: discord.Interaction, channel: discord.TextChannel, message_id: str, emoji: str, new_role: discord.Role):
        """Admins: Edit a role reaction to change the role assigned."""
        db = self.bot.db_interface
        result = await db.execute(
            """
            UPDATE role_reactions SET role_id = $1
            WHERE guild_id = $2 AND message_id = $3 AND emoji = $4
            """,
            new_role.id, interaction.guild.id, int(message_id), emoji
        )
        if result and "UPDATE 1" in result:
            await interaction.response.send_message(f"Role reaction updated: {emoji} → {new_role.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("No such role reaction found.", ephemeral=True)

    @app_commands.command(name="delrolereaction", description="Delete a role reaction.")
    @app_commands.checks.has_permissions(administrator=True)
    async def del_role_reaction(self, interaction: discord.Interaction, channel: discord.TextChannel, message_id: str, emoji: str):
        """Admins: Delete a role reaction from a message."""
        db = self.bot.db_interface
        result = await db.execute(
            """
            DELETE FROM role_reactions
            WHERE guild_id = $1 AND message_id = $2 AND emoji = $3
            """,
            interaction.guild.id, int(message_id), emoji
        )
        if result and "DELETE 1" in result:
            try:
                msg = await channel.fetch_message(int(message_id))
                await msg.clear_reaction(emoji)
            except Exception:
                pass
            await interaction.response.send_message(f"Role reaction deleted: {emoji}", ephemeral=True)
        else:
            await interaction.response.send_message("No such role reaction found.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleReactions(bot))
