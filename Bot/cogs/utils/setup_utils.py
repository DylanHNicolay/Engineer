import discord
import asyncio
from typing import Dict, List, Tuple, Optional

REQUIRED_ROLE_NAMES = ["Verified", "RPI Staff", "Student", "Alumni", "Prospective Student", "Friend"]

async def wait_for_owner_message(bot, channel: discord.TextChannel, timeout: int = 300) -> Optional[str]:
    def check(m):
        return m.channel == channel and m.author == channel.guild.owner
    try:
        msg = await bot.wait_for('message', check=check, timeout=timeout)
        return msg.content
    except asyncio.TimeoutError:
        return None

async def categorize_channel_permissions(channel: discord.TextChannel, role: discord.Role) -> str:
    perms = channel.permissions_for(role)
    if not perms.view_channel:
        return "NA"
    elif perms.send_messages:
        return "RW"
    else:
        return "R"

async def format_channel_lists(guild: discord.Guild, role: discord.Role) -> Tuple[List[str], List[str], List[str]]:
    na_channels = []
    read_channels = []
    write_channels = []
    
    for i, channel in enumerate(guild.text_channels, 1):
        perm_type = await categorize_channel_permissions(channel, role)
        channel_entry = f"{i}. {channel.name}"
        
        if perm_type == "NA":
            na_channels.append(channel_entry)
        elif perm_type == "R":
            read_channels.append(channel_entry)
        else:
            write_channels.append(channel_entry)
            
    return na_channels, read_channels, write_channels

async def update_channel_permission(channel: discord.TextChannel, role: discord.Role, perm_type: str):
    if perm_type == "NA":
        await channel.set_permissions(role, view_channel=False)
    elif perm_type == "R":
        await channel.set_permissions(role, view_channel=True, send_messages=False)
    elif perm_type == "RW":
        await channel.set_permissions(role, view_channel=True, send_messages=True)

async def handle_role_check(bot, guild: discord.Guild, setup_channel: discord.TextChannel):
    await setup_channel.send("Verifying required roles...")
    
    role_ids: Dict[str, int] = {}
    existing_roles = {role.name.lower(): role for role in guild.roles}
    potential_conflicts = {}
    missing_roles = []

    # Check existing roles and conflicts
    for required_name in REQUIRED_ROLE_NAMES:
        matches = [r for r in guild.roles if r.name.lower() == required_name.lower()]
        if len(matches) == 0:
            missing_roles.append(required_name)
        elif len(matches) > 1:
            potential_conflicts[required_name] = matches
        else:
            role_ids[required_name] = matches[0].id

    # Handle role conflicts
    if potential_conflicts:
        conflict_msg = "Multiple roles found:\n"
        for role_name, roles in potential_conflicts.items():
            conflict_msg += f"{role_name}:\n"
            for role in roles:
                conflict_msg += f"- ID: {role.id}, Position: {role.position}\n"
        
        await setup_channel.send(f"{conflict_msg}\nPlease specify which role ID to use for each (example: `Verified 123456789`):")
        
        response = await wait_for_owner_message(bot, setup_channel)
        if not response:
            raise Exception("Setup timed out while resolving role conflicts")

        try:
            parts = response.split()
            for i in range(0, len(parts), 2):
                role_name = parts[i]
                role_id = int(parts[i + 1])
                role = guild.get_role(role_id)
                if role:
                    role_ids[role_name] = role_id
        except Exception as e:
            raise Exception(f"Invalid role ID format: {e}")

    # Handle missing roles
    if missing_roles:
        if "Verified" in missing_roles:
            verified_role = await guild.create_role(name="Verified")
            role_ids["Verified"] = verified_role.id
            missing_roles.remove("Verified")
            await setup_channel.send("Created Verified role automatically.")

        if missing_roles:
            await setup_channel.send(
                f"Missing roles: {', '.join(missing_roles)}\n"
                f"Type 'create' to create them automatically, or 'continue' to proceed:"
            )
            
            response = await wait_for_owner_message(bot, setup_channel)
            if response and response.lower() == "create":
                for role_name in missing_roles:
                    new_role = await guild.create_role(name=role_name)
                    role_ids[role_name] = new_role.id

    # Store roles in database
    try:
        await bot.db_manager.update_guild_roles(
            guild.id,
            role_ids.get("Verified", 0),
            role_ids.get("RPI Staff", 0),
            role_ids.get("Student", 0),
            role_ids.get("Alumni", 0),
            role_ids.get("Prospective Student", 0),
            role_ids.get("Friend", 0)
        )
    except Exception as e:
        raise Exception(f"Failed to store role IDs: {e}")

    # Handle channel permissions for each role
    for role_name in REQUIRED_ROLE_NAMES:
        if role_name not in role_ids:
            continue
            
        role = guild.get_role(role_ids[role_name])
        if not role:
            continue

        while True:
            na_channels, read_channels, write_channels = await format_channel_lists(guild, role)
            
            permission_msg = f"**Channel Permissions for {role_name}**\n\n"
            permission_msg += "**No Access:**\n" + "\n".join(na_channels) + "\n\n"
            permission_msg += "**Read Only:**\n" + "\n".join(read_channels) + "\n\n"
            permission_msg += "**Read/Write:**\n" + "\n".join(write_channels) + "\n\n"
            permission_msg += "Type 'accept' to continue or 'change <column> <number> <NA/R/RW>'"
            
            await setup_channel.send(permission_msg)
            
            response = await wait_for_owner_message(bot, setup_channel)
            if not response:
                raise Exception("Setup timed out while configuring permissions")
                
            if response.lower() == "accept":
                break
                
            try:
                _, column, number, perm_type = response.split()
                channel_num = int(number) - 1
                if channel_num < 0 or channel_num >= len(guild.text_channels):
                    await setup_channel.send("Invalid channel number")
                    continue
                    
                channel = guild.text_channels[channel_num]
                await update_channel_permission(channel, role, perm_type.upper())
            except Exception as e:
                await setup_channel.send(f"Invalid format: {e}")

    await setup_channel.send("All roles verified and permissions set. The /user_sync command is now enabled.")
