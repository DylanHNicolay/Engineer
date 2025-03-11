from discord.ext import commands
import discord

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Handles when a member leaves the server"""
        db = self.bot.get_cog("DbCog")
        if db and getattr(db, "db", None):
            try:
                await db.db.remove_user_from_guild(member.id, member.guild.id)
            except Exception as e:
                print(f"Error removing user from guild in database: {e}")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        # Ignore if guild is in setup
        setup_cog = self.bot.get_cog("Setup")
        if setup_cog and after.guild.id in setup_cog.pending_setups:
            return

        guild = after.guild
        bot_member = guild.get_member(self.bot.user.id)
        if bot_member and after in bot_member.roles:
            # Check top role
            highest_position = max(guild.roles, key=lambda r: r.position).position
            # Fetch engineer_channel_id from DB or a cache
            # ...existing code...
            engineer_channel_id = None  # Example placeholder
            # ...existing code...
            channel = guild.get_channel(engineer_channel_id) if engineer_channel_id else None

            if after.position < highest_position:
                # Disable bot functions, send warning
                if channel:
                    await channel.send("Engineer role is no longer at the top! Bot functions disabled.")
                # ... code to disable ...
            else:
                # Re-enable bot functions
                if channel:
                    await channel.send("Engineer role restored. Bot functions re-enabled.\nPlease execute /role_check.")
                # ... code to re-enable ...

                # If role was moved again incorrectly:
                # ...existing code to send repeated warnings...

# Add the setup function
async def setup(bot):
    await bot.add_cog(Events(bot))
