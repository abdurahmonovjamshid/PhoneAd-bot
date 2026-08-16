from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager


def getnumber(url):
    phone_number = url
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        driver.maximize_window()
        button = driver.find_element(
            By.CSS_SELECTOR, 'button[data-test="show-phones-button"]')
        ActionChains(driver).move_to_element(button).click().perform()
        driver.implicitly_wait(1)
        phone_element = driver.find_element(
            By.CSS_SELECTOR, '.contacts-block__item')
        phone_number = phone_element.text.strip().replace(' ', '')
        print('Phone number:', phone_number)

        driver.quit()
    except Exception as e:
        driver.quit()
        print(e)
    return phone_number
