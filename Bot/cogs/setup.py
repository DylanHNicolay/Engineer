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
            # Engineer is the top role, proceed with setup
            try:
                # Mark the guild as setup=False in the database to indicate setup is complete
                await db.execute('''
                    UPDATE guilds SET setup = FALSE WHERE guild_id = $1
                ''', guild_id)
                
                # Get the engineer channel
                engineer_channel_id = guild_data['engineer_channel_id']
                engineer_channel = guild.get_channel(engineer_channel_id)
                
                # Remove setup commands for this guild
                self.bot.tree.clear_commands(guild=discord.Object(id=guild_id))
                await self.bot.tree.sync(guild=discord.Object(id=guild_id))
                
                # Send a completion message to the user
                await interaction.followup.send("Setup completed successfully! I'm now ready to use.")
                
                # Send a detailed completion message to the engineer channel
                if engineer_channel:
                    await engineer_channel.send(
                        "🎉 **Setup Completed!** 🎉\n\n"
                        "Engineer has been successfully configured for your server.\n\n"
                        "**What happens now?**\n"
                        "- Engineer role will remain at the top of your role hierarchy\n"
                        "- This channel will be maintained for administrative purposes\n"
                        "- Users will be able to verify their affiliation with RPI\n\n"
                        "If you encounter any issues, please contact the developer, Dylan Nicolay through Discord: **nico1ax**"
                    )
            except Exception as e:
                await interaction.followup.send(f"Error completing setup: {e}")
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
