import discord
import asyncio
from utils.db import db
from utils.user_init import add_user
from views.friend_confirmation_view import FriendConfirmationView
from utils.role_utils import handle_role_change

async def start_friend_verification(interaction: discord.Interaction):
    """Initiates the friend verification process with confirmation from the friend."""
    try:
        user_dm_channel = await interaction.user.create_dm()
        await interaction.response.send_message("I've sent you a DM to begin the friend verification process.", ephemeral=True)

        privacy_notice = (
            "**Privacy Notice:** The only information that will be stored is your Discord ID. "
            "No other personal information is stored."
        )
        await user_dm_channel.send(privacy_notice)
        
        await user_dm_channel.send("Please provide the exact Discord username (e.g., `username`) of a friend who is already a verified member of this server.")

        def check_username(m):
            return m.channel == user_dm_channel and m.author == interaction.user

        username_message = await interaction.client.wait_for('message', check=check_username, timeout=300.0)
        friend_username = username_message.content.strip()

        friend_member = discord.utils.get(interaction.guild.members, name=friend_username)

        if not friend_member or friend_member.id == interaction.user.id:
            await user_dm_channel.send(f"I couldn't find a valid member with that username. Please check the spelling and try again.")
            return

        settings = await db.execute("SELECT student_id, verified_id, alumni_id, friend_id FROM server_settings WHERE guild_id = $1", interaction.guild.id)
        if not settings:
            await user_dm_channel.send("Role info is not configured. Please contact an admin.")
            return

        valid_role_ids = {settings[0][key] for key in ['student_id', 'verified_id', 'alumni_id', 'friend_id'] if settings[0].get(key)}
        if not any(role.id in valid_role_ids for role in friend_member.roles):
            await user_dm_channel.send(f"`{friend_username}` is not a verified member. Please provide the username of a verified member.")
            return

        await user_dm_channel.send(f"I have found `{friend_username}`. I will now ask for their confirmation. They have 30 minutes to respond.")

        try:
            friend_dm_channel = await friend_member.create_dm()
            confirmation_view = FriendConfirmationView(interaction.user, friend_member)
            await friend_dm_channel.send(
                f"Hello! {interaction.user.mention} has requested to be verified as your friend in the `{interaction.guild.name}` server. "
                "Do you know this person?",
                view=confirmation_view
            )
            
            await confirmation_view.wait() # Wait for the friend to click a button or for the view to time out

            if confirmation_view.result is True:
                friend_role = interaction.guild.get_role(settings[0].get('friend_id'))
                if friend_role:
                    all_status_roles = {
                        'Student': interaction.guild.get_role(settings[0].get('student_id')),
                        'Alumni': interaction.guild.get_role(settings[0].get('alumni_id')),
                        'Friend': friend_role,
                        'Verified': interaction.guild.get_role(settings[0].get('verified_id')),
                    }
                    await handle_role_change(interaction.guild, interaction.user.id, friend_role, all_status_roles)
                    await add_user(interaction.user.id, -1)
                    await user_dm_channel.send(f"`{friend_username}` has confirmed your request! Your previous status roles have been removed and you have been granted the {friend_role.name} role.")
                else:
                    await user_dm_channel.send("Your friend confirmed, but the 'Friend' role is not configured on this server.")
            elif confirmation_view.result is False:
                await user_dm_channel.send(f"Your verification request was denied by `{friend_username}`.")
            else: # Timeout
                await user_dm_channel.send(f"`{friend_username}` did not respond in time. Your verification request has expired.")

        except discord.Forbidden:
            await user_dm_channel.send(f"I could not send a DM to `{friend_username}`. They may have DMs disabled. Please ask them to enable DMs and try again.")
            return

    except asyncio.TimeoutError:
        await user_dm_channel.send("You took too long to respond. The verification process has expired. Please try again.")
    except discord.errors.Forbidden:
        await interaction.followup.send("I couldn't send you a DM to start the process. Please check your privacy settings.", ephemeral=True)
    except Exception as e:
        print(f"Error in friend verification: {e}")
        await user_dm_channel.send("An unexpected error occurred. Please contact an administrator.")
