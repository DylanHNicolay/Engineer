import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.role_channel_utils import is_role_at_top, send_role_setup_error, get_roles_above_engineer
import logging

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
        # Defer response in case this takes a while
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        db = self.bot.db_interface
        
        # Get guild data
        guild_data = await db.get_guild_setup(guild_id)
        
        if guild_data is None:
            await interaction.followup.send("This server is not configured in the database!")
            return
        
        # Send the response immediately before potentially long operations
        await interaction.followup.send("Setup cancellation in progress. The bot will remove the engineer channel and leave the server.")
        
        # Get the engineer channel
        engineer_channel_id = guild_data['engineer_channel_id']
        
        # Store a reference to the guild before any operations that might affect our access
        guild = interaction.guild
        
        # Try to delete the channel
        if engineer_channel_id:
            try:
                channel = guild.get_channel(engineer_channel_id)
                if channel:
                    # Allow the channel to be deleted by telling the listener to ignore it
                    role_channel_listener = self.bot.get_cog("RoleChannelListener")
                    if role_channel_listener:
                        # Allow deletion for 10 seconds
                        await role_channel_listener.allow_channel_deletion(engineer_channel_id, 10)
                    
                    # Now proceed with deleting the channel
                    await channel.delete(reason="Setup cancelled")
            except discord.Forbidden:
                self.logger.error(f"No permission to delete engineer channel in guild {guild_id}")
            except Exception as e:
                self.logger.error(f"Error deleting channel in guild {guild_id}: {e}")
        
        # Use safe_exit to remove guild data from the database
        success = await db.safe_exit(guild_id)
        if not success:
            self.logger.error(f"Failed to clean up database entries for guild {guild_id}")
        
        # Wait a short time to ensure database operations complete
        await asyncio.sleep(1)
        
        try:
            # Leave the guild
            await guild.leave()
        except Exception as e:
            self.logger.error(f"Error leaving guild {guild_id}: {e}")

    async def find_roles_by_name(self, guild: discord.Guild, role_name: str) -> list:
        """Find all roles with a given name in the guild"""
        return [role for role in guild.roles if role.name.lower() == role_name.lower()]
        
    async def create_role(self, guild: discord.Guild, role_name: str, color=None) -> discord.Role:
        """Create a role with the given name"""
        try:
            # Ignoring color parameter to create colorless roles
            return await guild.create_role(name=role_name, reason="Engineer setup")
        except Exception as e:
            self.logger.error(f"Error creating role {role_name}: {e}")
            raise
            
    async def resolve_duplicate_roles(self, interaction: discord.Interaction, channel: discord.TextChannel, 
                                    roles: list, role_name: str) -> discord.Role:
        """Ask admin which duplicate role to keep and delete others"""
        # Create a select menu with the duplicate roles
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
        
        # Create a view with the select menu
        view = discord.ui.View(timeout=300)  # 5 minute timeout
        selected_role_id = None
        
        # Future to store the result
        future = asyncio.get_event_loop().create_future()
        
        async def on_select(select_interaction):
            nonlocal selected_role_id
            selected_role_id = int(select_interaction.data["values"][0])
            await select_interaction.response.send_message(f"Selected {role_name} role with ID {selected_role_id}", ephemeral=True)
            future.set_result(selected_role_id)
            view.stop()

        select.callback = on_select
        view.add_item(select)
        
        # Send the message with the view
        await channel.send(
            f"⚠️ **Multiple {role_name} roles found**\n\n"
            f"Please select which {role_name} role to keep. Others will be deleted.",
            view=view
        )
        
        try:
            # Wait for a selection or timeout
            selected_id = await asyncio.wait_for(future, timeout=300)
            
            # Get the selected role
            selected_role = next(role for role in roles if role.id == selected_id)
            
            # Delete other roles
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
        """Check for all required roles and create missing ones"""
        # Define required roles without colors (per updated requirements)
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
            # Find existing roles with this name
            existing_roles = await self.find_roles_by_name(guild, role_name)
            
            if len(existing_roles) == 0:
                # Role doesn't exist, create it
                await engineer_channel.send(f"⚙️ Creating missing role: **{role_name}**")
                try:
                    # Create role without color specification
                    new_role = await self.create_role(guild, role_name)
                    role_ids[role_name.lower().replace(' ', '_')] = new_role.id
                    await engineer_channel.send(f"✅ Created role: **{role_name}** (ID: {new_role.id})")
                except Exception as e:
                    await engineer_channel.send(f"❌ Failed to create role **{role_name}**: {str(e)}")
                    self.logger.error(f"Failed to create {role_name} role: {e}")
                    return None
            
            elif len(existing_roles) == 1:
                # Only one role exists, use it
                role_ids[role_name.lower().replace(' ', '_')] = existing_roles[0].id
                await engineer_channel.send(f"✅ Found existing role: **{role_name}** (ID: {existing_roles[0].id})")
            
            else:
                # Multiple roles with the same name
                await engineer_channel.send(f"⚠️ Found **{len(existing_roles)}** roles named **{role_name}**")
                
                # Ask admin which role to keep
                selected_role = await self.resolve_duplicate_roles(
                    None, engineer_channel, existing_roles, role_name
                )
                
                if selected_role is None:
                    # Admin didn't select a role in time
                    await engineer_channel.send("❌ Setup failed: Role selection timed out")
                    return None
                
                role_ids[role_name.lower().replace(' ', '_')] = selected_role.id
        
        await engineer_channel.send("✅ **All required roles verified**")
        
        # Now adjust the role positions to ensure proper order
        await engineer_channel.send("⚙️ **Adjusting role positions...**")
        
        # Desired order from highest to lowest
        role_order = ["rpi_admin", "student", "alumni", "friend", "prospective_student", "verified"]
        
        # Collect all role objects
        roles_to_position = {}
        for role_key in role_order:
            if role_key in role_ids:
                role = guild.get_role(role_ids[role_key])
                if role:
                    roles_to_position[role_key] = role
        
        # Sort them in reverse order (since we'll position them from bottom to top)
        ordered_roles = [roles_to_position[key] for key in reversed(role_order) if key in roles_to_position]
        
        # Calculate the position where we should start placing our roles
        # Find the highest position available below the Engineer role
        engineer_role_id = await self.bot.db_interface.get_engineer_role_id(guild.id)
        engineer_role = guild.get_role(engineer_role_id)
        
        if not engineer_role:
            await engineer_channel.send("❌ Cannot position roles: Engineer role not found")
            return role_ids
        
        try:
            # Position each role one by one, from bottom to top
            for i, role in enumerate(ordered_roles):
                try:
                    # Calculate position - position them below the Engineer role
                    # First role should be at position 1, next at 2, etc.
                    new_position = i + 1
                    
                    # Only move if the position is different
                    if role.position != new_position:
                        await role.edit(position=new_position)
                        await engineer_channel.send(f"📊 Positioned role **{role.name}** at level {new_position}")
                        
                        # Add a small delay to prevent rate limiting
                        await asyncio.sleep(1)
                except discord.Forbidden:
                    await engineer_channel.send(f"⚠️ Missing permissions to position role **{role.name}**")
                except Exception as e:
                    await engineer_channel.send(f"⚠️ Error positioning role **{role.name}**: {str(e)}")
                    self.logger.error(f"Error positioning role {role.name}: {e}")
        
        except Exception as e:
            await engineer_channel.send(f"⚠️ Error while positioning roles: {str(e)}")
            self.logger.error(f"Error during role positioning: {e}")
        
        # Final confirmation
        await engineer_channel.send("✅ **Role positions adjusted**")
        return role_ids
        
    async def update_database_with_roles(self, guild_id: int, role_ids: dict):
        """Update the database with role IDs"""
        try:
            # Map the role names to database column names
            column_mapping = {
                "verified": "verified_role_id",
                "rpi_admin": "rpi_admin_role_id",
                "student": "student_role_id",
                "alumni": "alumni_role_id",
                "friend": "friend_role_id",
                "prospective_student": "prospective_student_role_id"
            }
            
            # Build the SQL update statement
            query_parts = []
            values = [guild_id]
            param_index = 2  # Start with $2 since $1 is guild_id
            
            for role_key, column_name in column_mapping.items():
                if role_key in role_ids:
                    query_parts.append(f"{column_name} = ${param_index}")
                    values.append(role_ids[role_key])
                    param_index += 1
            
            # Update the database if we have roles to update
            if query_parts:
                query = f"UPDATE guilds SET {', '.join(query_parts)} WHERE guild_id = $1"
                await self.bot.db_interface.execute(query, *values)
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"Error updating database with role IDs: {e}")
            return False
    
    @app_commands.command(name="setup", description="Begins the setup process")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction):
        # Defer the response while we check things
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild_id
        guild = interaction.guild
        db = self.bot.db_interface
        
        # Get guild data to find the engineer role ID
        guild_data = await db.get_guild_setup(guild_id)
        
        if guild_data is None:
            await interaction.followup.send("This server is not configured in the database!")
            return
            
        # Get the engineer role ID
        engineer_role_id = guild_data['engineer_role_id']
        
        if engineer_role_id is None:
            await interaction.followup.send("Engineer role not found in the database. Please reinvite the bot.")
            return
            
        # Get the actual role object
        engineer_role = guild.get_role(engineer_role_id)
        
        if not engineer_role:
            await interaction.followup.send("Engineer role not found in the server. Please reinvite the bot.")
            return
            
        # Check if Engineer role is at the top using the utility function
        if is_role_at_top(guild, engineer_role_id):
            # Engineer is the top role, proceed with setting up other roles
            
            # Get the engineer channel
            engineer_channel_id = guild_data['engineer_channel_id']
            engineer_channel = guild.get_channel(engineer_channel_id)
            
            if not engineer_channel:
                await interaction.followup.send("Engineer channel not found. Please reinvite the bot.")
                return
                
            await interaction.followup.send("Engineer role position verified. Setting up required roles...")
            
            await engineer_channel.send(
                "🚀 **Engineer Setup Process Started**\n\n"
                "Setting up all required roles for the server. This process may take a few minutes."
            )
            
            # Check for required roles and create missing ones
            role_ids = await self.check_and_create_roles(guild, engineer_channel)
            
            if role_ids is None:
                # Something went wrong during role setup
                await interaction.followup.send("Setup failed during role creation. Check the Engineer channel for details.")
                return
                
            # Update the database with role IDs
            await engineer_channel.send("⚙️ **Updating database with role information...**")
            db_updated = await self.update_database_with_roles(guild_id, role_ids)
            
            if not db_updated:
                await engineer_channel.send("⚠️ Warning: Failed to update some role information in the database")
            else:
                await engineer_channel.send("✅ Successfully updated role information in the database")
                
            # Mark the guild as setup=False in the database to indicate setup is complete
            try:
                await db.execute('''
                    UPDATE guilds SET setup = FALSE WHERE guild_id = $1
                ''', guild_id)
                
                # Remove setup commands for this guild
                self.bot.tree.clear_commands(guild=discord.Object(id=guild_id))
                await self.bot.tree.sync(guild=discord.Object(id=guild_id))
                
                # Send a completion message
                await engineer_channel.send(
                    "🎉 **Setup Completed!** 🎉\n\n"
                    "Engineer has been successfully configured for your server.\n\n"
                    "**What happens now?**\n"
                    "- Engineer role will remain at the top of your role hierarchy\n"
                    "- The following roles are now actively managed: Verified, RPI Admin, Student, Alumni, Friend, and Prospective Student\n"
                    "- This channel will be maintained for administrative purposes\n"
                    "- Users will be able to verify their affiliation with RPI\n\n"
                    "If you encounter any issues, please contact the developer, Dylan Nicolay through Discord: **nico1ax**"
                )
                
                # Log completion
                self.logger.info(f"Setup completed successfully for guild {guild_id}")
                
                # Let the admin know setup is done
                await interaction.followup.send("Setup completed successfully! All roles have been configured.")
            except Exception as e:
                self.logger.error(f"Error completing setup: {e}")
                await interaction.followup.send(f"Error during final setup steps: {str(e)}")
                await engineer_channel.send(f"❌ **Setup Error:** {str(e)}")
        else:
            # Engineer is not the top role
            roles_above = get_roles_above_engineer(guild, engineer_role_id)
            roles_text = ""
            if roles_above:
                roles_text = "\n\nThe following roles need to be moved below Engineer:\n"
                roles_text += "\n".join([f"- {role.name}" for role in roles_above])
                
            await interaction.followup.send(f"Engineer must be the **top level role** in your server. Please move it to the top and try again.{roles_text}")
            
            # If we have a channel_id in the database, send a detailed message there
            if 'engineer_channel_id' in guild_data and guild_data['engineer_channel_id']:
                # Use the utility function to send the setup error message
                await send_role_setup_error(guild, guild_data['engineer_channel_id'])
    
async def setup(bot):
    await bot.add_cog(Setup(bot))
