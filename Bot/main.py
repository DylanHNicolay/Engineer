import discord
from discord import app_commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.tree.command()
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000) 
    await interaction.response.send_message(f"Pong! Latency: {latency}ms")

client.run(os.getenv("DISCORD_SECRET"))
