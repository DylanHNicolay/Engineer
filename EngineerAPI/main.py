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
@commands.has_permissions(administrator=True)
async def init(ctx):
    await ctx.send(f"Initializing user data and updating roles... Logged in as {bot.user}")
    conn, cursor = connect_to_db()
    if not (conn and cursor):
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
                await member.remove_roles(student_role, reason="Reverification: Moving from Student to Alumni")
                await member.add_roles(alumni_role, reason="Reverification required: Assigned Alumni role")

                # DM the user for reverification
                await member.send(
                    "Hello, please reverify your student status in the RPI Esports Discord Server.\n"
                    "Click the verification button in the server channel to begin."
                    "(https://discord.gg/8tzMdZxBh4)"
                )

                updated_members += 1
            except discord.Forbidden:
                await ctx.send(f"Permission error: Could not update roles for {member.display_name}.")
            except Exception as e:
                await ctx.send(f"An error occurred while updating {member.display_name}: {e}")

    # Close the database connection
    await ctx.send(f"User data initialized successfully. Updated roles for {updated_members} members.")

    if cursor:
        cursor.close()
    if conn:
        conn.close()


# Channel ID for the static verification message (set this to your desired channel ID)
VERIFICATION_CHANNEL_ID = int(os.getenv("VERIFICATION_CHANNEL_ID"))

# Student Verification Button Class
class StudentVerifyButton(discord.ui.Button):
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

# Friend Verification Button Class
class FriendVerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Friend Verification", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        await user.send("Please reply with your friend's Discord user ID (the numbers). You can find it by right-clicking their profile and selecting 'Copy ID' (make sure Developer Mode is enabled).")
        await interaction.response.send_message("A DM has been sent to you. Please check your DMs!", ephemeral=True)

        def id_check(m):
            return m.author == user and m.channel == user.dm_channel and m.content.isdigit()

        try:
            # Wait for the user to provide their friend's Discord user ID
            friend_msg = await bot.wait_for('message', check=id_check, timeout=300)
            friend_id = int(friend_msg.content.strip())

            try:
                # Fetch the friend's user object using the Discord user ID
                friend = await bot.fetch_user(friend_id)

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
                    response_msg = await bot.wait_for('message', check=friend_response_check, timeout=86400)

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
            
# Alumni Verification Button Class
class AlumniVerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Alumni Verification", style=discord.ButtonStyle.success)

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
            except Exception as e:
                await user.send("An error occurred while assigning the temporary role. Please try again later.")
                print(f"Error assigning 'temp' role: {e}")

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
        else:
            # Update permissions for the "temp" role in the existing modmail channel
            await modmail_channel.set_permissions(temp_role, read_messages=True, send_messages=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))
    channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
    
    # Delete previous messages sent by the bot
    try:
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
    except Exception as e:
        print(f"Error deleting previous messages: {e}")

    if channel:
        view = View()
        view.add_item(StudentVerifyButton())
        view.add_item(FriendVerifyButton())
        view.add_item(AlumniVerifyButton())
        await channel.send("Welcome to the server! Click the button that applies to you.\n", view=view)

@bot.event
async def on_guild_join(guild):
    channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
    
    # Delete previous messages sent by the bot
    try:
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
    except Exception as e:
        print(f"Error deleting previous messages: {e}")

    if channel:
        view = View()
        view.add_item(StudentVerifyButton())
        view.add_item(FriendVerifyButton())
        view.add_item(AlumniVerifyButton())
        await channel.send("Welcome to the server! Click the button that applies to you.\n", view=view)
        
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command. Only administrators can use `!init`.")

bot.run(TOKEN)