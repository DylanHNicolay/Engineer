import discord
from discord.ext import commands
from discord.ui import View
import asyncio
from verification import *
from database import *
import os
import datetime
from verification_handler import VerifyStudentButton, FriendVerifyButton, AlumniVerifyButton, ProspectiveVerifyButton  # Import the VerifyStudentButton, FriendVerifyButton, AlumniVerifyButton, and ProspectiveVerifyButton classes
from init_helpers import initialize_roles, update_member_roles
from reactions import *
import re  # Import regex module

TOKEN = os.getenv("DISCORD_KEY")
SERVER = os.getenv("SERVER_ID")
CHANNEL = int(os.getenv("CHANNEL_ID"))

# Define intents
intents = discord.Intents.default()
intents.members = True # Necessary for reading member data
intents.message_content = True  # Necessary for reading message content

# Create an instance of Bot with a command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Establish a global database connection
conn, cursor = connect_to_db()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))

    # Initialize user data and update roles
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
        view.add_item(FriendVerifyButton(bot))  # Add the FriendVerifyButton
        view.add_item(AlumniVerifyButton(bot))  # Add the AlumniVerifyButton
        view.add_item(ProspectiveVerifyButton(bot))  # Add the ProspectiveVerifyButton
        await channel.send("If you are a student, click the button below to start the verification process.", view=view)

@bot.command(name='ping')
async def ping(ctx):
    if ctx.channel.id == CHANNEL:
        await ctx.send('pong!')

@bot.command(name='addrole')
@commands.has_permissions(administrator=True)
async def addrole(ctx):
    reaction_cog = bot.get_cog('ReactionRoles')
    if reaction_cog is None:
        await ctx.send("ReactionRoles cog is not loaded.")
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter the name of the new role:")
    role_msg = await bot.wait_for('message', check=check)
    role_name = role_msg.content.strip()

    await ctx.send("Enter the emoji for this role (send the emoji itself or the name of a custom emoji):")
    emoji_msg = await bot.wait_for('message', check=check)
    emoji_input = emoji_msg.content.strip()

    guild = ctx.guild

    # Create the role if it doesn't exist
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        role = await guild.create_role(name=role_name)

    # Process the emoji input
    # If input is in the form '<:name:id>', parse it to get the name
    custom_emoji_match = re.match(r'<a?:(\w+):(\d+)>', emoji_input)
    if custom_emoji_match:
        emoji_name = custom_emoji_match.group(1)
        emoji_id = int(custom_emoji_match.group(2))
        emoji_identifier = emoji_name
        # Optionally verify that the emoji exists
        custom_emoji = discord.utils.get(await guild.fetch_emojis(), id=emoji_id)
        if not custom_emoji:
            await ctx.send("Invalid custom emoji.")
            return
    else:
        # Assume it's a standard emoji character
        emoji_identifier = emoji_input

    # Update role_emojis mapping
    reaction_cog.role_emojis[role_name] = emoji_identifier
    reaction_cog.save_role_emojis()

    # Update the reaction role message
    await reaction_cog.update_reaction_message()
    await ctx.send(f"Role '{role_name}' has been added with emoji {emoji_input}.")

@bot.command(name='removerole')
@commands.has_permissions(administrator=True)
async def removerole(ctx):
    reaction_cog = bot.get_cog('ReactionRoles')
    if reaction_cog is None:
        await ctx.send("ReactionRoles cog is not loaded.")
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("Enter the name of the role to remove:")
    role_msg = await bot.wait_for('message', check=check)
    role_name = role_msg.content.strip()

    guild = ctx.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await role.delete()
        reaction_cog.role_emojis.pop(role_name, None)
        reaction_cog.save_role_emojis()
        await reaction_cog.update_reaction_message()
        await ctx.send(f"Role '{role_name}' has been removed.")
    else:
        await ctx.send(f"No role named '{role_name}' found.")

async def main():
    async with bot:
        await bot.load_extension('reactions')  # Load the ReactionRoles cog
        await bot.load_extension('elections')  # Load the Elections cog
        await bot.start(TOKEN)

asyncio.run(main())

# Ensure the database connection is closed on shutdown
@bot.event
async def on_close():
    if cursor:
        cursor.close()
    if conn:
        conn.close()