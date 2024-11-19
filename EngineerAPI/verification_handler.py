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