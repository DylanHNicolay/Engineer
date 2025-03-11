import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from .utils.setup_utils import handle_role_check

class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending_setups = {}  # Track pending setups per guild (guild_id -> task)
        self.setup_channels = {}  # Map guild_id to its setup channel

    # Define the slash command group at the class level.
    configure = app_commands.Group(
        name="configure", 
        description="Server configuration commands"
    )

    @configure.command(name="role_check", description="Check and configure required roles.")
    async def role_check(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        guild = interaction.guild
        setup_channel = self.setup_channels.get(guild_id)
        if not setup_channel:
            await interaction.response.send_message("No setup channel found.", ephemeral=True)
            return

        # Reset the timer upon executing /configure role_check
        if guild_id in self.pending_setups:
            self.pending_setups[guild_id].cancel()
        self.pending_setups[guild_id] = asyncio.create_task(self.timeout_setup(guild, setup_channel))

        # Ensure the setup transaction is started if not already
        if not self.bot.db_manager.in_use:
            await self.bot.db_manager.start_setup_transaction(guild_id)

        await interaction.response.send_message("Starting role check...", ephemeral=True)

        try:
            await handle_role_check(self.bot, guild, setup_channel)
        except Exception as e:
            await setup_channel.send(f"Error in role check: {e}")
            await self.bot.db_manager.rollback_setup_transaction()
            await setup_channel.delete()
            await guild.leave()

    @configure.command(name="finish", description="Finish setup and commit changes.")
    async def finish(self, interaction: discord.Interaction):
        try:
            await self.bot.db_manager.commit_setup_transaction()
            await interaction.response.send_message("Setup finished and committed.", ephemeral=True)
        except Exception as e:
            await self.bot.db_manager.rollback_setup_transaction()
            await interaction.response.send_message(f"Error: {e}. Rolling back and leaving.", ephemeral=True)
            setup_channel = self.setup_channels.get(interaction.guild_id)
            if setup_channel:
                try:
                    await setup_channel.delete()
                except Exception:
                    pass
            await interaction.guild.leave()

    async def timeout_setup(self, guild: discord.Guild, setup_channel: discord.TextChannel):
        await asyncio.sleep(300)  # Wait 5 minutes
        try:
            await setup_channel.delete()
        except Exception:
            pass
        try:
            await guild.owner.send(
                "You did not set up the bot in time. The channel has been deleted and the bot is leaving the server."
            )
        except Exception:
            pass
        self.pending_setups.pop(guild.id, None)
        self.setup_channels.pop(guild.id, None)
        await guild.leave()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # Add guild to database and begin setup transaction
        await self.bot.db_manager.add_guild(guild.id)
        await self.bot.db_manager.start_setup_transaction(guild.id)
        bot_role = guild.get_member(self.bot.user.id).top_role

        # Create channel overwrites for the setup channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.owner: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            self.bot.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Create the setup channel
        setup_channel = await guild.create_text_channel(
            'engineer',
            overwrites=overwrites,
            topic="Bot setup channel - Only server owner can see this"
        )
        self.setup_channels[guild.id] = setup_channel

        # Send initial setup message
        await setup_channel.send(
            f"Welcome {guild.owner.mention}! Setup started! Please move the bot's role to the very top of the role hierarchy.\n"
        )

        # Insert guild data into the database
        await self.bot.db_manager.insert_guild_data(guild.id, bot_role.id, setup_channel.id)

        # Schedule setup timeout
        self.pending_setups[guild.id] = asyncio.create_task(self.timeout_setup(guild, setup_channel))

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        guild = after.guild
        bot_member = guild.get_member(self.bot.user.id)
        if not bot_member:
            return
        if after.id in [role.id for role in bot_member.roles]:
            setup_channel = self.setup_channels.get(guild.id)
            if not setup_channel:
                return
            highest_position = max(guild.roles, key=lambda r: r.position).position
            if after.position == highest_position:
                await setup_channel.send("The bot's role is at the top of the role hierarchy! Please execute `/configure role_check`.")
            else:
                await setup_channel.send("Please move Engineer's role to the top of the role hierarchy. It must not be below any other role.")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        # Clean up pending setup if the guild is removed
        self.pending_setups.pop(guild.id, None)

async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))