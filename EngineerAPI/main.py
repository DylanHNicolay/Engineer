import discord
from discord.ext import commands
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

@bot.command(name='verify')
async def verify(ctx, rcsid: str = None):
    """
    Discord command to verify a student and create an entry in the user_info table.
    Arguments:
    - rcsid: The RCSID of the student.
    """
    if rcsid is None:
        await ctx.send('Please provide your RCSID. Usage: `!verify <RCSID>`')
        return

    try:
        connection = connect_to_db_verification()
        cursor = connection.cursor()

        verification_code = generate_verification_code()
        discord_id = str(ctx.author.id)
        discord_username = str(ctx.author)
        discord_server_username = str(ctx.author.display_name)

        status = upsert_user_info(cursor, rcsid, discord_id, discord_username, discord_server_username, verification_code)

        if status == "already_verified":
            await ctx.send(f'You are already verified.')
            return
        elif status == "updated":
            await ctx.send(f'Your verification code has been updated. Please check your email for further instructions.')
        elif status == "inserted":
            await ctx.send(f'A verification code has been generated for {rcsid}. Please check your email for further instructions.')

        connection.commit()

        if not send_verification_email(rcsid, verification_code):
            await ctx.send('Failed to send the verification email. Please try again later.')
            return

        # Send DM to user to request verification code
        await ctx.author.send('Please reply with the 6-digit verification code sent to your email. You have 15 minutes to complete the verification.')

        def code_check(m):
            return m.author == ctx.author and m.channel == ctx.author.dm_channel and m.content.isdigit() and len(m.content) == 6

        try:
            code_msg = await bot.wait_for('message', check=code_check, timeout=900)  # Wait for up to 15 minutes (900 seconds)
            entered_code = int(code_msg.content)

            result = verify_code_and_update_user(cursor, discord_id, entered_code)

            if result:
                rcsid = result[0]
                await ctx.author.send('Verification successful! How many years do you have remaining at RPI (between 1 and 8)? Please reply with a number between 1 and 8.')

                def years_check(m):
                    return m.author == ctx.author and m.channel == ctx.author.dm_channel and m.content.isdigit() and 1 <= int(m.content) <= 8

                years_msg = await bot.wait_for('message', check=years_check, timeout=900)  # Wait for up to 15 minutes
                years_remaining = int(years_msg.content)

                update_verification_status(cursor, rcsid, years_remaining)
                connection.commit()

                await ctx.author.send('You have been successfully verified and your information has been updated.')

                # Apply the "Student" role if it exists, otherwise create and apply it
                guild = ctx.guild
                student_role = discord.utils.get(guild.roles, name="Student")
                if student_role is None:
                    student_role = await guild.create_role(name="Student")

                await ctx.author.add_roles(student_role)

            else:
                await ctx.author.send('The verification code is incorrect. Please request a new verification code using the !verify_student command.')
        except asyncio.TimeoutError:
            handle_verification_timeout(cursor, discord_id)
            connection.commit()
            await ctx.author.send('Your verification time has expired. Please request a new verification code using the !verify_student command.')

    except (Exception, psycopg2.Error) as error:
        await ctx.send('An error occurred while trying to verify the student. Please try again later.')
        print(f'Error: {error}')

    finally:
        if connection:
            cursor.close()
            connection.close()


bot.run(TOKEN)