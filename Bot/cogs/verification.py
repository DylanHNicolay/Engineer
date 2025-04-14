"""Verification cog for Engineer bot"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from typing import Optional
import time
from utils.verification_utils import (
    start_student_verification,
    start_prospective_verification,
    verify_code,
    update_verification_status
)
from utils.role_channel_utils import is_role_at_top

class VerificationButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, custom_id: str):
        super().__init__(label=label, style=style, custom_id=f"verify_{custom_id}")

class StudentVerifyButton(VerificationButton):
    def __init__(self):
        super().__init__("Student", discord.ButtonStyle.primary, "student")
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Please check your DMs for verification instructions.", 
            ephemeral=True
        )
        
        try:
            await interaction.user.send(
                "To verify as a student, please enter your RPI RCS ID (e.g., `smithj4`).\n"
                "You will receive a verification code at your @rpi.edu email."
            )
            
            # Wait for RCS ID
            def check(m):
                return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)
                
            try:
                msg = await interaction.client.wait_for('message', check=check, timeout=300)
                rcsid = msg.content.strip().lower()
                
                # Start verification process
                success, message = await start_student_verification(
                    interaction.client.db_interface,
                    interaction.user.id,
                    rcsid
                )
                
                await interaction.user.send(message)
                if success:
                    await self.handle_verification_code(interaction, "student")
                    
            except asyncio.TimeoutError:
                await interaction.user.send("Verification timed out. Please try again.")
                
        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't send you a DM. Please enable DMs from server members and try again.",
                ephemeral=True
            )
    
    async def handle_verification_code(self, interaction: discord.Interaction, verification_type: str):
        """Handle verification code entry and processing"""
        def check(m):
            return (
                m.author == interaction.user 
                and isinstance(m.channel, discord.DMChannel)
                and m.content.isdigit() 
                and len(m.content) == 6
            )
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=300)
            entered_code = int(msg.content)
            
            success, message, confirmed_type = await verify_code(
                interaction.client.db_interface,
                interaction.user.id,
                entered_code
            )
            
            await interaction.user.send(message)
            
            if success and confirmed_type == "student":
                await interaction.user.send(
                    "How many years do you have remaining at RPI?\n"
                    "Please enter a number between 1 and 8."
                )
                
                def years_check(m):
                    return (
                        m.author == interaction.user 
                        and isinstance(m.channel, discord.DMChannel)
                        and m.content.isdigit() 
                        and 1 <= int(m.content) <= 8
                    )
                
                msg = await interaction.client.wait_for('message', check=years_check, timeout=300)
                years = int(msg.content)
                
                # Update verification status and assign role
                if await update_verification_status(
                    interaction.client.db_interface,
                    interaction.user.id,
                    interaction.guild_id,
                    "student",
                    years
                ):
                    # Assign the student role
                    guild_data = await interaction.client.db_interface.get_guild_setup(interaction.guild_id)
                    if guild_data and guild_data.get('student_role_id'):
                        guild = interaction.guild
                        member = guild.get_member(interaction.user.id)
                        if member:
                            student_role = guild.get_role(guild_data['student_role_id'])
                            verified_role = guild.get_role(guild_data['verified_role_id'])
                            if student_role and verified_role:
                                await member.add_roles(student_role, verified_role, 
                                                     reason="Verified as RPI student")
                                await interaction.user.send("✅ You have been verified as a student!")
                                return
                                
                await interaction.user.send("❌ There was an error assigning your roles. Please contact an administrator.")
                
        except asyncio.TimeoutError:
            await interaction.user.send("Verification timed out. Please try again.")

class FriendVerifyButton(VerificationButton):
    def __init__(self):
        super().__init__("Friend", discord.ButtonStyle.secondary, "friend")
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Please check your DMs for verification instructions.",
            ephemeral=True
        )
        
        try:
            await interaction.user.send(
                "To verify as a friend, please provide the username of an existing server member who can vouch for you.\n"
                "They will receive a DM asking them to confirm that they know you."
            )
            
            def check(m):
                return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)
                
            try:
                msg = await interaction.client.wait_for('message', check=check, timeout=300)
                friend_name = msg.content.strip()
                
                # Find the friend in the server
                guild = interaction.guild
                friend = discord.utils.get(guild.members, name=friend_name)
                
                if not friend:
                    await interaction.user.send(
                        "❌ Could not find that user in the server. Please make sure you entered their exact username."
                    )
                    return
                    
                if friend.bot:
                    await interaction.user.send("❌ You cannot be verified by a bot.")
                    return
                    
                try:
                    await friend.send(
                        f"👋 Hello! {interaction.user.name} has requested verification in {guild.name} and listed you as a friend.\n"
                        f"Do you know this person and can vouch for them? (yes/no)"
                    )
                    
                    def friend_check(m):
                        return (
                            m.author == friend 
                            and isinstance(m.channel, discord.DMChannel)
                            and m.content.lower() in ['yes', 'no']
                        )
                    
                    friend_response = await interaction.client.wait_for('message', 
                                                                      check=friend_check, 
                                                                      timeout=86400)  # 24 hours
                    
                    if friend_response.content.lower() == 'yes':
                        # Update verification status and assign role
                        if await update_verification_status(
                            interaction.client.db_interface,
                            interaction.user.id,
                            interaction.guild_id,
                            "friend"
                        ):
                            # Assign the friend role
                            guild_data = await interaction.client.db_interface.get_guild_setup(interaction.guild_id)
                            if guild_data and guild_data.get('friend_role_id'):
                                member = guild.get_member(interaction.user.id)
                                if member:
                                    friend_role = guild.get_role(guild_data['friend_role_id'])
                                    verified_role = guild.get_role(guild_data['verified_role_id'])
                                    if friend_role and verified_role:
                                        await member.add_roles(friend_role, verified_role,
                                                            reason=f"Verified as friend by {friend.name}")
                                        await interaction.user.send("✅ You have been verified as a friend!")
                                        await friend.send(f"✅ Thank you! {interaction.user.name} has been verified.")
                                        return
                                        
                        await interaction.user.send("❌ There was an error assigning your roles. Please contact an administrator.")
                    else:
                        await interaction.user.send("❌ The user did not verify you as a friend. Please try another verification method.")
                        await friend.send("You have declined to verify the user.")
                        
                except discord.Forbidden:
                    await interaction.user.send(
                        "❌ I couldn't send a message to that user. They may have DMs disabled."
                    )
                    
            except asyncio.TimeoutError:
                await interaction.user.send("Verification timed out. Please try again.")
                
        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't send you a DM. Please enable DMs from server members and try again.",
                ephemeral=True
            )

class AlumniVerifyButton(VerificationButton):
    def __init__(self):
        super().__init__("Alumni", discord.ButtonStyle.success, "alumni")
        
    async def callback(self, interaction: discord.Interaction):
        guild_data = await interaction.client.db_interface.get_guild_setup(interaction.guild_id)
        if not guild_data or not guild_data.get('modmail_channel_id'):
            await interaction.response.send_message(
                "❌ The modmail channel has not been set up. Please contact an administrator.",
                ephemeral=True
            )
            return
            
        await interaction.response.send_message(
            "You will be assigned a temporary role and directed to the modmail channel.",
            ephemeral=True
        )
        
        # Find or create temp role
        guild = interaction.guild
        temp_role = discord.utils.get(guild.roles, name="temp")
        if not temp_role:
            try:
                temp_role = await guild.create_role(name="temp", reason="Temporary role for alumni verification")
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ I don't have permission to create roles.",
                    ephemeral=True
                )
                return
                
        # Assign temp role
        member = guild.get_member(interaction.user.id)
        if member:
            try:
                await member.add_roles(temp_role, reason="Alumni verification in progress")
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ I don't have permission to assign roles.",
                    ephemeral=True
                )
                return
                
        # Get modmail channel
        modmail_channel = guild.get_channel(guild_data['modmail_channel_id'])
        if not modmail_channel:
            await interaction.followup.send(
                "❌ The modmail channel could not be found.",
                ephemeral=True
            )
            return
            
        # Update channel permissions
        try:
            await modmail_channel.set_permissions(temp_role, 
                                                read_messages=True, 
                                                send_messages=True,
                                                reason="Allow alumni verification access")
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to modify channel permissions.",
                ephemeral=True
            )
            return
            
        # Notify admins
        admin_roles = []
        role_names = ['Co-President', 'Secretary', 'Treasurer', 'Representative']
        for role_name in role_names:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                admin_roles.append(role.mention)
                
        if admin_roles:
            await modmail_channel.send(
                f"{', '.join(admin_roles)}: {interaction.user.mention} needs Alumni verification."
            )
        
        await interaction.followup.send(
            f"Please go to {modmail_channel.mention} and provide proof of your alumni status.\n"
            "An administrator will verify you shortly.",
            ephemeral=True
        )

class ProspectiveVerifyButton(VerificationButton):
    def __init__(self):
        super().__init__("Prospective Student", discord.ButtonStyle.secondary, "prospective")
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Please check your DMs for verification instructions.",
            ephemeral=True
        )
        
        try:
            await interaction.user.send(
                "To verify as a prospective student, please enter your email address.\n"
                "You will receive a verification code at this email."
            )
            
            def check(m):
                return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)
                
            try:
                msg = await interaction.client.wait_for('message', check=check, timeout=300)
                email = msg.content.strip()
                
                # Start verification process
                success, message = await start_prospective_verification(
                    interaction.client.db_interface,
                    interaction.user.id,
                    email
                )
                
                await interaction.user.send(message)
                if success:
                    await self.handle_verification_code(interaction)
                    
            except asyncio.TimeoutError:
                await interaction.user.send("Verification timed out. Please try again.")
                
        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't send you a DM. Please enable DMs from server members and try again.",
                ephemeral=True
            )
    
    async def handle_verification_code(self, interaction: discord.Interaction):
        """Handle verification code entry and processing"""
        def check(m):
            return (
                m.author == interaction.user 
                and isinstance(m.channel, discord.DMChannel)
                and m.content.isdigit() 
                and len(m.content) == 6
            )
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=300)
            entered_code = int(msg.content)
            
            success, message, confirmed_type = await verify_code(
                interaction.client.db_interface,
                interaction.user.id,
                entered_code
            )
            
            await interaction.user.send(message)
            
            if success and confirmed_type == "prospective":
                # Update verification status and assign role
                if await update_verification_status(
                    interaction.client.db_interface,
                    interaction.user.id,
                    interaction.guild_id,
                    "prospective"
                ):
                    # Assign the prospective role
                    guild_data = await interaction.client.db_interface.get_guild_setup(interaction.guild_id)
                    if guild_data and guild_data.get('prospective_student_role_id'):
                        guild = interaction.guild
                        member = guild.get_member(interaction.user.id)
                        if member:
                            prospective_role = guild.get_role(guild_data['prospective_student_role_id'])
                            verified_role = guild.get_role(guild_data['verified_role_id'])
                            if prospective_role and verified_role:
                                await member.add_roles(prospective_role, verified_role,
                                                    reason="Verified as prospective student")
                                await interaction.user.send("✅ You have been verified as a prospective student!")
                                return
                                
                await interaction.user.send("❌ There was an error assigning your roles. Please contact an administrator.")
                
        except asyncio.TimeoutError:
            await interaction.user.send("Verification timed out. Please try again.")

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(StudentVerifyButton())
        self.add_item(FriendVerifyButton())
        self.add_item(AlumniVerifyButton())
        self.add_item(ProspectiveVerifyButton())

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.views = {}  # Track active verification views
        self.setup_task = None
    
    async def cog_load(self):
        """Initialize persistent views"""
        self.bot.add_view(VerificationView())
        self.setup_task = self.bot.loop.create_task(self.setup_verification_channels())
    
    async def cog_unload(self):
        """Clean up when cog is unloaded"""
        if self.setup_task:
            self.setup_task.cancel()
            
    async def setup_verification_channels(self):
        """Setup verification channels for all guilds"""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            try:
                await self.ensure_verification_channels(guild)
            except Exception as e:
                self.logger.error(f"Error setting up verification channels for guild {guild.id}: {e}")
                
    async def ensure_verification_channels(self, guild: discord.Guild):
        """Ensure verification and modmail channels exist with correct permissions"""
        try:
            db = self.bot.db_interface
            guild_data = await db.get_guild_setup(guild.id)
            
            if not guild_data:
                return
            
            # Get channel IDs
            verification_channel_id = guild_data.get('verification_channel_id')
            modmail_channel_id = guild_data.get('modmail_channel_id')
            verification_channel = guild.get_channel(verification_channel_id) if verification_channel_id else None
            modmail_channel = guild.get_channel(modmail_channel_id) if modmail_channel_id else None

            # Ensure verification message exists
            if verification_channel:
                await self._ensure_verification_message(verification_channel, guild_data)

        except Exception as e:
            self.logger.error(f"Error in ensure_verification_channels for guild {guild.id}: {e}")

    async def _ensure_verification_message(self, channel: discord.TextChannel, guild_data: dict):
        """Ensure the verification message exists in the verification channel"""
        try:
            message_id = guild_data.get('verification_message_id')
            message = None
            
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                except (discord.NotFound, discord.Forbidden):
                    pass
                    
            if not message:
                # Send new verification message
                message = await channel.send(
                    "**Welcome to the verification system!**\n\n"
                    "Please select your status below to begin verification:\n\n"
                    "🎓 **Student** - Current RPI student\n"
                    "👥 **Friend** - Friend of an existing member\n"
                    "🎊 **Alumni** - Former RPI student\n"
                    "🔍 **Prospective Student** - Interested in attending RPI\n\n"
                    "Click the appropriate button below to start the verification process.",
                    view=VerificationView()
                )
                
                # Update database with new message ID
                await self.bot.db_interface.execute('''
                    UPDATE guilds 
                    SET verification_message_id = $1 
                    WHERE guild_id = $2
                ''', message.id, channel.guild.id)
                
        except Exception as e:
            self.logger.error(f"Error ensuring verification message: {e}")
            raise
            
async def setup(bot):
    await bot.add_cog(Verification(bot))