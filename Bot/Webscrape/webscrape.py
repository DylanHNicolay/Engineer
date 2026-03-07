import undetected_chromedriver as uc
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from getpass import getpass


driver = uc.Chrome(version_main=144)
driver.get("https://cms.union.rpi.edu/login/password/")

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

# receive duo code
time.sleep(5)
duo_code_div = driver.find_element(By.XPATH, "/html/body/div[1]/div/div[1]/div/div[2]/div[3]")
duo_code_div = driver.find_element(By.XPATH, "//div[@class='verification-code']")
duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']")
duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']/div[@class='main']")
duo_code_div = driver.find_element(By.XPATH, "//div[@class='app']/div[@class='main']//div[@class='verification-code']")

duo_code = duo_code_div.text()
print(f"DUO CODE: {duo_code}")
#<div class="row display-flex align-flex-justify-content-center verification-code">613</div>

time.sleep(10)

driver.quit()


# class webscrape(commands.Cog):

# 	@app_commands.command(name="webscrape", description="Asynchronously access the Club Management System")
# 	async def webscrape(self, innteraction: discord.Interaction):
# 		driver = uc.Chrome(version_main=144)
# 		driver.get("https://cms.union.rpi.edu/login/password/")

# 		# click RCS Login button
# 		login_button_obj = driver.find_element(By.XPATH, "//div[@id='content-wrap']/div[@id='content']//div[@id='login-panel']/div[@class='panel-body']/a")
# 		login_button_obj.click()
# 		login_button_obj = None
# 		time.sleep(1.5)

# 		# get username input, input username
# 		username_input_obj = driver.find_element(By.XPATH, "//form/input[@id='username']")
# 		username = str(input("Username: "))
# 		username_input_obj.send_keys(username)

# 		# click login button to show password input
# 		login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
# 		login_button_obj.click()
# 		login_button_obj = None
# 		time.sleep(1.5)

# 		# get password input, input password
# 		password_input_obj = driver.find_element(By.XPATH, "//form/input[@id='password']")
# 		password = getpass("Password: ")
# 		password_input_obj.send_keys(password)

# 		# re-get login button, login
# 		login_button_obj = driver.find_element(By.XPATH, "//form/div/button")
# 		login_button_obj.click()

# 		# receive duo code

# 		time.sleep(10)

# 		driver.quit()