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
from threading import Lock
from dotenv import load_dotenv

# + bright data (stdlib)
import urllib.request
import ssl
import random

load_dotenv()

# ---------- KEYWORDS ----------
with open("keywords.yaml", "r", encoding="utf-8") as f:
    keyword_patterns = yaml.safe_load(f)

# ---------- GOOGLE SHEETS ----------
gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE26 - Similar to Adobe Ecommerce").worksheet("Classification")

# ---------- RANGE / POOL ----------
start_value = 1
end_value = 1800
bucket_size = 200
max_threads = 25

# ---------- HEADERS ----------
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------- SELENIUM ----------
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
selenium_driver = webdriver.Chrome(options=chrome_options)
selenium_lock = Lock()  # ważne przy wątkach

def get_text_with_selenium(url):
    try:
        with selenium_lock:
            selenium_driver.set_page_load_timeout(10)
            selenium_driver.get(url)
            time.sleep(2)
            html = selenium_driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ").strip()
    except Exception:
        return None

# ---------- BRIGHT DATA (Web Unlocker) ----------
# Używamy dokładnie tego stylu logowania, który u Ciebie działał.
BRD_CUSTOMER = os.getenv("BRD_CUSTOMER")
BRD_PASSWORD = os.getenv("BRD_PASSWORD")
BRD_HOST     = os.getenv("BRD_HOST", "brd.superproxy.io")
BRD_PORT     = os.getenv("BRD_PORT", "33335")

def build_bd_opener():
    """Buduje opener z proxy Web-Unlocker; brak verify SSL (jak w Twoim teście)."""
    if not BRD_CUSTOMER or not BRD_PASSWORD:
        return None
    proxy = f"http://{BRD_CUSTOMER}:{BRD_PASSWORD}@{BRD_HOST}:{BRD_PORT}"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'https': proxy, 'http': proxy}),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
    )
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        ("Accept-Language", "en-US,en;q=0.9"),
    ]
    return opener

def html_to_text(html: str) -> str:
    """Czyszczenie skryptów/stylów i ucinanie banera cookies z góry."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = soup.get_text(separator="\n", strip=True).splitlines()
    head = "\n".join(lines[:50]).lower()
    if any(w in head for w in ("cookie", "gdpr", "consent", "rodo")):
        lines = lines[50:]
    return "\n".join(l for l in (s.strip() for s in lines) if l)

def get_text_with_brightdata(url, timeout=60):
    """Trzeci etap: próba przez Bright Data Web-Unlocker; zwraca czysty tekst lub None."""
    try:
        opener = build_bd_opener()
        if not opener:
            return None
        raw = opener.open(url, timeout=timeout).read()
        html = raw.decode("utf-8", errors="ignore")
        return html_to_text(html)
    except Exception:
        return None

# ---------- HELPERS ----------
def is_valid_domain(domain):
    return bool(re.match(r"^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$", domain))

def classify_content(text, patterns):
    text = (text or "").lower()
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

# ---------- PIPELINE (requests -> selenium -> bright data) ----------
def process_domain(index, domain):
    if not is_valid_domain(domain):
        print(f"Row {index}: Invalid domain '{domain}'")
        return index, "Invalid domain", "Yes: False Maybe: 0 No: 0"

    url = "https://" + domain
    text = None

    # 1) requests + bs4
    try:
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            text = soup.get_text(separator=" ").strip()
        else:
            text = None
    except requests.exceptions.RequestException:
        text = None

    # 2) selenium (jeśli brak treści)
    if not text:
        text = get_text_with_selenium(url)

    # 3) bright data (jeśli nadal brak treści)
    if not text:
        text = get_text_with_brightdata(url)

    # klasyfikacja
    if text:
        clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        result, stats = classify_content(clean, keyword_patterns)
    else:
        result, stats = "No content", "Yes: False Maybe: 0 No: 0"

    return index, result, stats

# ---------- MAIN LOOP ----------
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

    update_range_B = f"B{bucket_start}:B{bucket_end}"
    update_range_C = f"C{bucket_start}:C{bucket_end}"
    result_list_B = [[""] for _ in range(bucket_size)]
    result_list_C = [[""] for _ in range(bucket_size)]

    for i in range(bucket_size):
        row_idx = bucket_start + i
        result_list_B[i][0] = results.get(row_idx, "")
        result_list_C[i][0] = stats.get(row_idx, "")

    sh.update(update_range_B, result_list_B)
    sh.update(update_range_C, result_list_C)

selenium_driver.quit()
