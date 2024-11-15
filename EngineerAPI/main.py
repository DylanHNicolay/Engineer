import discord
from discord.ext import commands
from discord.ui import View
import asyncio
from verification import *
from database import *
import os
import datetime
from verification_handler import VerifyStudentButton  # Import the VerifyStudentButton class
from init_helpers import initialize_roles, update_member_roles

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

    # Initialize user data and update roles
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        print("Failed to connect to the database.")
        return

    create_user_info_table(cursor, conn)

    student_role, alumni_role = await initialize_roles(None, guild)

    if student_role is None or alumni_role is None:
        return
    
    updated_members = await update_member_roles(guild, student_role, alumni_role)

    # Close the database connection
    cursor.close()
    conn.close()

    print(f"User data initialized successfully. Updated roles for {updated_members} member(s).")

    # Send Static Verification Message
    channel = guild.get_channel(int(os.getenv("VERIFICATION_CHANNEL_ID")))

    if channel:
        view = View()
        view.add_item(VerifyStudentButton(bot))  # Pass the bot instance
        await channel.send("If you are a student, click the button below to start the verification process.", view=view)

@bot.command(name='ping')
async def ping(ctx):
    if ctx.channel.id == CHANNEL:
        await ctx.send('pong!')

bot.run(TOKEN)