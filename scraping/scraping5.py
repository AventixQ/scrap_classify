import openai
import requests
from bs4 import BeautifulSoup
import gspread
import os
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from gpt_classification5 import classify

# OpenAI setup
openai.api_key = os.getenv("OPENAI_API_KEY")

# Wczytaj prompt
with open("categorize_ecommerce.txt", "r", encoding="utf-8") as f:
    base_prompt = f.read().strip()

# Google Sheets
gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE26 - Visitors campaign").worksheet("Companies classification")

start_value = 1
end_value = 100000
bucket_size = 500
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# Selenium setup
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)

def get_text_with_selenium(url):
    try:
        driver.set_page_load_timeout(10)
        driver.get(url)
        time.sleep(2)
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ").strip()
    except (WebDriverException, TimeoutException):
        return None

for bucket_start in range(start_value, end_value + 1, bucket_size):
    bucket_end = min(bucket_start + bucket_size - 1, end_value)
    rows = sh.get(f"A{bucket_start}:A{bucket_end}")

    for index, row in enumerate(rows, start=bucket_start):
        domain = row[0].strip() if row else None

        if not domain:
            print(f"Row {index}: No domain")
            sh.update_acell(f"B{index}", "No domain")
            continue

        url = "https://" + domain
        print(f"Processing {url}")

        text_content = None
        try:
            response = requests.get(url, headers=headers, timeout=4)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                text_content = soup.get_text(separator=" ").strip()
            else:
                text_content = get_text_with_selenium(url)
        except requests.exceptions.RequestException:
            text_content = get_text_with_selenium(url)

        if text_content:
            clean_text = "\n".join(line.strip() for line in text_content.splitlines() if line.strip())
            try:
                result = classify(clean_text)
                sh.update_acell(f"B{index}", result)
            except Exception as e:
                sh.update_acell(f"B{index}", "Error")
                print(f"Error classifying row {index}: {e}")
        else:
            sh.update_acell(f"B{index}", "No content")

driver.quit()
