

class View(discord.ui.View):
    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def button_callback(self, button, interaction):
        await button.response.send_message("Ending session.")
        driver.quit()