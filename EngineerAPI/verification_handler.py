import discord
from discord.ui import Button
import asyncio
from verification import generate_verification_code, update_user_info, verify_code_and_update_user, update_verification_status, handle_verification_timeout
from database import connect_to_db, update_user_data  # Import the unified function
from email_utils import *

class VerifyStudentButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Student Verification", style=discord.ButtonStyle.primary)
        self.bot = bot  # Store the bot instance

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        await user.send("Hello! Please reply with your RCSID to start the verification process.")
        await interaction.response.send_message("A DM has been sent to you. Please check your DMs!", ephemeral=True)

        connection, cursor = None, None

        try:
            rcsid = await self.get_rcsid(user)
            connection, cursor = connect_to_db()
            if not connection or not cursor:
                await user.send("Failed to connect to the database. Please try again later.")
                return

            update_user_data(cursor, connection, user, rcsid)
            verification_code = generate_verification_code()
            discord_id, discord_username, discord_server_username = str(user.id), str(user), str(user.display_name)

            status = update_user_info(cursor, rcsid, discord_id, discord_username, discord_server_username, verification_code)
            await self.handle_verification_status(user, status, rcsid, verification_code)

            connection.commit()

            if not send_verification_email(rcsid, verification_code):
                await user.send("Failed to send the verification email. Please try again later.")
                return

            entered_code = await self.get_verification_code(user)
            result = verify_code_and_update_user(cursor, discord_id, entered_code)

            if result:
                await self.complete_verification(user, interaction, cursor, connection, result[0])
            else:
                handle_verification_timeout(cursor, discord_id)
                await user.send("The verification code is incorrect. Please request a new verification code using the verification button.")

        except asyncio.TimeoutError:
            handle_verification_timeout(cursor, discord_id)
            connection.commit()
            await user.send("Your verification time has expired. Please request a new verification code using the verification button.")
        except Exception as error:
            await user.send("An error occurred during verification. Please try again later.")
            print(f"Error: {error}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    async def get_rcsid(self, user):
        def rcsid_check(m):
            return m.author == user and m.channel == user.dm_channel
        rcsid_msg = await self.bot.wait_for('message', check=rcsid_check, timeout=900)
        return rcsid_msg.content.strip()

    async def handle_verification_status(self, user, status, rcsid, verification_code):
        if status == "already_verified":
            await user.send("You are already verified.")
        else:
            await user.send(f"Please reply with the 6-digit verification code sent to {rcsid}\@rpi.edu (check your spam). You have 5 minutes to complete the verification.")
        
    async def get_verification_code(self, user):
        def code_check(m):
            return m.author == user and m.channel == user.dm_channel and m.content.isdigit() and len(m.content) == 6
        code_msg = await self.bot.wait_for('message', check=code_check, timeout=300)
        return int(code_msg.content)

    async def complete_verification(self, user, interaction, cursor, connection, rcsid):
        await user.send("Verification successful! How many years do you have remaining at RPI (between 1 and 8)? Please reply with a number between 1 and 8.")
        years_remaining = await self.get_years_remaining(user)
        update_verification_status(cursor, rcsid, years_remaining)
        connection.commit()
        await user.send("You have been successfully verified and your information has been updated.")
        await self.assign_student_role(user, interaction)
        handle_verification_timeout(cursor, str(user.id))

    async def get_years_remaining(self, user):
        def years_check(m):
            return m.author == user and m.channel == user.dm_channel and m.content.isdigit() and 1 <= int(m.content) <= 8
        years_msg = await self.bot.wait_for('message', check=years_check, timeout=300)
        return int(years_msg.content)

    async def assign_student_role(self, user, interaction):
        guild = interaction.guild
        student_role = discord.utils.get(guild.roles, name="Student")
        alumni_role = discord.utils.get(guild.roles, name="Alumni")
        if student_role is None:
            student_role = await guild.create_role(name="Student")
        member = guild.get_member(user.id)
        if member:
            if alumni_role and alumni_role in member.roles:
                await member.remove_roles(alumni_role, reason="User verified as a Student")
            await member.add_roles(student_role)
            await user.send("The 'Student' role has been assigned to you.")

class FriendVerifyButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Friend Verification", style=discord.ButtonStyle.secondary)
        self.bot = bot  # Store the bot instance

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        await user.send("Please reply with your friend's Discord user ID (the numbers). You can find it by right-clicking their profile and selecting 'Copy ID' (make sure Developer Mode is enabled).")
        await interaction.response.send_message("A DM has been sent to you. Please check your DMs!", ephemeral=True)

        def id_check(m):
            return m.author == user and m.channel == user.dm_channel and m.content.isdigit()

        try:
            # Wait for the user to provide their friend's Discord user ID
            friend_msg = await self.bot.wait_for('message', check=id_check, timeout=300)
            friend_id = int(friend_msg.content.strip())

            try:
                # Fetch the friend's user object using the Discord user ID
                friend = await self.bot.fetch_user(friend_id)

                if not friend:
                    await user.send("The user could not be found. Please ensure you provided the correct Discord user ID.")
                    return

                # DM the friend for verification
                try:
                    await friend.send(
                        f"Hello! {user.display_name} has requested that you verify them in the RPI Esports server.\n"
                        "If you confirm that you know them, please reply with 'yes'. Otherwise, please reply 'no'."
                    )

                    await user.send(f"A verification request has been sent to {friend.display_name}.")

                    def friend_response_check(m):
                        return m.author == friend and m.channel == friend.dm_channel and m.content.lower() in ['yes', 'no']

                    # Wait for the friend's response
                    response_msg = await self.bot.wait_for('message', check=friend_response_check, timeout=86400)

                    if response_msg.content.lower() == 'yes':
                        # Verification successful
                        friend_role = discord.utils.get(interaction.guild.roles, name="Friend")

                        if friend_role is None:
                            friend_role = await interaction.guild.create_role(name="Friend")

                        member = interaction.guild.get_member(user.id)
                        if member:
                            await member.add_roles(friend_role)
                            await user.send("You have been verified!")
                            await friend.send("Thank you for verifying your friend!")
                    else:
                        # Verification denied
                        await user.send("Your friend did not verify you. Please try another verification method.")
                        await friend.send("You chose not to verify your friend.")

                except discord.Forbidden:
                    await user.send(f"Could not send a DM to {friend.display_name}. Please ask them to allow DMs from server members.")
                except Exception as e:
                    await user.send("An error occurred while sending a verification request to your friend. Please try again later.")
                    print(f"Error DMing friend: {e}")

            except discord.NotFound:
                await user.send("The specified user ID could not be found.")
            except discord.HTTPException as e:
                await user.send("An error occurred while fetching the user. Please try again later.")
                print(f"Error fetching user by ID: {e}")

        except asyncio.TimeoutError:
            await user.send("Verification request timed out. Please try again.")
        except Exception as error:
            await user.send("An error occurred during the friend verification process. Please try again later.")
            print(f"Error: {error}")

class AlumniVerifyButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Alumni Verification", style=discord.ButtonStyle.success)
        self.bot = bot  # Store the bot instance

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild
        await interaction.response.send_message("A DM has been sent to you. Please check your DMs!", ephemeral=True)

        # Check if the "temp" role exists, if not, create it
        temp_role = discord.utils.get(guild.roles, name="temp")
        if temp_role is None:
            temp_role = await guild.create_role(name="temp", reason="Temporary role for Alumni Verification")

        # Assign the "temp" role to the user
        member = guild.get_member(user.id)
        if member:
            try:
                await member.add_roles(temp_role, reason="Alumni Verification: Assigned temporary role")
                await user.send("Please go to the **#modmail** channel and provide additional information for alumni verification.")
                print(f"Assigned 'temp' role to {user.display_name}.")
            except discord.Forbidden:
                await user.send("I do not have permission to assign the temporary role. Please contact an administrator.")
                return
            except Exception as e:
                await user.send("An error occurred while assigning the temporary role. Please try again later.")
                print(f"Error assigning 'temp' role: {e}")
                return

        # Ensure the modmail channel exists and set permissions
        modmail_channel = discord.utils.get(guild.text_channels, name="modmail")
        if modmail_channel is None:
            # Create the modmail channel if it doesn't exist
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                temp_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            try:
                modmail_channel = await guild.create_text_channel("modmail", overwrites=overwrites)
                await user.send("A private modmail channel has been created. You can now access it for alumni verification.")
                print("Created 'modmail' text channel with permissions.")
            except Exception as e:
                await user.send("An error occurred while creating the modmail channel. Please contact an administrator.")
                print(f"Error creating 'modmail' channel: {e}")
                return
        else:
            # Update permissions for the "temp" role in the existing modmail channel
            await modmail_channel.set_permissions(temp_role, read_messages=True, send_messages=True)

        # Retrieve the roles by name
        co_president_role = discord.utils.get(guild.roles, name="Co-President")
        secretary_role = discord.utils.get(guild.roles, name="Secretary")
        treasurer_role = discord.utils.get(guild.roles, name="Treasurer")
        representative_role = discord.utils.get(guild.roles, name="Representative")

        # Construct the ping message
        role_mentions = []
        if co_president_role:
            role_mentions.append(co_president_role.mention)
        if secretary_role:
            role_mentions.append(secretary_role.mention)
        if treasurer_role:
            role_mentions.append(treasurer_role.mention)
        if representative_role:
            role_mentions.append(representative_role.mention)

        if role_mentions:
            mention_message = f"{', '.join(role_mentions)}: {user.mention} needs Alumni verification."
            try:
                await modmail_channel.send(mention_message)
                print("Successfully pinged the roles for Alumni verification.")
            except Exception as e:
                await user.send("An error occurred while notifying the admins. Please contact an administrator.")
                print(f"Error sending ping message in modmail channel: {e}")

class ProspectiveVerifyButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Prospective Student Verification", style=discord.ButtonStyle.secondary)
        self.bot = bot  # Store the bot instance

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild
        await interaction.response.send_message("A DM has been sent to you. Please check your DMs!", ephemeral=True)

        # Prompt the user to provide their full email address
        await user.send("Hello! Please reply with your full email address (e.g., example@example.com) to receive a verification code.")

        def email_check(m):
            return m.author == user and m.channel == user.dm_channel and "@" in m.content and "." in m.content

        try:
            # Wait for the user to provide their email address
            email_msg = await self.bot.wait_for('message', check=email_check, timeout=300)
            email = email_msg.content.strip()

            # Generate a verification code
            verification_code = generate_verification_code()

            # Send the verification email
            if not send_verification_email(email, verification_code, 0):
                await user.send("Failed to send the verification email. Please try again later.")
                return

            await user.send("A verification code has been sent to your email. Please reply with the 6-digit code. You have 5 minutes to complete the verification.")

            def code_check(m):
                return m.author == user and m.channel == user.dm_channel and m.content.isdigit() and len(m.content) == 6

            try:
                # Wait for the user to enter the verification code
                code_msg = await self.bot.wait_for('message', check=code_check, timeout=300)
                entered_code = int(code_msg.content)

                if entered_code == verification_code:
                    # Verification successful
                    prospective_role = discord.utils.get(guild.roles, name="Prospective Student")

                    if prospective_role is None:
                        prospective_role = await guild.create_role(name="Prospective Student")

                    member = guild.get_member(user.id)
                    if member:
                        await member.add_roles(prospective_role)
                        await user.send("You have been successfully verified as a Prospective Student!")
                else:
                    # Incorrect verification code
                    await user.send("The verification code is incorrect. Please try the verification process again.")

            except asyncio.TimeoutError:
                await user.send("Your verification time has expired. Please try the verification process again.")

        except Exception as error:
            await user.send("An error occurred during the prospective student verification process. Please try again later.")
            print(f"Error: {error}")