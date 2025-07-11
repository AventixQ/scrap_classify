import requests
from bs4 import BeautifulSoup
import gspread
import os
import re
import time
import yaml
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

with open("keywords.yaml", "r", encoding="utf-8") as f:
    keyword_patterns = yaml.safe_load(f)

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE 26 - similiar companies to commercetools").worksheet("class")

start_value = 1
end_value = 1200
bucket_size = 200
max_threads = 25

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

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
    return bool(re.match(r"^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$", domain))

def classify_content(text, patterns):
    text = text.lower()
    found_yes = any(re.search(pat, text) for pat in patterns["strong_yes"].values())
    found_no = sum(bool(re.search(pat, text)) for pat in patterns["strong_no"].values())
    found_maybe = sum(bool(re.search(pat, text)) for pat in patterns["maybe"].values())

    if found_yes and found_no < 2:
        classification = "Yes"
    elif found_maybe >= 3 and found_no < 2:
        classification = "Maybe"
    elif not text:
        classification = "No content"
    else:
        classification = "No"

    debug_stats = f"Yes: {found_yes} Maybe: {found_maybe} No: {found_no}"
    return classification, debug_stats

def process_domain(index, domain):
    if not is_valid_domain(domain):
        print(f"Row {index}: Invalid domain '{domain}'")
        return index, "Invalid domain", "Yes: False Maybe: 0 No: 0"

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
        result, stats = classify_content(clean, keyword_patterns)
    else:
        result, stats = "No content", "Yes: False Maybe: 0 No: 0"

    return index, result, stats

for bucket_start in range(start_value, end_value + 1, bucket_size):
    bucket_end = min(bucket_start + bucket_size - 1, end_value)
    rows = sh.get(f"A{bucket_start}:A{bucket_end}")

    domains = [(i, row[0].strip()) for i, row in enumerate(rows, start=bucket_start) if row and row[0].strip()]

    results = {}
    stats = {}
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(process_domain, idx, dom): idx for idx, dom in domains}
        for future in as_completed(futures):
            try:
                idx, result, debug = future.result()
                results[idx] = result
                stats[idx] = debug
                print(f"Processed row {idx}: {result} | {debug}")
            except Exception as e:
                print(f"Error processing future for row {futures[future]}: {e}")
                results[futures[future]] = "Error"
                stats[futures[future]] = "Error"

    update_range_E = f"B{bucket_start}:B{bucket_end}"
    update_range_F = f"C{bucket_start}:C{bucket_end}"
    result_list_E = [[""] for _ in range(bucket_size)]
    result_list_F = [[""] for _ in range(bucket_size)]

    for i in range(bucket_size):
        row_idx = bucket_start + i
        result_list_E[i][0] = results.get(row_idx, "")
        result_list_F[i][0] = stats.get(row_idx, "")

    sh.update(update_range_E, result_list_E)
    sh.update(update_range_F, result_list_F)

selenium_driver.quit()
