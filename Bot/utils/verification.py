import discord
from discord import app_commands
from utils.db import db
from verification_utils.student import start_student_verification
from verification_utils.alumni import start_alumni_verification
from verification_utils.friend import start_friend_verification
from verification_utils.general import start_general_verification

# This set will act as a lock to prevent users from starting multiple verification processes at once.
VERIFYING_USERS = set()

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        if isinstance(error, app_commands.CommandOnCooldown):
            # Convert remaining seconds into a user-friendly format
            minutes, seconds = divmod(int(error.retry_after), 60)
            await interaction.response.send_message(
                f"This button is on cooldown. Please try again in {minutes}m {seconds}s.",
                ephemeral=True
            )
        else:
            # Handle other errors if necessary
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
            print(error)

    async def _handle_verification(self, interaction: discord.Interaction, verification_function):
        """A wrapper to handle the user verification lock."""
        if interaction.user.id in VERIFYING_USERS:
            await interaction.response.send_message(
                "You already have a verification process active. Please complete or cancel it in your DMs.",
                ephemeral=True
            )
            return
        
        VERIFYING_USERS.add(interaction.user.id)
        try:
            await verification_function(interaction)
        finally:
            # Ensure the user is always removed from the set when the process ends.
            if interaction.user.id in VERIFYING_USERS:
                VERIFYING_USERS.remove(interaction.user.id)

    @discord.ui.button(label="Student", style=discord.ButtonStyle.primary, custom_id="student_verify")
    @app_commands.checks.cooldown(1, 600.0, key=lambda i: i.user.id)
    async def student_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_verification(interaction, start_student_verification)

    @discord.ui.button(label="Alumni", style=discord.ButtonStyle.green, custom_id="alumni_verify")
    @app_commands.checks.cooldown(1, 600.0, key=lambda i: i.user.id)
    async def alumni_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_verification(interaction, start_alumni_verification)

    @discord.ui.button(label="Friend", style=discord.ButtonStyle.secondary, custom_id="friend_verify")
    @app_commands.checks.cooldown(1, 600.0, key=lambda i: i.user.id)
    async def friend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_verification(interaction, start_friend_verification)

    @discord.ui.button(label="General Verification", style=discord.ButtonStyle.secondary, custom_id="general_verify")
    @app_commands.checks.cooldown(1, 600.0, key=lambda i: i.user.id)
    async def verified_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_verification(interaction, start_general_verification)

async def _send_verification_embed(channel: discord.TextChannel):
    """Sends the verification embed and view to a given channel."""
    embed = discord.Embed(
        title="Verification",
        description=(
            "Please select your status below to begin verification:\n\n"
            "🎓 **Student** - Current RPI student\n"
            "🎊 **Alumni** - Former RPI student\n"
            "👥 **Friend** - Friend of an existing member\n"
            "🔍 **General Verification** - Interested in attending RPI"
        ),
        color=discord.Color.blue()
    )
    await channel.send(embed=embed, view=VerificationView())

async def post_verification_message(guild: discord.Guild):
    """Posts the verification message in the guild's verification channel."""
    settings = await db.execute("SELECT verify_channel_id FROM server_settings WHERE guild_id = $1", guild.id)
    if not settings or not settings[0]['verify_channel_id']:
        return

    channel = guild.get_channel(settings[0]['verify_channel_id'])
    if channel:
        await _send_verification_embed(channel)

async def refresh_verification_message(guild: discord.Guild):
    """Clears old verification messages and posts a new one."""
    settings = await db.execute("SELECT verify_channel_id FROM server_settings WHERE guild_id = $1", guild.id)
    if not settings or not settings[0]['verify_channel_id']:
        return

    channel = guild.get_channel(settings[0]['verify_channel_id'])
    if channel:
        async for message in channel.history(limit=100):
            if message.author == guild.me:
                await message.delete()
        await _send_verification_embed(channel)
