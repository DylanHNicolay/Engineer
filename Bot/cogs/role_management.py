import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import datetime
import pytz # Required for timezone handling
from typing import Optional

class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.semester_check_loop.start()

    def cog_unload(self):
        self.semester_check_loop.cancel()

    async def get_engineer_channel(self, guild_id: int) -> Optional[discord.TextChannel]:
        """Fetches the engineer channel for a given guild."""
        guild_data = await self.bot.db_interface.get_guild_setup(guild_id)
        if guild_data and guild_data.get('engineer_channel_id'):
            guild = self.bot.get_guild(guild_id)
            if guild:
                channel = guild.get_channel(guild_data['engineer_channel_id'])
                if isinstance(channel, discord.TextChannel):
                    return channel
        self.logger.warning(f"Could not find engineer channel for guild {guild_id}")
        return None

    async def send_admin_notification(self, guild_id: int, message: str):
        """Sends a notification message to the engineer channel."""
        channel = await self.get_engineer_channel(guild_id)
        if channel:
            try:
                # Attempt to mention roles like 'Admin' or 'Moderator' if they exist
                guild = channel.guild
                admin_mentions = []
                for role_name in ["Admin", "Administrator", "Moderator", "RPI Admin"]: # Add relevant admin role names
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        admin_mentions.append(role.mention)

                prefix = f"{' '.join(admin_mentions)} " if admin_mentions else ""
                await channel.send(f"{prefix}{message}", allowed_mentions=discord.AllowedMentions(roles=True))
            except discord.Forbidden:
                self.logger.error(f"Missing permissions to send message in engineer channel for guild {guild_id}")
            except Exception as e:
                self.logger.error(f"Failed to send admin notification to guild {guild_id}: {e}")
        else:
             self.logger.warning(f"Cannot send admin notification: Engineer channel not found for guild {guild_id}")

    # --- Action Methods ---
    async def NewFallAction(self, guild_id: int):
        self.logger.info(f"Executing NewFallAction for guild {guild_id}")
        channel = await self.get_engineer_channel(guild_id)
        if channel:
            try:
                await channel.send("🍂 **New Fall Semester Action Triggered!** (Test Message)")
                # TODO: Implement actual fall semester logic (e.g., decrementing years_remaining)
            except Exception as e:
                self.logger.error(f"Error during NewFallAction for guild {guild_id}: {e}")

    async def NewSpringAction(self, guild_id: int):
        self.logger.info(f"Executing NewSpringAction for guild {guild_id}")
        channel = await self.get_engineer_channel(guild_id)
        if channel:
            try:
                await channel.send("🌸 **New Spring Semester Action Triggered!** (Test Message)")
                # TODO: Implement actual spring semester logic (if any)
            except Exception as e:
                self.logger.error(f"Error during NewSpringAction for guild {guild_id}: {e}")

    # --- Warning Methods ---
    async def FallActionWarning1Month(self, guild_id: int, date: datetime.datetime):
        await self.send_admin_notification(guild_id, f"🍂 Reminder: New Fall Semester action scheduled for {date.strftime('%Y-%m-%d %H:%M %Z')} is approximately 1 month away.")

    async def FallActionWarning1Week(self, guild_id: int, date: datetime.datetime):
        await self.send_admin_notification(guild_id, f"🍂 Reminder: New Fall Semester action scheduled for {date.strftime('%Y-%m-%d %H:%M %Z')} is 1 week away.")

    async def FallActionWarning1Day(self, guild_id: int, date: datetime.datetime):
        await self.send_admin_notification(guild_id, f"🍂 Reminder: New Fall Semester action scheduled for {date.strftime('%Y-%m-%d %H:%M %Z')} is 1 day away.")

    async def SpringActionWarning1Month(self, guild_id: int, date: datetime.datetime):
        await self.send_admin_notification(guild_id, f"🌸 Reminder: New Spring Semester action scheduled for {date.strftime('%Y-%m-%d %H:%M %Z')} is approximately 1 month away.")

    async def SpringActionWarning1Week(self, guild_id: int, date: datetime.datetime):
        await self.send_admin_notification(guild_id, f"🌸 Reminder: New Spring Semester action scheduled for {date.strftime('%Y-%m-%d %H:%M %Z')} is 1 week away.")

    async def SpringActionWarning1Day(self, guild_id: int, date: datetime.datetime):
        await self.send_admin_notification(guild_id, f"🌸 Reminder: New Spring Semester action scheduled for {date.strftime('%Y-%m-%d %H:%M %Z')} is 1 day away.")

    # --- Commands ---
    @app_commands.command(name="set_new_fall_semester", description="Sets the date/time for the fall semester start action.")
    @app_commands.describe(date="Date (YYYY-MM-DD)", time="Time (HH:MM)", timezone="Timezone (e.g., America/New_York)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_new_fall_semester(self, interaction: discord.Interaction, date: str, time: str, timezone: str = "America/New_York"):
        await interaction.response.defer(ephemeral=True)
        try:
            # Validate timezone
            try:
                tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                await interaction.followup.send(f"Invalid timezone '{timezone}'. Please use a valid TZ database name (e.g., America/New_York, UTC).")
                return

            # Parse date and time
            dt_str = f"{date} {time}"
            naive_dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            aware_dt = tz.localize(naive_dt)

            # Validate month
            if aware_dt.month not in [8, 9]: # August or September
                await interaction.followup.send("Invalid month. Fall semester start date must be in August or September.")
                return

            # Store in database (convert to UTC for consistency)
            utc_dt = aware_dt.astimezone(pytz.utc)
            await self.bot.db_interface.execute(
                """
                UPDATE guilds
                SET fall_semester_start = $1,
                    last_fall_action_year = NULL, -- Reset flags when setting a new date
                    fall_warning_1m_sent_year = NULL,
                    fall_warning_1w_sent_year = NULL,
                    fall_warning_1d_sent_year = NULL
                WHERE guild_id = $2
                """,
                utc_dt, interaction.guild_id
            )

            await interaction.followup.send(f"Fall semester start action set to: {aware_dt.strftime('%Y-%m-%d %H:%M %Z')}")
            self.logger.info(f"Fall semester start set to {utc_dt} for guild {interaction.guild_id}")

            # Check if date is in the past
            if aware_dt < datetime.datetime.now(tz):
                self.logger.info(f"Fall semester date {aware_dt} is in the past for guild {interaction.guild_id}. Triggering action now.")
                await self.NewFallAction(interaction.guild_id)
                # Mark action as done for this year
                await self.bot.db_interface.execute(
                    "UPDATE guilds SET last_fall_action_year = $1 WHERE guild_id = $2",
                    aware_dt.year, interaction.guild_id
                )

        except ValueError:
            await interaction.followup.send("Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.")
        except Exception as e:
            self.logger.error(f"Error setting fall semester date for guild {interaction.guild_id}: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="set_new_spring_semester", description="Sets the date/time for the spring semester start action.")
    @app_commands.describe(date="Date (YYYY-MM-DD)", time="Time (HH:MM)", timezone="Timezone (e.g., America/New_York)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_new_spring_semester(self, interaction: discord.Interaction, date: str, time: str, timezone: str = "America/New_York"):
        await interaction.response.defer(ephemeral=True)
        try:
            # Validate timezone
            try:
                tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                await interaction.followup.send(f"Invalid timezone '{timezone}'. Please use a valid TZ database name (e.g., America/New_York, UTC).")
                return

            # Parse date and time
            dt_str = f"{date} {time}"
            naive_dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            aware_dt = tz.localize(naive_dt)

            # Validate month
            if aware_dt.month not in [1, 2]: # January or February
                await interaction.followup.send("Invalid month. Spring semester start date must be in January or February.")
                return

            # Store in database (convert to UTC for consistency)
            utc_dt = aware_dt.astimezone(pytz.utc)
            await self.bot.db_interface.execute(
                """
                UPDATE guilds
                SET spring_semester_start = $1,
                    last_spring_action_year = NULL, -- Reset flags
                    spring_warning_1m_sent_year = NULL,
                    spring_warning_1w_sent_year = NULL,
                    spring_warning_1d_sent_year = NULL
                WHERE guild_id = $2
                """,
                utc_dt, interaction.guild_id
            )

            await interaction.followup.send(f"Spring semester start action set to: {aware_dt.strftime('%Y-%m-%d %H:%M %Z')}")
            self.logger.info(f"Spring semester start set to {utc_dt} for guild {interaction.guild_id}")

            # Check if date is in the past
            if aware_dt < datetime.datetime.now(tz):
                self.logger.info(f"Spring semester date {aware_dt} is in the past for guild {interaction.guild_id}. Triggering action now.")
                await self.NewSpringAction(interaction.guild_id)
                # Mark action as done for this year
                await self.bot.db_interface.execute(
                    "UPDATE guilds SET last_spring_action_year = $1 WHERE guild_id = $2",
                    aware_dt.year, interaction.guild_id
                )

        except ValueError:
            await interaction.followup.send("Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.")
        except Exception as e:
            self.logger.error(f"Error setting spring semester date for guild {interaction.guild_id}: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    # --- Background Task ---
    @tasks.loop(hours=1) # Check every hour
    async def semester_check_loop(self):
        await self.bot.wait_until_ready()
        now_utc = discord.utils.utcnow()
        current_year = now_utc.year
        self.logger.info(f"Running semester check loop at {now_utc}")

        try:
            guilds_data = await self.bot.db_interface.fetch("SELECT * FROM guilds WHERE fall_semester_start IS NOT NULL OR spring_semester_start IS NOT NULL")

            for guild_data in guilds_data:
                guild_id = guild_data['guild_id']
                fall_start: Optional[datetime.datetime] = guild_data['fall_semester_start']
                spring_start: Optional[datetime.datetime] = guild_data['spring_semester_start']

                # --- Fall Semester Checks ---
                if fall_start and fall_start.year >= current_year: # Only process for current or future years set
                    # Check Main Action
                    if now_utc >= fall_start and guild_data['last_fall_action_year'] != fall_start.year:
                        await self.NewFallAction(guild_id)
                        await self.bot.db_interface.execute("UPDATE guilds SET last_fall_action_year = $1 WHERE guild_id = $2", fall_start.year, guild_id)
                    else: # Only check warnings if main action hasn't happened yet
                        # Check 1 Month Warning (approx 30 days)
                        if now_utc >= (fall_start - datetime.timedelta(days=30)) and guild_data['fall_warning_1m_sent_year'] != fall_start.year:
                            await self.FallActionWarning1Month(guild_id, fall_start)
                            await self.bot.db_interface.execute("UPDATE guilds SET fall_warning_1m_sent_year = $1 WHERE guild_id = $2", fall_start.year, guild_id)
                        # Check 1 Week Warning
                        elif now_utc >= (fall_start - datetime.timedelta(weeks=1)) and guild_data['fall_warning_1w_sent_year'] != fall_start.year:
                            await self.FallActionWarning1Week(guild_id, fall_start)
                            await self.bot.db_interface.execute("UPDATE guilds SET fall_warning_1w_sent_year = $1 WHERE guild_id = $2", fall_start.year, guild_id)
                        # Check 1 Day Warning
                        elif now_utc >= (fall_start - datetime.timedelta(days=1)) and guild_data['fall_warning_1d_sent_year'] != fall_start.year:
                            await self.FallActionWarning1Day(guild_id, fall_start)
                            await self.bot.db_interface.execute("UPDATE guilds SET fall_warning_1d_sent_year = $1 WHERE guild_id = $2", fall_start.year, guild_id)

                # --- Spring Semester Checks ---
                if spring_start and spring_start.year >= current_year:
                     # Check Main Action
                    if now_utc >= spring_start and guild_data['last_spring_action_year'] != spring_start.year:
                        await self.NewSpringAction(guild_id)
                        await self.bot.db_interface.execute("UPDATE guilds SET last_spring_action_year = $1 WHERE guild_id = $2", spring_start.year, guild_id)
                    else: # Only check warnings if main action hasn't happened yet
                        # Check 1 Month Warning (approx 30 days)
                        if now_utc >= (spring_start - datetime.timedelta(days=30)) and guild_data['spring_warning_1m_sent_year'] != spring_start.year:
                            await self.SpringActionWarning1Month(guild_id, spring_start)
                            await self.bot.db_interface.execute("UPDATE guilds SET spring_warning_1m_sent_year = $1 WHERE guild_id = $2", spring_start.year, guild_id)
                        # Check 1 Week Warning
                        elif now_utc >= (spring_start - datetime.timedelta(weeks=1)) and guild_data['spring_warning_1w_sent_year'] != spring_start.year:
                            await self.SpringActionWarning1Week(guild_id, spring_start)
                            await self.bot.db_interface.execute("UPDATE guilds SET spring_warning_1w_sent_year = $1 WHERE guild_id = $2", spring_start.year, guild_id)
                        # Check 1 Day Warning
                        elif now_utc >= (spring_start - datetime.timedelta(days=1)) and guild_data['spring_warning_1d_sent_year'] != spring_start.year:
                            await self.SpringActionWarning1Day(guild_id, spring_start)
                            await self.bot.db_interface.execute("UPDATE guilds SET spring_warning_1d_sent_year = $1 WHERE guild_id = $2", spring_start.year, guild_id)

        except Exception as e:
            self.logger.error(f"Error in semester_check_loop: {e}", exc_info=True)

async def setup(bot):
    # Ensure pytz is installed or handle potential import error
    try:
        import pytz
    except ImportError:
        logging.error("RoleManagement cog requires 'pytz'. Please install it (`pip install pytz`).")
        return # Prevent cog loading if dependency is missing

    await bot.add_cog(RoleManagement(bot))
