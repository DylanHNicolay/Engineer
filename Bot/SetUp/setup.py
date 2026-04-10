import discord
from utils.db import db
from utils.verification import post_verification_message

async def _init_guild_db(guild: discord.Guild):
    """Initializes the guild in the database."""
    await db.execute("INSERT INTO server_settings (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING", guild.id)

async def _create_initial_engineer_channel(guild: discord.Guild):
    """Creates or finds the engineer channel, setting initial bot-only permissions."""
    settings_records = await db.execute("SELECT engineer_channel_id FROM server_settings WHERE guild_id = $1", guild.id)
    engineer_channel = None
    if settings_records and settings_records[0]['engineer_channel_id']:
        engineer_channel = guild.get_channel(settings_records[0]['engineer_channel_id'])
        await engineer_channel.edit(name = 'engineer')
    
    if not engineer_channel:
        engineer_channel = discord.utils.get(guild.text_channels, name='engineer')

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    if engineer_channel:
        await engineer_channel.edit(overwrites=overwrites)
        await engineer_channel.send("Found existing engineer channel. Resetting permissions and using for setup logs.")
    else:
        engineer_channel = await guild.create_text_channel('engineer', overwrites=overwrites)
        await engineer_channel.send("This channel will be used for setup logs and leadership communication.")

    await db.execute("UPDATE server_settings SET engineer_channel_id = $1 WHERE guild_id = $2", engineer_channel.id, guild.id)
    return engineer_channel

async def _setup_roles(guild: discord.Guild, log_channel: discord.TextChannel):
    """Sets up roles for the guild, creating them if they don't exist."""
    role_names = ['Co-President', 'Representative', 'Student', 'Alumni', 'Friend', 'Verified']
    role_columns = {
        'Co-President': 'co_president_id',
        'Representative': 'representative_id',
        'Student': 'student_id',
        'Alumni': 'alumni_id',
        'Friend': 'friend_id',
        'Verified': 'verified_id'
    }
    role_objects = {}

    for name in role_names:
        found_roles = [role for role in guild.roles if role.name == name]
        role = None
        if not found_roles:
            role = await guild.create_role(name=name)
            await log_channel.send(f"Created role: {name}")
        elif len(found_roles) == 1:
            role = found_roles[0]
            await log_channel.send(f"Found role: {name}")
        else:
            role_mentions = ", ".join([r.mention for r in found_roles])
            await log_channel.send(f"Warning: Found duplicate roles for '{name}': {role_mentions}. Please resolve this manually.")
        
        if role:
            role_objects[name] = role
            await db.execute(f"UPDATE server_settings SET {role_columns[name]} = $1 WHERE guild_id = $2", role.id, guild.id)
    return role_objects

async def _update_engineer_channel_perms(engineer_channel: discord.TextChannel, role_objects: dict):
    """Updates the engineer channel with permissions for leadership roles."""
    co_president_role = role_objects.get('Co-President')
    representative_role = role_objects.get('Representative')

    overwrites = engineer_channel.overwrites
    
    if co_president_role:
        overwrites[co_president_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if representative_role:
        overwrites[representative_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    await engineer_channel.edit(overwrites=overwrites)
    await engineer_channel.send("Channel permissions have been updated for leadership roles.")

async def _create_verify_channel(guild: discord.Guild, engineer_channel: discord.TextChannel):
    """Creates or finds the verfiy channel."""
    settings_records = await db.execute("SELECT verify_channel_id FROM server_settings WHERE guild_id = $1", guild.id)
    verify_channel = None

    # Check if verify channel exists, if not create it
    if settings_records and settings_records[0]['verify_channel_id']:
        verify_channel = guild.get_channel(settings_records[0]['verify_channel_id'])
        await verify_channel.edit(name = 'verify')

    
    # Check the guild channels directly
    if not verify_channel:
        verify_channel = discord.utils.get(guild.text_channels, name='verify')

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    if verify_channel:
        #Clear the channel if it already exists to ensure a clean slate for verification
        async for message in verify_channel.history(limit=None):
            await message.delete()
            
        await verify_channel.edit(overwrites=overwrites)
        await engineer_channel.send("Found existing #verify channel. Using for verification.")
    else:
        verify_channel = await guild.create_text_channel('verify', overwrites=overwrites)
        await engineer_channel.send("Created #verify channel.")

    await db.execute("UPDATE server_settings SET verify_channel_id = $1 WHERE guild_id = $2", verify_channel.id, guild.id)
    return verify_channel

async def _update_verify_channel_perms(verify_channel: discord.TextChannel, role_objects: dict):
    """Updates the verify channel with permissions for leadership roles."""
    co_president_role = role_objects.get('Co-President')
    representative_role = role_objects.get('Representative')

    overwrites = verify_channel.overwrites
    
    if co_president_role:
        overwrites[co_president_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if representative_role:
        overwrites[representative_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    await verify_channel.edit(overwrites=overwrites)
    await verify_channel.send("Channel permissions have been updated for leadership roles.")

async def setup_guild(guild: discord.Guild):
    """
    Sets up the server when the bot joins by calling modular setup functions.
    """
    await _init_guild_db(guild)
    
    engineer_channel = await _create_initial_engineer_channel(guild)
    
    role_objects = await _setup_roles(guild, engineer_channel)
    await _update_engineer_channel_perms(engineer_channel, role_objects)
    
    verify_channel = await _create_verify_channel(guild, engineer_channel)
    await _update_verify_channel_perms(verify_channel, role_objects)

    await engineer_channel.send("Initial role and channel setup is complete. Run the `/backfill` command to populate the database with existing members. Please ensure that the bot is above the roles you want to backfill.")

    await post_verification_message(guild)
    await engineer_channel.send("Posted initial verification message.")
    
    await engineer_channel.send("Server setup complete.")
