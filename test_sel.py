from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install())
)

driver.get("https://images.google.com")

time.sleep(2)

search = driver.find_element(By.NAME, "q")

search.send_keys("car air filter")

search.send_keys(Keys.ENTER)

input("Search completed. Press Enter...")

driver.quit()