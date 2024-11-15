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
    await ctx.send(f"Initializing user data and updating roles... Logged in as {bot.user}")
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        await ctx.send("Failed to connect to the database.")
        return

    create_user_info_table(cursor, conn)

    guild = ctx.guild
    student_role = discord.utils.get(guild.roles, name="Student")
    alumni_role = discord.utils.get(guild.roles, name="Alumni")

    if student_role is None:
        await ctx.send("The 'Student' role does not exist.")
        return
    if alumni_role is None:
        # Create the "Alumni" role if it doesn't exist
        alumni_role = await guild.create_role(name="Alumni")
        await ctx.send("The 'Alumni' role was created.")

    updated_members = 0

    for member in guild.members:
        if student_role in member.roles:
            try:
                # Remove the "Student" role and add the "Alumni" role
                await member.remove_roles(student_role, reason="Reverification required: Moving from Student to Alumni")
                await member.add_roles(alumni_role, reason="Reverification required: Assigned Alumni role")

                # DM the user for reverification
                await member.send(
                    "Hello, please reverify your student status in the RPI Esports Discord Server.\n"
                    "Click the verification button in the server channel to begin."
                    "https://discord.gg/8tzMdZxBh4"
                )

                updated_members += 1
            except discord.Forbidden:
                await ctx.send(f"Permission error: Could not update roles for {member.display_name}.")
            except Exception as e:
                await ctx.send(f"An error occurred while updating {member.display_name}: {e}")

    # Close the database connection
    cursor.close()
    conn.close()

    await ctx.send(f"User data initialized successfully. Updated roles for {updated_members} member(s).")


# Channel ID for the static verification message (set this to your desired channel ID)
VERIFICATION_CHANNEL_ID = int(os.getenv("VERIFICATION_CHANNEL_ID"))

# Verification Button Class
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
                await user.send("Your verification code has been updated. Please reply with the 6-digit verification code sent to your email (check your spam). You have 5 minutes to complete the verification.")
            elif status == "inserted":
                await user.send(f"A verification code has been generated for {rcsid}. Please check your email. Please reply with the 6-digit verification code sent to your email (check your spam). You have 5 minutes to complete the verification.")

            connection.commit()

            # Send the verification email
            if not send_verification_email(rcsid, verification_code):
                await user.send("Failed to send the verification email. Please try again later.")
                return

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

                    # Remove the verification code from the database
                    handle_verification_timeout(cursor, discord_id)

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
            if connection:
                cursor.close()
                connection.close()

# Send Static Verification Message on Startup
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))
    channel = guild.get_channel(VERIFICATION_CHANNEL_ID)

    if channel:
        view = View()
        view.add_item(VerifyButton())
        await channel.send("Welcome to the server! Click the button below to start the verification process.", view=view)

# Send Static Verification Message When Bot Joins a New Guild
@bot.event
async def on_guild_join(guild):
    channel = guild.get_channel(VERIFICATION_CHANNEL_ID)

    if channel:
        view = View()
        view.add_item(VerifyButton())
        await channel.send("Welcome to the server! Click the button below to start the verification process.", view=view)


bot.run(TOKEN)