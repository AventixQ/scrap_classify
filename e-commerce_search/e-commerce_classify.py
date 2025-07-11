import requests
from bs4 import BeautifulSoup
import gspread
import os
import re
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException

# Setup Google Sheets
gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("Company Lookalikes ").worksheet("Class")

# Config
start_value = 1
end_value = 17200
bucket_size = 200
max_threads = 25

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# Regex pattern
ecommerce_pattern = re.compile(r"\b(e[\s\-]?commerce|commerce)\b", re.IGNORECASE)

def contains_ecommerce_keyword(text):
    return bool(ecommerce_pattern.search(text))

# Selenium fallback (uruchamiamy tylko 1 przeglądarkę)
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
selenium_driver = webdriver.Chrome(options=chrome_options)

def get_text_with_selenium(url):
    try:
        selenium_driver.set_page_load_timeout(10)
        selenium_driver.get(url)
        time.sleep(2)
        html = selenium_driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ").strip()
    except Exception:
        return None

def is_valid_domain(domain):
    # Prosta walidacja domeny
    return bool(re.match(r"^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$", domain))

# Funkcja robocza
def process_domain(index, domain):
    if not is_valid_domain(domain):
        print(f"Row {index}: Invalid domain '{domain}'")
        return index, "Invalid domain"
    url = "https://" + domain
    try:
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text(separator=" ").strip()
        else:
            text = get_text_with_selenium(url)
    except requests.exceptions.RequestException:
        text = get_text_with_selenium(url)

    if text:
        clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        result = "Yes" if contains_ecommerce_keyword(clean) else "No"
    else:
        result = "No content"

    return index, result

# Główna pętla
for bucket_start in range(start_value, end_value + 1, bucket_size):
    bucket_end = min(bucket_start + bucket_size - 1, end_value)
    rows = sh.get(f"A{bucket_start}:A{bucket_end}")
    
    domains = [(i, row[0].strip()) for i, row in enumerate(rows, start=bucket_start) if row and row[0].strip()]
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(process_domain, idx, dom): idx for idx, dom in domains}
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                results[idx] = result
                print(f"Processed row {idx}: {result}")
            except Exception as e:
                print(f"Error processing future for row {futures[future]}: {e}")
                results[futures[future]] = "Error"

    
    # Przygotuj dane do batch update
    update_range = f"B{bucket_start}:B{bucket_end}"
    result_list = [[""] for _ in range(bucket_size)]
    for i in range(bucket_size):
        row_idx = bucket_start + i
        result_list[i][0] = results.get(row_idx, "")

    sh.update(update_range, result_list)

selenium_driver.quit()
