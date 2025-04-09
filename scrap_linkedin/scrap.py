import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from print import extract_information

'''
To scrape seperate page from linkedin
'''

def configure_browser():
    chrome_options = Options()

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def login_to_linkedin(driver, email, password):
    driver.get('https://www.linkedin.com/login')

    time.sleep(random.uniform(2, 5))

    username_field = driver.find_element(By.ID, 'username')
    password_field = driver.find_element(By.ID, 'password')

    username_field.send_keys(email)
    time.sleep(random.uniform(1, 2))
    password_field.send_keys(password)
    time.sleep(random.uniform(1, 2))

    login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')
    login_button.click()

    time.sleep(random.uniform(5, 10))

def get_data(driver, url):

    driver.get(url)
    time.sleep(random.uniform(3, 6))

    actions = webdriver.ActionChains(driver)
    for _ in range(3):
        actions.send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(random.uniform(1, 3))

    page_html = driver.page_source

    print(extract_information(page_html))

def main():
    email = 'aventix.jj@gmail.com'
    password = '22668fed'

    company_url = 'https://www.linkedin.com/company/ups/about'

    driver = configure_browser()

    try:
        login_to_linkedin(driver, email, password)
        get_data(driver, company_url)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()