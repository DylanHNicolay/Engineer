import discord
from utils.db import db
from utils.verification import post_verification_message
from utils.user_init import add_user

async def _init_guild_db(guild: discord.Guild):
    """Initializes the guild in the database."""
    await db.execute("INSERT INTO server_settings (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING", guild.id)

async def _create_initial_engineer_channel(guild: discord.Guild):
    """Creates or finds the engineer channel, setting initial bot-only permissions."""
    settings_records = await db.execute("SELECT engineer_channel_id FROM server_settings WHERE guild_id = $1", guild.id)
    engineer_channel = None
    if settings_records and settings_records[0]['engineer_channel_id']:
        engineer_channel = guild.get_channel(settings_records[0]['engineer_channel_id'])
    
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
    guild = engineer_channel.guild
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
    """Creates the public verify channel."""
    verify_channel = await guild.create_text_channel('verify')
    await db.execute("UPDATE server_settings SET verify_channel_id = $1 WHERE guild_id = $2", verify_channel.id, guild.id)
    await engineer_channel.send("Created #verify channel.")


async def _backfill_users(guild: discord.Guild, role_objects: dict, engineer_channel: discord.TextChannel, assign_verified_role=False):
    """
    Backfills the DB. If assign_verified_role is True, grants 'Verified' to users with no role.
    """
    logs = ["**Starting Database Backfill**\n---"]
    
    if not guild.chunked:
        try:
            await guild.chunk(cache=True)
        except discord.errors.ClientException:
            logs.append(f"⚠️ **Warning:** Could not chunk members. Please enable the Server Members Intent.")
    
    logs.append(f"Found `{len(guild.members)}` members in cache.")
    
    existing_users_records = await db.execute("SELECT discord_id FROM users")
    existing_user_ids = {record['discord_id'] for record in existing_users_records}
    logs.append(f"Found `{len(existing_user_ids)}` users in DB.")
    logs.append("---")
    
    backfill_count = 0
    verified_role = role_objects.get('Verified')
    managed_roles = {role for role in role_objects.values() if role is not None}

    for member in guild.members:
        if member.bot or member.id in existing_user_ids:
            continue

        member_has_managed_role = any(role in member.roles for role in managed_roles)

        if not member_has_managed_role:
            if assign_verified_role:
                if verified_role:
                    try:
                        await member.add_roles(verified_role)
                        await add_user(member.id, -2)
                        backfill_count += 1
                        logs.append(f"User `{member.name}` had no role. Granted **Verified**.")
                    except discord.Forbidden:
                        logs.append(f"Could not grant Verified to `{member.name}`. Check permissions.")
                else:
                    logs.append(f"Could not grant Verified to `{member.name}` (role not configured).")
        else:
            if role_objects.get('Student') in member.roles:
                await add_user(member.id, 1)
                logs.append(f"Found existing **Student** `{member.name}` and added to DB.")
                backfill_count += 1
            elif role_objects.get('Alumni') in member.roles:
                await add_user(member.id, 0)
                logs.append(f"Found existing **Alumni** `{member.name}` and added to DB.")
                backfill_count += 1
            elif role_objects.get('Friend') in member.roles:
                await add_user(member.id, -1)
                logs.append(f"Found existing **Friend** `{member.name}` and added to DB.")
                backfill_count += 1
            elif verified_role in member.roles:
                 await add_user(member.id, -2)
                 logs.append(f"Found existing **Verified** user `{member.name}` and added to DB.")
                 backfill_count += 1

    logs.append("---\n**Database backfill complete.**")
    logs.append(f"Processed and added `{backfill_count}` users to the database.")
    
    log_message = "\n".join(logs)
    if len(log_message) > 2000:
        await engineer_channel.send(log_message[:2000])
        await engineer_channel.send(log_message[2000:])
    else:
        await engineer_channel.send(log_message)


async def setup_guild(guild: discord.Guild):
    """
    Sets up the server when the bot joins by calling modular setup functions.
    """
    await _init_guild_db(guild)
    
    engineer_channel = await _create_initial_engineer_channel(guild)
    
    role_objects = await _setup_roles(guild, engineer_channel)
    await _update_engineer_channel_perms(engineer_channel, role_objects)
    
    await _create_verify_channel(guild, engineer_channel)
    await engineer_channel.send("Initial role and channel setup is complete. Run the `/backfill` command to populate the database with existing members. Please ensure that the bot is above the roles you want to backfill.")

    await post_verification_message(guild)
    await engineer_channel.send("Posted initial verification message.")

    await engineer_channel.send("Server setup complete.")
