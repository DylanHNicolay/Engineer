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
from year import reduce_years_in_db  # Import the new function
from team import *  # Import the to_pdf function and create_team command

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
    
    # Update all members in the database
    conn, cursor = connect_to_db()
    if conn and cursor:
        update_all_users_data(cursor, conn, guild.members)
        cursor.close()
        conn.close()

    await ctx.send(f"Updated roles for {updated_members} member(s).")

@bot.command(name='year')
async def reduce_years(ctx):
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))
    conn, cursor = connect_to_db()
    if not conn or not cursor:
        await ctx.send("Failed to connect to the database.")
        return

    try:
        await reduce_years_in_db(cursor, conn, guild)
        await ctx.send("Years reduced and roles updated successfully.")
    except Exception as e:
        conn.rollback()
        await ctx.send(f"Error updating years and roles: {e}")
    finally:
        cursor.close()
        conn.close()

@bot.command(name='purge')
@commands.has_permissions(manage_messages=True)
async def purge(ctx, number: int):
    if ctx.channel.id == CHANNEL:
        deleted = await ctx.channel.purge(limit=number)
        await ctx.send(f'Deleted {len(deleted)} message(s)', delete_after=5)

@bot.command(name='export_to_pdf')
async def export_to_pdf(ctx):
    if ctx.channel.id == CHANNEL:
        output_file = "channel_history.pdf"
        await to_pdf(ctx.channel, output_file)
        await ctx.send(file=discord.File(output_file))
        os.remove(output_file)

@bot.command(name='create')
async def create_team(ctx, game_name, team_name, team_members):
    await create_team(ctx, game_name, team_name, team_members)

bot.run(TOKEN)