import discord
import asyncio
from utils.db import db
from utils.user_init import add_user

async def start_friend_verification(interaction: discord.Interaction):
    """Initiates the friend verification process in DMs."""
    try:
        await interaction.response.send_message("I've sent you a DM to begin the friend verification process.", ephemeral=True)
        dm_channel = await interaction.user.create_dm()

        privacy_notice = (
            "**Privacy Notice:** The only information that will be stored is your Discord ID. "
            "No other personal information is stored."
        )
        await dm_channel.send(privacy_notice)
        
        await dm_channel.send("Please provide the exact Discord username (e.g., `username`, not `username#1234` or a nickname) of a friend who is already a member of this server.")

        def check_username(m):
            return m.channel == dm_channel and m.author == interaction.user

        username_message = await interaction.client.wait_for('message', check=check_username, timeout=300.0)
        friend_username = username_message.content.strip()

        friend_member = discord.utils.get(interaction.guild.members, name=friend_username)

        if not friend_member:
            await dm_channel.send(f"I couldn't find a user with the username `{friend_username}` in this server. Please check the spelling and try again.")
            return

        settings = await db.execute(
            "SELECT student_id, verified_id, alumni_id, friend_id FROM server_settings WHERE guild_id = $1", 
            interaction.guild.id
        )

        if not settings:
            await dm_channel.send("Role information is not configured for this server. Please contact an administrator.")
            return

        valid_role_ids = {
            settings[0]['student_id'],
            settings[0]['verified_id'],
            settings[0]['alumni_id'],
            settings[0]['friend_id']
        }
        
        is_friend_verified = any(role.id in valid_role_ids for role in friend_member.roles)

        if not is_friend_verified:
            await dm_channel.send(f"`{friend_username}` is not a verified member. You must provide the username of a member with a Student, Alumni, Friend, or Verified role.")
            return

        friend_role_id = settings[0]['friend_id']
        if not friend_role_id:
            await dm_channel.send("The Friend role is not configured for this server. Please contact an administrator.")
            return

        friend_role = interaction.guild.get_role(friend_role_id)
        if not friend_role:
            await dm_channel.send("Could not find the Friend role. Please contact an administrator.")
            return

        await interaction.user.add_roles(friend_role)
        await add_user(interaction.user.id, -1)  # -1 for Friend
        await dm_channel.send(f"Verification successful! You have been granted the {friend_role.name} role. Welcome!")

    except asyncio.TimeoutError:
        await dm_channel.send("You took too long to respond. The verification process has expired. Please try again.")
    except discord.errors.Forbidden:
        error_message = ("The bot encountered a permissions error. This could be because it cannot create DMs, or because its role "
                         "is not high enough in the server's role hierarchy to assign the 'Friend' role. Please check your "
                         "privacy settings and ask an administrator to check the bot's role position.")
        try:
            await dm_channel.send(error_message)
        except (discord.errors.Forbidden, NameError):
            await interaction.followup.send("I couldn't send you a DM to start the process. Please check your privacy settings and allow DMs from server members.", ephemeral=True)
    except Exception as e:
        print(f"Error in friend verification: {e}")
        await dm_channel.send("An unexpected error occurred. Please contact an administrator.")
