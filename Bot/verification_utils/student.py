import discord
import asyncio
import re
import random
import string
from utils.db import db
from utils.email import email_sender
from utils.user_init import add_user
from utils.role_utils import handle_role_change

async def start_student_verification(interaction: discord.Interaction):
    """Initiates the student verification process in DMs."""
    try:
        await interaction.response.send_message("I've sent you a DM to begin the student verification process.", ephemeral=True)
        dm_channel = await interaction.user.create_dm()
        
        privacy_notice = (
            "**Privacy Notice:** The only information that will be stored is your Discord ID and, if you are a student, "
            "the number of years you expect to remain at RPI. No other personal information is stored."
        )
        await dm_channel.send(privacy_notice)

        await dm_channel.send("Please enter your RCSID (e.g., 'turing25').")

        def check_rcsid(m):
            return m.channel == dm_channel and m.author == interaction.user

        rcsid_message = await interaction.client.wait_for('message', check=check_rcsid, timeout=300.0)
        rcsid = rcsid_message.content.strip().lower()

        verification_code = ''.join(random.choices(string.digits, k=6))
        email_address = f"{rcsid}@rpi.edu"
        
        success, message = await email_sender.send_email(
            email_address,
            "RPI Discord Verification Code",
            f"Your verification code is: {verification_code}"
        )

        if not success:
            await dm_channel.send(f"There was an error sending your verification email: {message}")
            return
        await dm_channel.send(f"A verification code has been sent to `{email_address}`. Please enter the 6-digit code below. You have 5 minutes.")

        def check_code(m):
            return m.channel == dm_channel and m.author == interaction.user and m.content.strip().isdigit()

        code_message = await interaction.client.wait_for('message', check=check_code, timeout=300.0)
        entered_code = code_message.content.strip()

        if entered_code != verification_code:
            await dm_channel.send("Incorrect code. Please start the verification process again.")
            return

        await dm_channel.send("Verification successful! How many years do you expect to attend RPI? (Please enter a number from 1 to 8)")

        def check_years(m):
            return m.channel == dm_channel and m.author == interaction.user and m.content.strip().isdigit() and 1 <= int(m.content.strip()) <= 8

        years_message = await interaction.client.wait_for('message', check=check_years, timeout=300.0)
        years_remaining = int(years_message.content.strip())
        
        # --- Role Assignment Logic ---
        settings_records = await db.execute("SELECT * FROM server_settings WHERE guild_id = $1", interaction.guild.id)
        if not settings_records:
            await dm_channel.send("Server settings are not configured. Please contact an administrator.")
            return
        
        settings = settings_records[0]
        student_role = interaction.guild.get_role(settings.get('student_id'))
        if not student_role:
            await dm_channel.send("The Student role could not be found. Please contact an administrator.")
            return

        all_status_roles = {
            'Student': student_role,
            'Alumni': interaction.guild.get_role(settings.get('alumni_id')),
            'Friend': interaction.guild.get_role(settings.get('friend_id')),
            'Verified': interaction.guild.get_role(settings.get('verified_id')),
        }

        await handle_role_change(interaction.guild, interaction.user.id, student_role, all_status_roles)
        await add_user(interaction.user.id, years_remaining)

        await dm_channel.send(f"You have been granted the {student_role.name} role and your previous status roles have been removed. Welcome!")

    except asyncio.TimeoutError:
        await dm_channel.send("You took too long to respond. The verification process has expired. Please try again.")
    except discord.errors.Forbidden:
        # This error is now smarter. It checks if a DM has already been established.
        error_message = ("The bot encountered a permissions error. This is most likely because its role is not high enough "
                         "in the server's role hierarchy to assign the 'Student' role. Please ask an administrator to move the bot's role up.")
        try:
            # If the DM is open, send the error there where the user is looking.
            await dm_channel.send(error_message)
        except (discord.errors.Forbidden, NameError):
            # If we couldn't even open the DM, send it as a followup.
            await interaction.followup.send("I couldn't send you a DM to start the process. Please check your privacy settings and allow DMs from server members.", ephemeral=True)
    except Exception as e:
        print(f"Error in student verification: {e}")
        await dm_channel.send("An unexpected error occurred. Please contact an administrator.")
