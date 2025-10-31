import os
import discord
from discord import app_commands
from discord.ext import commands
from utils.db import db
from utils.setup import setup_guild
from utils.verification import VerificationView, refresh_verification_message
from commands.year import year_command_logic
from commands.backfill import backfill_command_logic
from utils.email import email_sender
from cogs.roles import RolesCog

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        print("Running setup hook...")
        await db.connect()
        await email_sender.start()
        self.add_view(VerificationView())
        print("Connected to the database and started services.")

        # Run migrations
        await db.execute("CREATE TABLE IF NOT EXISTS role_reaction_messages (message_id BIGINT PRIMARY KEY);")
        await db.execute("ALTER TABLE role_reactions ADD COLUMN IF NOT EXISTS guild_id BIGINT;")
        try:
            await db.execute("""
                ALTER TABLE role_reactions 
                ADD CONSTRAINT role_reactions_message_id_fkey 
                FOREIGN KEY (message_id) 
                REFERENCES role_reaction_messages(message_id) 
                ON DELETE CASCADE;
            """)
        except Exception:
            # Constraint likely already exists
            pass
        print("Database migrations applied.")

        await self.load_extension("cogs.roles")
        print("Loaded cogs.")

        print("Syncing application commands...")
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} command(s).")

        print("Refreshing verification messages in all guilds...")
        for guild in self.guilds:
            await refresh_verification_message(guild)
        print("Verification messages refreshed.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    # The main setup is now in setup_hook

@bot.event
async def on_guild_join(guild: discord.Guild):
    await setup_guild(guild)

async def is_admin_or_rep(interaction: discord.Interaction) -> bool:
    """Custom check to see if a user is an admin or has the Representative role."""
    if interaction.permissions.administrator:
        return True
    
    settings_records = await db.execute("SELECT representative_id FROM server_settings WHERE guild_id = $1", interaction.guild.id)
    if not settings_records or not settings_records[0].get('representative_id'):
        return False
        
    rep_role_id = settings_records[0]['representative_id']
    if any(role.id == rep_role_id for role in interaction.user.roles):
        return True
        
    return False

@bot.tree.command(name="year", description="Updates student years, graduates alumni, and cleans the database.")
@app_commands.checks.has_permissions(administrator=True)
async def year(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    result_message = await year_command_logic(interaction.guild)
    await interaction.followup.send(result_message, ephemeral=True)

@bot.tree.command(name="backfill", description="Manually populates the database with existing server members.")
@app_commands.check(is_admin_or_rep)
async def backfill(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    result_message = await backfill_command_logic(interaction)
    await interaction.followup.send(result_message, ephemeral=True)

@backfill.error
async def backfill_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You do not have permission to use this command. You must be an Administrator or a Representative.", ephemeral=True)
    else:
        await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
        print(error)

@bot.event
async def on_disconnect():
    await db.close()
    print("Disconnected from the database.")


bot.run(os.getenv("DISCORD_TOKEN"))
