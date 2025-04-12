import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.role_channel_utils import is_role_at_top, send_role_setup_error, get_roles_above_engineer
import logging
import time

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    @app_commands.command(name="ping", description="Simple ping command")
    @app_commands.checks.has_permissions(administrator=True)
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")
    
    @app_commands.command(name="setup_cancel", description="Cancels setup, deletes the configured channel, and removes the bot from the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def exit_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        db = self.bot.db_interface
        
        guild_data = await db.get_guild_setup(guild_id)
        
        if guild_data is None:
            await interaction.followup.send("This server is not configured in the database!")
            return
        
        await interaction.followup.send("Setup cancellation in progress. The bot will remove the engineer channel and leave the server.")
        
        engineer_channel_id = guild_data['engineer_channel_id']
        guild = interaction.guild
        
        if engineer_channel_id:
            try:
                channel = guild.get_channel(engineer_channel_id)
                if channel:
                    role_channel_listener = self.bot.get_cog("RoleChannelListener")
                    if role_channel_listener:
                        await role_channel_listener.allow_channel_deletion(engineer_channel_id, 10)
                    await channel.delete(reason="Setup cancelled")
            except discord.Forbidden:
                self.logger.error(f"No permission to delete engineer channel in guild {guild_id}")
            except Exception as e:
                self.logger.error(f"Error deleting channel in guild {guild_id}: {e}")
        
        success = await db.safe_exit(guild_id)
        if not success:
            self.logger.error(f"Failed to clean up database entries for guild {guild_id}")
        
        await asyncio.sleep(1)
        
        try:
            await guild.leave()
        except Exception as e:
            self.logger.error(f"Error leaving guild {guild_id}: {e}")

    async def find_roles_by_name(self, guild: discord.Guild, role_name: str) -> list:
        return [role for role in guild.roles if role.name.lower() == role_name.lower()]
        
    async def create_role(self, guild: discord.Guild, role_name: str, color=None) -> discord.Role:
        try:
            return await guild.create_role(name=role_name, reason="Engineer setup")
        except Exception as e:
            self.logger.error(f"Error creating role {role_name}: {e}")
            raise
            
    async def resolve_duplicate_roles(self, interaction: discord.Interaction, channel: discord.TextChannel, 
                                    roles: list, role_name: str) -> discord.Role:
        select = discord.ui.Select(
            placeholder=f"Choose which {role_name} role to keep",
            options=[
                discord.SelectOption(
                    label=f"{role.name} (ID: {role.id})",
                    description=f"Created: {role.created_at.strftime('%Y-%m-%d')} | Position: {role.position}",
                    value=str(role.id)
                ) for role in roles
            ]
        )
        
        view = discord.ui.View(timeout=300)
        selected_role_id = None
        future = asyncio.get_event_loop().create_future()
        
        async def on_select(select_interaction):
            nonlocal selected_role_id
            selected_role_id = int(select_interaction.data["values"][0])
            await select_interaction.response.send_message(f"Selected {role_name} role with ID {selected_role_id}", ephemeral=True)
            future.set_result(selected_role_id)
            view.stop()

        select.callback = on_select
        view.add_item(select)
        
        await channel.send(
            f"⚠️ **Multiple {role_name} roles found**\n\n"
            f"Please select which {role_name} role to keep. Others will be deleted.",
            view=view
        )
        
        try:
            selected_id = await asyncio.wait_for(future, timeout=300)
            selected_role = next(role for role in roles if role.id == selected_id)
            
            for role in roles:
                if role.id != selected_id:
                    try:
                        await role.delete(reason=f"Duplicate {role_name} role during setup")
                        await channel.send(f"✅ Deleted duplicate {role_name} role (ID: {role.id})")
                    except Exception as e:
                        await channel.send(f"⚠️ Failed to delete duplicate {role_name} role (ID: {role.id}): {str(e)}")
                        self.logger.error(f"Failed to delete duplicate {role_name} role: {e}")
            
            return selected_role
        except asyncio.TimeoutError:
            await channel.send(
                f"⚠️ **Selection timed out**\n\n"
                f"No {role_name} role was selected. Setup cannot continue.\n"
                f"Please run `/setup` again and make a selection."
            )
            return None
            
    async def check_and_create_roles(self, guild: discord.Guild, engineer_channel: discord.TextChannel):
        required_roles = {
            "Verified": {},
            "RPI Admin": {},
            "Student": {},
            "Alumni": {},
            "Friend": {},
            "Prospective Student": {}
        }
        
        role_ids = {}
        
        await engineer_channel.send("🔍 **Checking for required roles...**")
        
        for role_name, settings in required_roles.items():
            existing_roles = await self.find_roles_by_name(guild, role_name)
            
            if len(existing_roles) == 0:
                await engineer_channel.send(f"⚙️ Creating missing role: **{role_name}**")
                try:
                    new_role = await self.create_role(guild, role_name)
                    role_ids[role_name.lower().replace(' ', '_')] = new_role.id
                    await engineer_channel.send(f"✅ Created role: **{role_name}** (ID: {new_role.id})")
                except Exception as e:
                    await engineer_channel.send(f"❌ Failed to create role **{role_name}**: {str(e)}")
                    self.logger.error(f"Failed to create {role_name} role: {e}")
                    return None
            
            elif len(existing_roles) == 1:
                role_ids[role_name.lower().replace(' ', '_')] = existing_roles[0].id
                await engineer_channel.send(f"✅ Found existing role: **{role_name}** (ID: {existing_roles[0].id})")
            
            else:
                await engineer_channel.send(f"⚠️ Found **{len(existing_roles)}** roles named **{role_name}**")
                selected_role = await self.resolve_duplicate_roles(
                    None, engineer_channel, existing_roles, role_name
                )
                
                if selected_role is None:
                    await engineer_channel.send("❌ Setup failed: Role selection timed out")
                    return None
                
                role_ids[role_name.lower().replace(' ', '_')] = selected_role.id
        
        await engineer_channel.send("✅ **All required roles verified**")
        
        await engineer_channel.send("⚙️ **Adjusting role positions...**")
        
        role_order = ["rpi_admin", "student", "alumni", "friend", "prospective_student", "verified"]
        
        roles_to_position = {}
        for role_key in role_order:
            if role_key in role_ids:
                role = guild.get_role(role_ids[role_key])
                if role:
                    roles_to_position[role_key] = role
        
        ordered_roles = [roles_to_position[key] for key in reversed(role_order) if key in roles_to_position]
        
        engineer_role_id = await self.bot.db_interface.get_engineer_role_id(guild.id)
        engineer_role = guild.get_role(engineer_role_id)
        
        if not engineer_role:
            await engineer_channel.send("❌ Cannot position roles: Engineer role not found")
            return role_ids
        
        try:
            for i, role in enumerate(ordered_roles):
                try:
                    new_position = i + 1
                    if role.position != new_position:
                        await role.edit(position=new_position)
                        await engineer_channel.send(f"📊 Positioned role **{role.name}** at level {new_position}")
                        await asyncio.sleep(1)
                except discord.Forbidden:
                    await engineer_channel.send(f"⚠️ Missing permissions to position role **{role.name}**")
                except Exception as e:
                    await engineer_channel.send(f"⚠️ Error positioning role **{role.name}**: {str(e)}")
                    self.logger.error(f"Error positioning role {role.name}: {e}")
        
        except Exception as e:
            await engineer_channel.send(f"⚠️ Error while positioning roles: {str(e)}")
            self.logger.error(f"Error during role positioning: {e}")
        
        await engineer_channel.send("✅ **Role positions adjusted**")
        return role_ids
        
    async def update_database_with_roles(self, guild_id: int, role_ids: dict):
        try:
            column_mapping = {
                "verified": "verified_role_id",
                "rpi_admin": "rpi_admin_role_id",
                "student": "student_role_id",
                "alumni": "alumni_role_id",
                "friend": "friend_role_id",
                "prospective_student": "prospective_student_role_id"
            }
            
            query_parts = []
            values = [guild_id]
            param_index = 2
            
            for role_key, column_name in column_mapping.items():
                if role_key in role_ids:
                    query_parts.append(f"{column_name} = ${param_index}")
                    values.append(role_ids[role_key])
                    param_index += 1
            
            if query_parts:
                query = f"UPDATE guilds SET {', '.join(query_parts)} WHERE guild_id = $1"
                await self.bot.db_interface.execute(query, *values)
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"Error updating database with role IDs: {e}")
            return False

    async def process_guild_members(self, guild: discord.Guild, engineer_channel: discord.TextChannel, role_ids: dict):
        await engineer_channel.send("👥 **Processing guild members...** This may take some time depending on server size.")
        
        db = self.bot.db_interface
        processed_count = 0
        new_users_added = 0
        roles_synced_count = 0
        errors = 0
        start_time = asyncio.get_event_loop().time()

        role_objects = {}
        for key, role_id in role_ids.items():
            role = guild.get_role(role_id)
            if role:
                role_objects[key] = role
            else:
                await engineer_channel.send(f"⚠️ Warning: Could not find role object for {key} (ID: {role_id}) during member processing.")

        db_column_map = {
            "verified": "verified",
            "student": "student",
            "alumni": "alumni",
            "prospective_student": "prospective",
            "friend": "friend",
            "rpi_admin": "rpi_admin"
        }
        
        role_priority = ["rpi_admin", "student", "alumni", "prospective_student", "friend"]

        members = guild.members
        total_members = len([m for m in members if not m.bot])
        await engineer_channel.send(f"Found {total_members} non-bot members to process.")
        last_update_time = time.time()

        for member in members:
            if member.bot:
                continue

            discord_id = member.id
            member_roles_changed = False
            
            try:
                user_record = await db.fetchrow('SELECT * FROM users WHERE discord_id = $1', discord_id)
                
                roles_to_add = []
                roles_to_remove = []
                current_roles_set = set(member.roles)

                if user_record:
                    for role_key, db_column in db_column_map.items():
                        role_object = role_objects.get(role_key)
                        if not role_object: continue

                        has_role_in_db = user_record[db_column]
                        has_role_on_member = role_object in current_roles_set

                        if has_role_in_db and not has_role_on_member:
                            roles_to_add.append(role_object)
                        elif not has_role_in_db and has_role_on_member:
                            roles_to_remove.append(role_object)
                else:
                    new_users_added += 1
                    db_insert_data = {'discord_id': discord_id}
                    primary_role_key_found = None

                    for key in role_priority:
                        role_object = role_objects.get(key)
                        if role_object and role_object in current_roles_set:
                            primary_role_key_found = key
                            break 
                            
                    for key, db_col in db_column_map.items():
                        db_insert_data[db_col] = False

                    if primary_role_key_found:
                        db_insert_data[db_column_map[primary_role_key_found]] = True
                        db_insert_data['verified'] = True
                    else:
                        db_insert_data['verified'] = True

                    verified_role_object = role_objects.get('verified')
                    
                    if db_insert_data['verified'] and verified_role_object and verified_role_object not in current_roles_set:
                         roles_to_add.append(verified_role_object)

                    for role_key, role_object in role_objects.items():
                        if role_key == 'verified': continue
                        
                        should_have_role = db_insert_data.get(db_column_map.get(role_key), False)
                        has_role = role_object in current_roles_set

                        if not should_have_role and has_role:
                            roles_to_remove.append(role_object)

                    columns = ', '.join(db_insert_data.keys())
                    placeholders = ', '.join(f'${i+1}' for i in range(len(db_insert_data)))
                    values = list(db_insert_data.values())
                    
                    insert_query = f'INSERT INTO users ({columns}) VALUES ({placeholders}) ON CONFLICT (discord_id) DO NOTHING'
                    await db.execute(insert_query, *values)

                if roles_to_add:
                    try:
                        await member.add_roles(*roles_to_add, reason="Engineer Setup: Syncing/Adding roles")
                        member_roles_changed = True
                    except discord.Forbidden:
                        self.logger.warning(f"Permission error adding roles to {discord_id} in {guild.id}")
                        errors += 1
                    except discord.HTTPException as e:
                         self.logger.warning(f"HTTP error adding roles to {discord_id} in {guild.id}: {e.status}")
                         errors += 1
                         
                if roles_to_remove:
                    try:
                        await member.remove_roles(*roles_to_remove, reason="Engineer Setup: Syncing/Removing roles")
                        member_roles_changed = True
                    except discord.Forbidden:
                        self.logger.warning(f"Permission error removing roles from {discord_id} in {guild.id}")
                        errors += 1
                    except discord.HTTPException as e:
                         self.logger.warning(f"HTTP error removing roles from {discord_id} in {guild.id}: {e.status}")
                         errors += 1

                if member_roles_changed:
                    roles_synced_count += 1

                await db.execute(
                    'INSERT INTO user_guilds (discord_id, guild_id) VALUES ($1, $2) ON CONFLICT (discord_id, guild_id) DO NOTHING', 
                    discord_id, guild.id
                )

                processed_count += 1
                
                current_time = time.time()
                if current_time - last_update_time >= 15:
                    elapsed_time = current_time - start_time
                    members_per_second = processed_count / elapsed_time if elapsed_time > 0 else 0
                    estimated_remaining = (total_members - processed_count) / members_per_second if members_per_second > 0 else float('inf')
                    eta_str = f"{int(estimated_remaining // 60)}m {int(estimated_remaining % 60)}s" if estimated_remaining != float('inf') else "N/A"
                    
                    await engineer_channel.send(
                        f"⏳ Processed {processed_count}/{total_members} members... "
                        f"(New: {new_users_added}, Synced: {roles_synced_count}, Errors: {errors}) "
                        f"ETA: {eta_str}"
                    )
                    last_update_time = current_time

            except discord.Forbidden:
                errors += 1
                self.logger.warning(f"Permission error processing member {discord_id} in guild {guild.id}. Skipping.")
            except Exception as e:
                errors += 1
                self.logger.error(f"Error processing member {discord_id} in guild {guild.id}: {e}", exc_info=True)
                try:
                    await engineer_channel.send(f"⚠️ Error processing member {member.mention} ({discord_id}). Check logs.", allowed_mentions=discord.AllowedMentions.none())
                except: pass

        await engineer_channel.send(
             f"✅ **Member processing complete.**\n"
             f"- Processed: {processed_count}/{total_members}\n"
             f"- New Users Added: {new_users_added}\n"
             f"- Members with Role Changes: {roles_synced_count}\n"
             f"- Errors: {errors}"
        )

    @app_commands.command(name="setup", description="Begins the setup process")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        guild = interaction.guild
        db = self.bot.db_interface
        
        guild_data = await db.get_guild_setup(guild_id)
        
        if guild_data is None:
            await interaction.followup.send("This server is not configured in the database!")
            return
            
        engineer_role_id = guild_data.get('engineer_role_id')
        
        if engineer_role_id is None:
            await interaction.followup.send("Engineer role not found in the database. Please reinvite the bot.")
            return
            
        engineer_role = guild.get_role(engineer_role_id)
        
        if not engineer_role:
            await interaction.followup.send("Engineer role not found in the server. Please reinvite the bot.")
            return
            
        if is_role_at_top(guild, engineer_role_id):
            engineer_channel_id = guild_data.get('engineer_channel_id')
            engineer_channel = guild.get_channel(engineer_channel_id) if engineer_channel_id else None
            
            if not engineer_channel:
                await interaction.followup.send("Engineer channel not found. Please reinvite the bot.")
                return
                
            await interaction.followup.send("Engineer role position verified. Setting up required roles and processing members...")
            
            await engineer_channel.send(
                "🚀 **Engineer Setup Process Started**\n\n"
                "Setting up required roles..."
            )
            
            role_ids = await self.check_and_create_roles(guild, engineer_channel)
            
            if role_ids is None:
                await interaction.followup.send("Setup failed during role creation/verification. Check the Engineer channel for details.")
                return
                
            await engineer_channel.send("⚙️ **Updating database with role information...**")
            db_updated = await self.update_database_with_roles(guild_id, role_ids)
            
            if not db_updated:
                await engineer_channel.send("⚠️ Warning: Failed to update role information in the database. Member processing might be incomplete.")
            else:
                await engineer_channel.send("✅ Successfully updated role information in the database.")

            await engineer_channel.send(
                f"✋ **Confirmation Required:**\n\n"
                f"Roles have been configured. The next step is to process all **{guild.member_count}** members in the server:\n"
                f"- Existing users in the database will have their roles synced.\n"
                f"- New users will be added to the database and assigned roles based on their current highest priority role (or Verified if none).\n"
                f"- All users will be added to the `user_guilds` table.\n\n"
                f"This process can take time. **{interaction.user.mention}, please type any message in this channel within 5 minutes to proceed.**"
            )

            def check(m):
                return m.channel == engineer_channel and m.author == interaction.user

            try:
                confirmation_msg = await self.bot.wait_for('message', check=check, timeout=300.0)
                await confirmation_msg.add_reaction('👍')
                await engineer_channel.send("✅ Confirmation received. Proceeding with member processing...")
            except asyncio.TimeoutError:
                await engineer_channel.send("❌ **Confirmation timed out.** Member processing cancelled. Run `/setup` again if you wish to complete the process.")
                await interaction.followup.send("Setup cancelled due to confirmation timeout.")
                return

            await self.process_guild_members(guild, engineer_channel, role_ids)

            try:
                await db.execute('UPDATE guilds SET setup = FALSE WHERE guild_id = $1', guild_id)
                
                self.bot.tree.clear_commands(guild=discord.Object(id=guild_id))
                await self.bot.tree.sync(guild=discord.Object(id=guild_id))
                
                await engineer_channel.send(
                    "🎉 **Setup Completed!** 🎉\n\n"
                    "Engineer has been successfully configured for your server.\n\n"
                    "**What happens now?**\n"
                    "- Engineer role will remain at the top of your role hierarchy.\n"
                    "- The following roles are now actively managed: Verified, RPI Admin, Student, Alumni, Friend, and Prospective Student.\n"
                    "- This channel will be maintained for administrative purposes.\n"
                    "- Existing members have been processed: roles synced or added based on current status.\n"
                    "- Users will be able to verify their affiliation with RPI (feature coming soon).\n\n"
                    "If you encounter any issues, please contact the developer, Dylan Nicolay through Discord: **nico1ax**"
                )
                
                self.logger.info(f"Setup completed successfully for guild {guild_id}")
                
            except Exception as e:
                self.logger.error(f"Error completing setup or processing members: {e}", exc_info=True)
                await interaction.followup.send(f"Error during final setup steps: {str(e)}")
                await engineer_channel.send(f"❌ **Setup Error during finalization:** {str(e)}")
        else:
            roles_above = get_roles_above_engineer(guild, engineer_role_id)
            roles_text = ""
            if roles_above:
                roles_text = "\n\nThe following roles need to be moved below Engineer:\n"
                roles_text += "\n".join([f"- {role.name}" for role in roles_above])
                
            await interaction.followup.send(f"Engineer must be the **top level role** in your server. Please move it to the top and try again.{roles_text}")
            
            engineer_channel_id = guild_data.get('engineer_channel_id')
            if engineer_channel_id:
                await send_role_setup_error(guild, engineer_channel_id)
    
async def setup(bot):
    await bot.add_cog(Setup(bot))
