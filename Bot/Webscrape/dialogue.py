import asyncio
import discord
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


# Notes:
# Each Button class is a type of Button that can be added to a View.
# Views are all the differnt combinations of Buttons that are used in the webscrape family of commands



# --------------------- Helper Functions -----------------------------

# stick in every button's callback. It's universal cleanup once a button has been clicked
# async def on_response(view, interaction):
#     await interaction.response.defer(ephemeral=True)
#     for btn in view.children:
#         btn.disabled = True



# --------------------- Button / Select Classes -------------------------------


class ContinueButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Continue", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = self.view

        if hasattr(view, "author") and interaction.user != view.author:
            return

        if hasattr(view, "value"):
            view.value = True
            await self.view.on_response(interaction)
            view.stop()


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = self.view

        if hasattr(view, "author") and interaction.user != view.author:
            return

        if hasattr(view, "on_cancel"):
            await self.view.on_response(interaction)
            await self.view.on_cancel(interaction)
            view.stop()

class ExitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Exit", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = self.view

        if hasattr(view, "author") and interaction.user != view.author:
            return

        if hasattr(view, "on_cancel"):
            await self.view.on_response(interaction)
            await self.view.on_cancel(interaction)
            view.stop()

class clubActionMenu(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select An Option", 
            options = [
                discord.SelectOption(label="Add Users", value="add"),
                discord.SelectOption(label="Remove Users", value="remove"),
                discord.SelectOption(label="Get Users", value="get"),
                discord.SelectOption(label="End Session", value="end")
            ])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = self.view
        select = self.values[0]
        if hasattr(view, "author") and interaction.user != view.author:
            return

        if hasattr(view, "value"):
            view.value = select
            await interaction.followup.send(select, ephemeral=True)

        await self.view.on_response(interaction)


class homeSelectMenu(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select An Option", 
            options = [
                discord.SelectOption(label="End Session", value="end")
                discord.SelectOption(label="Back")
            ])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = self.view
        select = self.values[0]
        if hasattr(view, "author") and interaction.user != view.author:
            return

        if hasattr(view, "value"):
            view.value = select
            if select == "end":
                self.value = False
                if hasattr(self, "driver"):
                    self.driver.quit()
                    self.driver = None
                self.quit()

        await self.view.on_response(interaction)


# --------------------- View Classes ---------------------------------


class ConfirmView(discord.ui.View):
    # def __init__(self, author):
    def __init__(self):
        super().__init__(timeout=60)
        # self.author = author
        self.value = None

        self.add_item(ContinueButton())
        self.add_item(CancelButton())

    async def on_response(self, interaction):
        for btn in self.children:
            btn.disabled = True
        await interaction.followup.edit_message(interaction.message.id, view=self)
    # CancelButton's modular callback function
    async def on_cancel(self, interaction):
        self.value = False
        self.stop()




class CancelDriverView(discord.ui.View):
    def __init__(self, author, driver):
        super().__init__(timeout=60)
        self.author = author
        self.driver = driver
        self.value = None

        self.add_item(CancelButton())
        self.add_item(ContinueButton())

    async def on_cancel(self, interaction):
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.value = False
        await interaction.followup.send("Driver shut down", ephemeral=True)
        self.stop()

class homeSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None

        self.add_item(homeSelectMenu())

    async def on_response(self, interaction):
        for obj in self.children:
            obj.disabled = True
        await interaction.edit_original_response(view=self)
        self.stop()


class defaultView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None

    async def on_response(self, interaction):
        for obj in self.children:
            self.disabled = True
        await interaction.edit_original_response(view=self)
        self.stop()
