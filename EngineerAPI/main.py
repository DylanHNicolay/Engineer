import discord
from discord.ext import commands
from discord.ui import View
import asyncio
from verification import *
from database import *
import os
import datetime
from verification_handler import VerifyStudentButton, FriendVerifyButton, AlumniVerifyButton, ProspectiveVerifyButton  # Import the VerifyStudentButton, FriendVerifyButton, AlumniVerifyButton, and ProspectiveVerifyButton classes
from init_helpers import *

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
    print(f"Logged in as {bot.user}")
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))

    # Initialize user data
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        print("Failed to connect to the database.")
        return

    create_user_info_table(cursor, conn)

    student_role, alumni_role = await initialize_roles(None, guild)

    if student_role is None or alumni_role is None:
        return

    # Close the database connection
    cursor.close()
    conn.close()

    print("User data initialized successfully.")

    # Send Static Verification Message
    channel = guild.get_channel(int(os.getenv("VERIFICATION_CHANNEL_ID")))

    if channel:
        view = View()
        view.add_item(VerifyStudentButton(bot))  # Pass the bot instance
        view.add_item(FriendVerifyButton(bot))  # Add the FriendVerifyButton
        view.add_item(AlumniVerifyButton(bot))  # Add the AlumniVerifyButton
        view.add_item(ProspectiveVerifyButton(bot))  # Add the ProspectiveVerifyButton
        await channel.send("If you are a student, click the button below to start the verification process.", view=view)

@bot.command(name='ping')
async def ping(ctx):
    if ctx.channel.id == CHANNEL:
        await ctx.send('pong!')

@bot.command(name='remove_student_roles')
async def update_year(ctx):
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))
    student_role, alumni_role = await initialize_roles(None, guild)

    if student_role is None or alumni_role is None:
        await ctx.send("Failed to initialize roles.")
        return

    updated_members = await remove_student_roles(guild, student_role, alumni_role)
    await ctx.send(f"Updated roles for {updated_members} member(s).")

bot.run(TOKEN)