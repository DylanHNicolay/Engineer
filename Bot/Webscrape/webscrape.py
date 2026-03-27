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

from . import dialogue



class webscrape(commands.Cog):

    @app_commands.command(name="webscrape", description="Asynchronously access the Club Management System")
    async def webscrape(self, interaction: discord.Interaction, rcsid:str, password:str):
        print("Running Command:", flush=True)
        await interaction.response.defer(ephemeral=True)
        view = dialogue.ConfirmView()
        await interaction.followup.send("WARNING: This command is currently incomplete. Are you sure you want to continue? (y / n)",
                                        view=view, ephemeral=True)

        await view.wait()

        if view.value is not True:
            print("...Command canceled")
            await interaction.followup.send(f"Canceling command.")
            return

        print("Webscrape")
        # check that cms.union.rpi.edu is up
        try:
            requests.get('https://cms.union.rpi.edu/login/password/')
        except Exception as exc:
            await interaction.followup.send(f"Failed to connect to the club management website:\n```{str(exc)}```", ephemeral=True)
            return


        try:
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--headless=new")

            driver = uc.Chrome(version_main=121, options=options)
            print("Initialized UC")
        except Exception as exc:
            await interaction.followup.send(f"While starting chrome instance threw error:\n ```{str(exc)}```", ephemeral=True)
            return

        try:        
            driver.get("https://cms.union.rpi.edu/login/password/")
            print("Reached CMS Site")
        except Exception as exc:
            await interaction.followup.send(f"While loading CMS, threw error:\n ```{str(exc)}```", ephemeral=True)
            return

        try:
            # click RCS Login button
            login_button_obj = driver.find_element(By.XPATH, "//div[@id='content-wrap']/div[@id='content']//div[@id='login-panel']/div[@class='panel-body']/a")
            print(f"login_button_obj = {login_button_obj}")
            login_button_obj.click()
            login_button_obj = None
            await asyncio.sleep(1.5)

            # get username input box, input username
            username_input_obj = driver.find_element(By.XPATH, "//form/input[@id='username']")
            print(f"username_input_obj = {username_input_obj}")
            # username = str(input("Username: "))
            username = rcsid
            username_input_obj.send_keys(username)

            # click login button to show password input
            login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
            print(f"login_button_obj = {login_button_obj}")
            login_button_obj.click()
            login_button_obj = None
            await asyncio.sleep(1.5)

            # get password input box, input password
            password_input_obj = driver.find_element(By.XPATH, "//form/input[@id='password']")
            print(f"password_input_obj = {password_input_obj}")
            # password = getpass("Password: ")
            password_input_obj.send_keys(password)

            # re-get login button, login
            login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
            print(f"login_button_obj = {login_button_obj}")
            login_button_obj.click()
            await asyncio.sleep(0.5)

            # check if an "incorrect login info" <p>-tag has been generated.
            try:
                incorrect_info = driver.find_element(By.XPATH, "//form/p")
                await interaction.followup.send(f"While logging into CMS, threw error:\n ```{str(incorrect_info.text)}```", ephemeral=True)
                return
            except:
                pass
        except Exception as exc:
            await interaction.followup.send(f"While logging into CMS, threw error:\n ```{str(exc)}```", ephemeral=True)
            return

        # wait for duo redirect
        for x in range(7):
            if "duosecurity.com/frame/v4/auth/prompt" in driver.current_url:
                print("duosecurity.com loaded")
                break
            await asyncio.sleep(1)
        await asyncio.sleep(3)

        # get duo code
        try:
            duo_code_div = driver.find_element(By.XPATH, "//div[@class='row display-flex align-flex-justify-content-center verification-code']")
            print("Found duo_code_div")
            duo_code = duo_code_div.text
            print(f"DUO CODE: {duo_code}")
            await interaction.followup.send(f"Your DUO code is {duo_code}, please input your code to the DUO mobile app", ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(f"While retrieving DUO code, threw error:\n ```{str(exc)}```", ephemeral=True)
            return


        # wait to be redirected from duo
        while "duo" in driver.current_url and x in range(31):
            try:
                # try to continue redirect
                dont_trust_button = driver.find_element(By.ID, "dont-trust-browser-button")
                dont_trust_button.click()
            except:
                # if redirecting from Duo takes >= 30 seconds / user does not input Duo code
                if x == 30:
                    await interaction.followup.send(f"While redirecting from DUO, threw error:\n ```Unable to redirect from DUO, stuck at {driver.current_url}```", ephemeral=True)
                await asyncio.sleep(2)
        await asyncio.sleep(2)
        print(driver.current_url)

        if "cms.union.rpi.edu" in driver.current_url:
            await interaction.followup.send(f"You have succesfully logged into the Club Management System!", ephemeral=True)
        else:
            await interaction.followup.send(f"While redirecting from DUO, threw error:\n ```Bad redirect to {driver.current_url}```", ephemeral=True)
            return

        await asyncio.sleep(10)

        driver.quit()
        print("Driver ended")
        await interaction.followup.send(f"Session ended.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(webscrape(bot))