import discord
import asyncio
import re
import random
import string
from utils.db import db
from utils.email import email_sender
from utils.user_init import add_user

async def start_general_verification(interaction: discord.Interaction):
    """Initiates the general email verification process in DMs."""
    try:
        await interaction.response.send_message("I've sent you a DM to begin the general verification process.", ephemeral=True)
        dm_channel = await interaction.user.create_dm()

        privacy_notice = (
            "**Privacy Notice:** The only information that will be stored is your Discord ID. "
            "No other personal information is stored."
        )
        await dm_channel.send(privacy_notice)

        await dm_channel.send("Please enter your email address.")

        def check_email(m):
            return m.channel == dm_channel and m.author == interaction.user

        email_message = await interaction.client.wait_for('message', check=check_email, timeout=300.0)
        email = email_message.content.strip()

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            await dm_channel.send("That doesn't look like a valid email address. Please start the verification process again.")
            return

        verification_code = ''.join(random.choices(string.digits, k=6))
        
        success, message = await email_sender.send_email(
            email,
            "Discord Verification Code",
            f"Your verification code is: {verification_code}"
        )

        if not success:
            await dm_channel.send(f"There was an error sending your verification email: {message}")
            return

        await dm_channel.send(f"A verification code has been sent to `{email}`. Please enter the 6-digit code below. You have 5 minutes.")

        def check_code(m):
            return m.channel == dm_channel and m.author == interaction.user and m.content.strip().isdigit()

        code_message = await interaction.client.wait_for('message', check=check_code, timeout=300.0)
        entered_code = code_message.content.strip()

        if entered_code != verification_code:
            await dm_channel.send("Incorrect code. Please start the verification process again.")
            return

        settings = await db.execute("SELECT verified_id FROM server_settings WHERE guild_id = $1", interaction.guild.id)
        if not settings or not settings[0]['verified_id']:
            await dm_channel.send("The Verified role is not configured on this server. Please contact an administrator.")
            return
            
        verified_role = interaction.guild.get_role(settings[0]['verified_id'])
        if not verified_role:
            await dm_channel.send("Could not find the Verified role. Please contact an administrator.")
            return

        await interaction.user.add_roles(verified_role)
        await add_user(interaction.user.id, -2)  # -2 for Verified
        await dm_channel.send(f"Verification successful! You have been granted the {verified_role.name} role. Welcome!")

    except asyncio.TimeoutError:
        await dm_channel.send("You took too long to respond. The verification process has expired. Please try again.")
    except discord.errors.Forbidden:
        error_message = ("The bot encountered a permissions error. This could be because it cannot create DMs, or because its role "
                         "is not high enough in the server's role hierarchy to assign the 'Verified' role. Please check your "
                         "privacy settings and ask an administrator to check the bot's role position.")
        try:
            await dm_channel.send(error_message)
        except (discord.errors.Forbidden, NameError):
            await interaction.followup.send("I couldn't send you a DM to start the process. Please check your privacy settings and allow DMs from server members.", ephemeral=True)
    except Exception as e:
        print(f"Error in general verification: {e}")
        await dm_channel.send("An unexpected error occurred. Please contact an administrator.")
