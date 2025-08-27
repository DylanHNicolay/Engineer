import discord

class FriendConfirmationView(discord.ui.View):
    def __init__(self, author: discord.Member, friend: discord.Member):
        super().__init__(timeout=1800.0)  # 30-minute timeout
        self.author = author
        self.friend = friend
        self.result = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.friend.id:
            await interaction.response.send_message("This is not for you.", ephemeral=True)
            return
        
        self.result = True
        self.stop()
        # Disable the buttons after a choice is made
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"You have confirmed that you know {self.author.mention}. Thank you!", view=self)

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.friend.id:
            await interaction.response.send_message("This is not for you.", ephemeral=True)
            return
            
        self.result = False
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"You have denied the request from {self.author.mention}. Thank you.", view=self)

    async def on_timeout(self):
        # This is called if the friend doesn't respond in time
        self.result = False
        # We can't edit the message here as we don't have an interaction,
        # but the view will stop listening for events.
