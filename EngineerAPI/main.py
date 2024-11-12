import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from verification import *
from database import *
import os

TOKEN = os.getenv("DISCORD_KEY")
SERVER = os.getenv("SERVER_ID")
CHANNEL = int(os.getenv("CHANNEL_ID"))

# Define intents
intents = discord.Intents.default()
intents.members = True # Necessary for reading member data
intents.message_content = True  # Necessary for reading message content

# Create an instance of Bot with a command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}')

@bot.command(name='ping')
async def ping(ctx):
    if ctx.channel.id == CHANNEL:
        await ctx.send('pong!')

@bot.command(name='init')
async def init(ctx):
    await ctx.send(f"Initializing user data... Logged in as {bot.user}")
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        await ctx.send("Failed to connect to the database.")
        return

    create_user_info_table(cursor, conn)
    for guild in bot.guilds:
        await ctx.send(f"Initializing data for server: {guild.name} (ID: {guild.id})")
        insert_user_data(cursor, conn, guild.members)

    # Close the connection
    cursor.close()
    conn.close()
    await ctx.send("User data initialized successfully.")

# Verification Command with Button
@bot.command(name='verify')
async def verify(ctx):
    """
    Discord command to verify a student. Sends a message with a button for the user to click.
    """

    # Define the button for the verification process
    class VerifyButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Start Verification", style=discord.ButtonStyle.primary)

        async def callback(self, interaction: discord.Interaction):
            user = interaction.user
            await user.send("Hello! Please reply with your RCSID to start the verification process.")
            await interaction.response.send_message("A DM has been sent to you. Please check your DMs!", ephemeral=True)

            def rcsid_check(m):
                return m.author == user and m.channel == user.dm_channel

            try:
                # Wait for the user to provide their RCSID
                rcsid_msg = await bot.wait_for('message', check=rcsid_check, timeout=900)
                rcsid = rcsid_msg.content.strip()

                connection = connect_to_db_verification()
                cursor = connection.cursor()

                verification_code = generate_verification_code()
                discord_id = str(user.id)
                discord_username = str(user)
                discord_server_username = str(user.display_name)

                status = upsert_user_info(cursor, rcsid, discord_id, discord_username, discord_server_username, verification_code)

                if status == "already_verified":
                    await user.send("You are already verified.")
                    return
                elif status == "updated":
                    await user.send("Your verification code has been updated. Please check your email.")
                elif status == "inserted":
                    await user.send(f"A verification code has been generated for {rcsid}. Please check your email.")

                connection.commit()

                # Send the verification email
                if not send_verification_email(rcsid, verification_code):
                    await user.send("Failed to send the verification email. Please try again later.")
                    return

                await user.send("Please reply with the 6-digit verification code sent to your email. You have 5 minutes to complete the verification.")

                def code_check(m):
                    return m.author == user and m.channel == user.dm_channel and m.content.isdigit() and len(m.content) == 6

                try:
                    # Wait for the user to enter the verification code
                    code_msg = await bot.wait_for('message', check=code_check, timeout=300)
                    entered_code = int(code_msg.content)

                    result = verify_code_and_update_user(cursor, discord_id, entered_code)

                    if result:
                        rcsid = result[0]
                        await user.send("Verification successful! How many years do you have remaining at RPI (between 1 and 8)? Please reply with a number between 1 and 8.")

                        def years_check(m):
                            return m.author == user and m.channel == user.dm_channel and m.content.isdigit() and 1 <= int(m.content) <= 8

                        years_msg = await bot.wait_for('message', check=years_check, timeout=300)
                        years_remaining = int(years_msg.content)

                        update_verification_status(cursor, rcsid, years_remaining)
                        connection.commit()

                        await user.send("You have been successfully verified and your information has been updated.")

                        # Apply the "Student" role if it exists, otherwise create and apply it
                        guild = ctx.guild
                        student_role = discord.utils.get(guild.roles, name="Student")
                        if student_role is None:
                            student_role = await guild.create_role(name="Student")

                        member = guild.get_member(user.id)
                        if member:
                            await member.add_roles(student_role)
                            await user.send("The 'Student' role has been assigned to you.")

                        # Remove the verification code from the database
                        handle_verification_timeout(cursor, discord_id)

                    else:
                        await user.send("The verification code is incorrect. Please request a new verification code using the !verify command.")

                except asyncio.TimeoutError:
                    handle_verification_timeout(cursor, discord_id)
                    connection.commit()
                    await user.send("Your verification time has expired. Please request a new verification code using the !verify command.")

            except Exception as error:
                await user.send("An error occurred during verification. Please try again later.")
                print(f"Error: {error}")

            finally:
                if connection:
                    cursor.close()
                    connection.close()

    # Create the view with the button
    view = View()
    view.add_item(VerifyButton())

    # Send the message with the button
    await ctx.send("Click the button below to start the verification process.", view=view)


bot.run(TOKEN)