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

# Add the setup function
async def setup(bot):
    await bot.add_cog(Events(bot))
