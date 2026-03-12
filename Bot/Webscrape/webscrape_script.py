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

rcsid = "BushG"
password = "f7BnKTaf"

try:
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # options.add_argument("--headless=new")

    driver = uc.Chrome(version_main=145, options=options)
    print("Initialized UC")
except Exception as exc:
    print(f"While starting chrome instance threw error:\n ```{str(exc)}```")
    exit()

try:        
    driver.get("https://cms.union.rpi.edu/login/password/")
    print("Reached CMS Site")
except Exception as exc:
    print(f"While loading CMS, threw error:\n ```{str(exc)}```")
    exit()

# try:
# click RCS Login button
login_button_obj = driver.find_element(By.XPATH, "//div[@id='content-wrap']/div[@id='content']//div[@id='login-panel']/div[@class='panel-body']/a")
print(f"login_button_obj = {login_button_obj}")
login_button_obj.click()
login_button_obj = None
time.sleep(1.5)

# get username input, input username
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
time.sleep(1.5)

# get password input, input password
password_input_obj = driver.find_element(By.XPATH, "//form/input[@id='password']")
print(f"password_input_obj = {password_input_obj}")
# password = getpass("Password: ")
password_input_obj.send_keys(password)

# re-get login button, login
login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
print(f"login_button_obj = {login_button_obj}")
login_button_obj.click()
# except Exception as exc:
# print(f"While logging in, threw error:\n ```{str(exc)}```")
# exit()

# receive duo code
# https://api-3e0243bb.duosecurity.com/frame/v4/auth/prompt?sid=frameless-3dee09bc-a439-4b8b-93f2-1885e314b8d4
for x in range(7):
    if "duosecurity.com/frame/v4/auth/prompt" in driver.current_url:
        print("duosecurity.com loaded")
        break
    time.sleep(1)
time.sleep(3)
try:
    duo_code_div = driver.find_element(By.XPATH, "//div[@class='row display-flex align-flex-justify-content-center verification-code']")
    print("Found duo_code_div")
    duo_code = duo_code_div.text
    print(f"DUO CODE: {duo_code}")
except Exception as exc:
    print(f"While retrieving DUO code, threw error:\n ```{str(exc)}```")
    exit()

while "duo" in driver.current_url and x in range(30):
    try:
        unsafe_button = driver.find_element(By.ID, "dont-trust-browser-button")
        unsafe_button.click()
    except:
        time.sleep(1)

# await asyncio.sleep(3)

time.sleep(60)

#<button id="dont-trust-browser-button" class="button--link link">No, other people use this device</button>
#<button id="dont-trust-browser-button" class="button--link link">No, other people use this device</button>

# https://api-3e0243bb.duosecurity.com/frame/v4/auth/prompt?sid=frameless-313a0d13-cc0e-4ed1-ae25-9617e1868067

driver.quit()