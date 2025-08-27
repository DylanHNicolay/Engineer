import discord
from typing import Dict

async def handle_role_change(guild: discord.Guild, member_id: int, new_role: discord.Role, all_status_roles: Dict[str, discord.Role]):
    """
    Manages a user's status roles, ensuring they only have one at a time.
    Fetches a fresh member object to ensure roles are up-to-date.
    Removes all other status roles before adding the new one.
    """
    try:
        member = await guild.fetch_member(member_id)
    except discord.NotFound:
        # If the member is no longer in the server, we can't do anything.
        print(f"Could not find member with ID {member_id} in guild {guild.name} to perform role change.")
        return

    roles_to_remove = []
    
    # Create a set of all status role IDs for efficient lookup
    all_status_role_ids = {role.id for role in all_status_roles.values() if role is not None}

    for role in member.roles:
        # If the member has a status role that is not the new one, mark it for removal
        if role.id in all_status_role_ids and role.id != new_role.id:
            roles_to_remove.append(role)
    
    if roles_to_remove:
        await member.remove_roles(*roles_to_remove)
    
    if new_role not in member.roles:
        await member.add_roles(new_role)
