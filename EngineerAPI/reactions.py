import discord
from discord.ext import commands
import os
import json
import asyncio
import re  # Import regex module

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_emojis = self.load_role_emojis()
        self.load_message_id()
        bot.loop.create_task(self.ensure_reaction_message())

    def load_role_emojis(self):
        try:
            with open('role_emojis.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "Dota2": "dota2",
                "TF2": "tf2",
                "R6": "rb6",
                "League": "league",
                "OW": "ow",
                "CS2": "csgo",
                "Valorant": "valorant",
                "RL": "rocketleague",
                "SC2": "sc2",
                "Omega Strikers": "omegastrikers",
                "Racing": "🏎️",  # Use actual emoji character
            }

    def save_role_emojis(self):
        with open('role_emojis.json', 'w') as f:
            json.dump(self.role_emojis, f)

    def load_message_id(self):
        try:
            with open('reaction_message_id.txt', 'r') as f:
                self.bot.reaction_message_id = int(f.read())
        except (FileNotFoundError, ValueError):
            self.bot.reaction_message_id = None

    async def ensure_reaction_message(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)  # Add a delay to ensure cache is populated
        await self.update_reaction_message()

    async def update_reaction_message(self):
        channel = self.bot.get_channel(int(os.getenv("VERIFICATION_CHANNEL_ID")))
        if channel is None:
            return

        guild = channel.guild

        # Ensure emojis are fetched from the API
        guild_emojis = await guild.fetch_emojis()

        embed = discord.Embed(
            title="Game Roles",
            description="React to get pinged for game PUG roles."
        )

        for role_name, emoji_identifier in self.role_emojis.items():
            # Ensure the role exists
            role = discord.utils.get(guild.roles, name=role_name)
            if role is None:
                role = await guild.create_role(name=role_name)

            # Check if the emoji is a custom emoji
            custom_emoji = discord.utils.get(guild_emojis, name=emoji_identifier)
            if custom_emoji:
                emoji = custom_emoji
                emoji_display = str(custom_emoji)
            else:
                # Assume it's a standard emoji character
                emoji = emoji_identifier
                emoji_display = emoji_identifier

            embed.add_field(name=role_name, value=emoji_display, inline=True)

        message = None
        if self.bot.reaction_message_id:
            try:
                message = await channel.fetch_message(self.bot.reaction_message_id)
            except discord.NotFound:
                pass

        if message:
            await message.edit(embed=embed)
            await message.clear_reactions()
        else:
            message = await channel.send(embed=embed)
            self.bot.reaction_message_id = message.id
            with open('reaction_message_id.txt', 'w') as f:
                f.write(str(message.id))

        # Add reactions
        for emoji_identifier in self.role_emojis.values():
            # Check if it's a custom emoji
            custom_emoji = discord.utils.get(guild.emojis, name=emoji_identifier)
            if custom_emoji:
                emoji = custom_emoji
            else:
                # Assume it's a standard emoji character
                emoji = emoji_identifier

            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                pass  # Skip if the emoji is invalid

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id != self.bot.reaction_message_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        emoji = payload.emoji  # This is a PartialEmoji or str
        for role_name, emoji_identifier in self.role_emojis.items():
            custom_emoji = discord.utils.get(guild.emojis, name=emoji_identifier)
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if member and role:
                if custom_emoji and emoji.id == custom_emoji.id:
                    await member.add_roles(role)
                    break
                elif not custom_emoji and emoji.name == emoji_identifier:
                    await member.add_roles(role)
                    break

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id != self.bot.reaction_message_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        emoji = payload.emoji
        for role_name, emoji_identifier in self.role_emojis.items():
            custom_emoji = discord.utils.get(guild.emojis, name=emoji_identifier)
            role = discord.utils.get(guild.roles, name=role_name)
            member = guild.get_member(payload.user_id)
            if member and role:
                if custom_emoji and emoji.id == custom_emoji.id:
                    await member.remove_roles(role)
                    break
                elif not custom_emoji and emoji.name == emoji_identifier:
                    await member.remove_roles(role)
                    break

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
