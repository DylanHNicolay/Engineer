import discord
import asyncio
import os
import re
import random
import string
import tempfile
from utils.db import db
from utils.email import email_sender

async def scan_file_local(attachment: discord.Attachment):
    """Scans a file using the local clamscan command-line tool."""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            await attachment.save(tmp_file.name)

            proc = await asyncio.create_subprocess_exec(
                'clamscan', '--no-summary', tmp_file.name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

        os.remove(tmp_file.name)

        if proc.returncode == 0:
            return True, "Clean"
        elif proc.returncode == 1:
            output = stdout.decode().strip()
            virus_name = output.split(': ')[1].replace(' FOUND', '')
            return False, f"Infected with `{virus_name}`"
        else:
            error_details = stderr.decode().strip()
            print(f"Clamscan error (exit code {proc.returncode}): {error_details}")
            return None, "An error occurred during the local file scan."

    except Exception as e:
        print(f"Clamscan execution error: {e}")
        return None, "An unexpected error occurred while scanning the file."


async def start_alumni_verification(interaction: discord.Interaction):
    """Initiates the alumni verification process in DMs."""
    try:
        await interaction.response.send_message("I've sent you a DM to begin the alumni verification process.", ephemeral=True)
        dm_channel = await interaction.user.create_dm()
        
        privacy_notice = (
            "**Privacy Notice:** The only information that will be stored is your Discord ID. "
            "No other personal information is stored."
        )
        await dm_channel.send(privacy_notice)

        # Step 1: Email Verification
        await dm_channel.send("Please enter your personal email address to continue.")

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

        await dm_channel.send("Email verification successful!")

        # Step 2: File Submission
        await dm_channel.send("Please upload an image or PDF as proof of your previous enrollment (e.g., a diploma, transcript, or student ID). You have 30 minutes.")

        def check_attachment(m):
            return m.channel == dm_channel and m.author == interaction.user and m.attachments

        message = await interaction.client.wait_for('message', check=check_attachment, timeout=1800.0)
        attachment = message.attachments[0]

        settings = await db.execute("SELECT verified_id, engineer_channel_id FROM server_settings WHERE guild_id = $1", interaction.guild.id)
        if not settings or not settings[0]['verified_id']:
            await dm_channel.send("The Verified role is not configured on this server. Please contact an administrator.")
            return

        verified_role = interaction.guild.get_role(settings[0]['verified_id'])
        if verified_role:
            await interaction.user.add_roles(verified_role)
            await dm_channel.send(f"Thank you. You've been granted the `{verified_role.name}` role while we review your submission. This may take some time.")
        else:
            await dm_channel.send("Thank you. We will now review your submission. The Verified role could not be found.")

        engineer_channel_id = settings[0]['engineer_channel_id']
        if not engineer_channel_id:
            await dm_channel.send("Could not find the staff channel to forward your submission. Please contact an administrator.")
            return

        engineer_channel = interaction.guild.get_channel(engineer_channel_id)
        if not engineer_channel:
             await dm_channel.send("Could not find the staff channel to forward your submission. Please contact an administrator.")
             return

        await engineer_channel.send(f"New alumni verification submission from {interaction.user.mention} (`{interaction.user.id}`).\nScanning file locally with ClamAV...")
        
        is_clean, result_message = await scan_file_local(attachment)
        
        if is_clean is None:
             await engineer_channel.send(f"**File Scan Error:** {result_message}")
             return

        embed_color = discord.Color.green() if is_clean else discord.Color.red()
        scan_status = "Clean" if is_clean else "Infected"

        embed = discord.Embed(
            title="Alumni Verification Submission",
            description=f"Scanned `{attachment.filename}` submitted by {interaction.user.mention}.",
            color=embed_color
        )
        embed.add_field(name="Local Scan Result", value=f"**Status:** {scan_status}\n**Details:** {result_message}", inline=False)
        
        file_for_forward = await attachment.to_file()
        await engineer_channel.send(embed=embed, file=file_for_forward)
        
        if not is_clean:
            await engineer_channel.send(f"**⚠️ WARNING:** The submitted file is flagged as malicious. **Do not open it.**")

        await engineer_channel.send(f"Admins: Please review the submission. If it is valid, grant the Alumni role to {interaction.user.mention}. If not, remove the Verified role.")

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
        print(f"Error in alumni verification: {e}")
        await dm_channel.send("An unexpected error occurred. Please contact an administrator.")
