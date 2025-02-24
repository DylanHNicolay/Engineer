import discord
from discord import app_commands
from discord.ext import commands
import asyncio

@app_commands.guild_only()
class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._setup_group = app_commands.Group(name="setup", description="Setup commands for the bot")
        self.bot.tree.add_command(self._setup_group)
        # Track pending setups per guild (guild_id -> task)
        self.pending_setups = {}
        self.setup_channels = {}  # guild_id -> setup_channel

    async def timeout_setup(self, guild: discord.Guild, setup_channel: discord.TextChannel):
        await asyncio.sleep(300)  # wait 5 minutes
        # If still pending, perform timeout actions
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
        # Add guild to database
        await self.bot.db_manager.add_guild(guild.id)
        
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

        # Save setup channel in dict
        self.setup_channels[guild.id] = setup_channel

        # Send initial setup message
        await setup_channel.send(
            f"Welcome {guild.owner.mention}! Please run `/setup begin` within 5 minutes to configure the bot.\n")

        # Schedule setup timeout
        self.pending_setups[guild.id] = asyncio.create_task(self.timeout_setup(guild, setup_channel))

    @app_commands.command(name="begin")
    @app_commands.guild_only()
    async def setup_begin(self, interaction: discord.Interaction):
        if interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Only the server owner can use setup commands!", ephemeral=True)
            return
        # Cancel the timeout task if it exists
        pending = self.pending_setups.pop(interaction.guild.id, None)
        if pending:
            pending.cancel()
        await interaction.response.send_message(
            "Setup started! Please move the bot's role to the very top of the role hierarchy. "
            "It must be the absolute top role (not below any other role). I'll notify in the setup channel once I detect the change."
        )

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
                try:
                    await setup_channel.send("The bot's role is now at the top. You have moved it correctly!")
                    await setup_channel.send("Updating database with server members. Please wait...")

                    # Wrap database operations in a transaction
                    await self.bot.db_manager.pool.execute("BEGIN")
                    for member in guild.members:
                        await self.bot.db_manager.pool.execute(
                            "INSERT INTO users(discord_id) VALUES($1) ON CONFLICT DO NOTHING",
                            member.id
                        )
                        await self.bot.db_manager.pool.execute(
                            "INSERT INTO user_guilds(discord_id, guild_id) VALUES($1, $2) ON CONFLICT DO NOTHING",
                            member.id, guild.id
                        )
                    await self.bot.db_manager.pool.execute(
                        "INSERT INTO guilds(guild_id) VALUES($1) ON CONFLICT DO NOTHING",
                        guild.id
                    )
                    await self.bot.db_manager.pool.execute("COMMIT")

                    # Reset the timer: cancel any existing timeout and start a new 5-minute timeout
                    if guild.id in self.pending_setups:
                        self.pending_setups[guild.id].cancel()
                    self.pending_setups[guild.id] = asyncio.create_task(self.timeout_setup(guild, setup_channel))
                except Exception as e:
                    # Roll back if an error occurs
                    await self.bot.db_manager.pool.execute("ROLLBACK")
                    print(f"Error while updating database: {e}")
                    if setup_channel:
                        try:
                            await setup_channel.send(f"An error occurred while setting up. Error: {e}")
                        except Exception:
                            pass
                        try:
                            await setup_channel.delete()
                        except Exception:
                            pass
                    await guild.leave()
            else:
                try:
                    await setup_channel.send(
                        "The bot's role is not at the very top. Please move it to the top of the role hierarchy, "
                        "so that it is not below any other role."
                    )
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        # Clean up pending setup if guild is removed
        self.pending_setups.pop(guild.id, None)

async def setup(bot):
    await bot.add_cog(Setup(bot))
