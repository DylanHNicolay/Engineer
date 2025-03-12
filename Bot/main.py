import discord
from discord.ext import commands
import asyncpg
import os
from utils.database import DatabaseInterface
import logging

class EngineerBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.all(),
        )
        self.initial_extensions = []
        self.db_interface = None
        logging.basicConfig(level=logging.INFO)
    
    async def setup_hook(self):
        # Database connection
        pool = await asyncpg.create_pool(
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB'),
            host='postgres'
        )
        self.db_interface = DatabaseInterface(pool)
        
        # Load the setup cog for guilds that are still in setup
        try:
            await self.load_extension("cogs.setup")
        except commands.ExtensionAlreadyLoaded:
            pass
        
        # Get all guilds that are in setup mode
        guilds_in_setup = await self.db_interface.fetch('''
            SELECT guild_id FROM guilds WHERE setup = TRUE
        ''')
        
        # Add setup commands to these guilds
        setup_cog = self.get_cog("Setup")
        if setup_cog:
            for guild_record in guilds_in_setup:
                guild_id = guild_record['guild_id']
                logging.info(f"Re-enabling setup for guild {guild_id} marked as setup=True")
                for command in setup_cog.walk_app_commands():
                    self.tree.add_command(command, guild=discord.Object(id=guild_id))
                
                # Sync the command tree for this guild
                await self.tree.sync(guild=discord.Object(id=guild_id))

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
    
    async def on_guild_join(self, guild: discord.Guild):
        # Create engineer channel with restricted permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
            guild.owner: discord.PermissionOverwrite(read_messages=True)
        }
        engineer_channel = await guild.create_text_channel('engineer', overwrites=overwrites)

        # Clear the command tree on join
        self.tree.clear_commands(guild=discord.Object(id=guild.id))
        
        # Add guild to database using the new interface
        await self.db_interface.add_guild_setup(guild.id, engineer_channel.id)
        
        # Ensure the Setup cog and relevant commands are loaded
        # Only newly joined guilds can have access to the setup cog
        try:
            await self.load_extension("cogs.setup")
        except commands.ExtensionAlreadyLoaded:
            pass
        
        setup_cog = self.get_cog("Setup")
        for command in setup_cog.walk_app_commands():
            self.tree.add_command(command, guild=discord.Object(id=guild.id))
        
        await self.tree.sync(guild=discord.Object(id=guild.id))
        
        # Send a message in the engineer channel with setup instructions
        await engineer_channel.send(
            "**Thank you for choosing Engineer!** To begin the setup, please use the **/setup** command.\n"
            "To cancel the setup, use the **/setup_cancel** command. The bot will delete this channel and leave the server.\n\n"
            "Please note that **data** will be **collected** on users including their -\n**discord ID**\n-**relationship with RPI**\n-**relationship with the club/community**.\n\n"
            "This data will be used to provide a better experience for users, including \n-**protecting against spam and harassment**\n-**seamless integration with other RPI communities**\n-**allowing for more personalized experiences**\n\n"
            "You may execute the command at any time, but it is important that **users are informed** about the implementation of Engineer. We recommend waiting at least 7 - 31 days after notifying your users before setting up this bot depending on your server size. Some individuals are uncomfortable with data collection, and it is important to respect their privacy.\n\n"
            "This project is open source and its source code can be found at https://github.com/DylanHNicolay/Engineer\n"
            "If you have any questions or concerns, please reach out to the developer, Dylan Nicolay through Discord: **nico1ax**"
        )

        

async def main():
    bot = EngineerBot()
    await bot.start(os.getenv('DISCORD_SECRET'))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
