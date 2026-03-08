import asyncio
import discord
import requests
from discord import app_commands
from discord.ext import commands
import undetected_chromedriver as uc
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from getpass import getpass



# options = uc.ChromeOptions()
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-gpu")
# options.add_argument("--headless=new")

# driver = uc.Chrome(version_main=121, options=options)

# # driver = uc.Chrome(version_main=144)
# driver.get("https://cms.union.rpi.edu/login/password/")

# # click RCS Login button
# login_button_obj = driver.find_element(By.XPATH, "//div[@id='content-wrap']/div[@id='content']//div[@id='login-panel']/div[@class='panel-body']/a")
# login_button_obj.click()
# login_button_obj = None
# time.sleep(1.5)

# # get username input, input username
# username_input_obj = driver.find_element(By.XPATH, "//form/input[@id='username']")
# username = str(input("Username: "))
# username_input_obj.send_keys(username)

# # click login button to show password input
# login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
# login_button_obj.click()
# login_button_obj = None
# time.sleep(1.5)

# # get password input, input password
# password_input_obj = driver.find_element(By.XPATH, "//form/input[@id='password']")
# password = getpass("Password: ")
# password_input_obj.send_keys(password)

# # re-get login button, login
# login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
# login_button_obj.click()

# # receive duo code
# time.sleep(5)
# duo_code_div = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div/div[2]/div[3]")
# duo_code_div = driver.find_element(By.XPATH, "//div[@class='verification-code']")
# duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']")
# duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']/div[@class='main']")
# duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']/div[@class='main']//div[@class='verification-code']")

# duo_code = duo_code_div.text()
# print(f"DUO CODE: {duo_code}")
# #<div class="row display-flex align-flex-justify-content-center verification-code">613</div>

# time.sleep(10)

# driver.quit()


class webscrape(commands.Cog):

    @app_commands.command(name="webscrape", description="Asynchronously access the Club Management System")
    async def webscrape(self, interaction: discord.Interaction):
        
        await interaction.response.send_message("WARNING: This command is currently incomplete. Are you sure you want to continue? (y / n)")

        def check(message: discord.Message) -> bool:
            return (
                message.author.id == interaction.user.id
                and message.channel.id == interaction.channel_id
            )

        try: # waiting for message
            response = await interaction.client.wait_for('message', check=check, timeout=30.0) # timeout - how long bot waits for message (in seconds)
        except asyncio.TimeoutError: # returning after timeout
            return

        # if response is different than yes / y - return
        if response.content.lower() not in ("yes", "y"):
            return

        # check that cms.union.rpi.edu is up
        try:
            requests.get('https://cms.union.rpi.edu/login/password/')
        except Exception as exc:
            await interaction.followup.send(f"Failed to connect to the club management website:\n```{str(exc)}```")
            return


        try:
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--headless=new")

            driver = uc.Chrome(version_main=121, options=options)
        except Exception as exc:
            await interaction.followup.send(f"While starting chrome instance threw error:\n ```{str(exc)}```", ephemeral=True)
            return

        try:        
            driver.get("https://cms.union.rpi.edu/login/password/")
        except Exception as exc:
            await interaction.followup.send(f"While loading CMS, threw error:\n ```{str(exc)}```", ephemeral=True)
            return

        try:
            # click RCS Login button
            login_button_obj = driver.find_element(By.XPATH, "//div[@id='content-wrap']/div[@id='content']//div[@id='login-panel']/div[@class='panel-body']/a")
            login_button_obj.click()
            login_button_obj = None
            time.sleep(1.5)

            # get username input, input username
            username_input_obj = driver.find_element(By.XPATH, "//form/input[@id='username']")
            username = str(input("Username: "))
            username_input_obj.send_keys(username)

            # click login button to show password input
            login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
            login_button_obj.click()
            login_button_obj = None
            time.sleep(1.5)

            # get password input, input password
            password_input_obj = driver.find_element(By.XPATH, "//form/input[@id='password']")
            password = getpass("Password: ")
            password_input_obj.send_keys(password)

            # re-get login button, login
            login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
            login_button_obj.click()
        except Exception as exc:
            await interaction.followup.send(f"While logging in, threw error:\n ```{str(exc)}```", ephemeral=True)
            return

        # receive duo code
        time.sleep(5)
        try:
            duo_code_div = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div/div[2]/div[3]")
            duo_code_div = driver.find_element(By.XPATH, "//div[@class='verification-code']")
            duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']")
            duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']/div[@class='main']")
            duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']/div[@class='main']//div[@class='verification-code']")

            duo_code = duo_code_div.text()
            print(f"DUO CODE: {duo_code}")
        except Exception as exc:
            await interaction.followup.send(f"While retrieving DUO code, threw error:\n ```{str(exc)}```", ephemeral=True)
            return

        time.sleep(10)

        driver.quit()

async def setup(bot: commands.Bot):
    await bot.add_cog(webscrape(bot))