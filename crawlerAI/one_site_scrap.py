import os
import csv
import json
import time
import ssl
import urllib.request
from urllib.error import URLError, HTTPError
import requests
from dotenv import load_dotenv
from openai import OpenAI

# -------------------- CONFIG --------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_API_KEY, "Brak OPENAI_API_KEY w .env"

# Tryb promptu: "speaker" albo "company"
MODE = os.getenv("MODE", "speaker").strip().lower()  # opcjonalnie z .env
assert MODE in {"speaker", "company"}, "MODE must be 'speaker' or 'company'"

INPUT_CSV = "links_to_scrap.csv"
OUTPUT_JSONL = "extracted_data.jsonl"

REQUEST_TIMEOUT_S = 15
BRIGHTDATA_TIMEOUT_S = 60
SLEEP_BETWEEN_REQ = 2.5  # grzeczne tempo

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# -------- Bright Data creds (Web Unlocker) --------
BRD_CUSTOMER = os.getenv("BRD_CUSTOMER")
BRD_PASSWORD = os.getenv("BRD_PASSWORD")
BRD_HOST     = os.getenv("BRD_HOST", "brd.superproxy.io")
BRD_PORT     = os.getenv("BRD_PORT", "33335")
BRIGHTDATA_ENABLED = bool(BRD_CUSTOMER and BRD_PASSWORD)

# -------------------- PROMPTS --------------------
PROMPT_COMPANY = """
Extract the following details from the given HTML:
    - Company Name
    - Company Domain
    - Email
    - Phone Number
    - Address
    - Hall Number
    - Stand Number
    - Description
    - Linkedin link
Provide the data in JSON format.
"""

PROMPT_SPEAKER = """
Extract the following details from the given HTML:
    - Company Name
    - Company Domain
    - Speaker First name
    - Speaker Last name
    - Speaker position
    - Topic of talk
    - Description of talk
    - Language
    - Date and hour
Provide the data in JSON format.
"""

# -------------------- OPENAI --------------------
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_details(page_html: str) -> str:
    """Wywołanie LLM, zwraca tekst (JSON jako string lub surowy)."""
    prompt = PROMPT_SPEAKER if MODE == "speaker" else PROMPT_COMPANY
    full_prompt = f"{prompt}\nHTML:\n{page_html[:127000]}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content

# -------------------- FETCHERS --------------------
def fetch_via_requests(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_S)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"[requests] Error for {url}: {e}")
        return None

def build_brightdata_opener() -> urllib.request.OpenerDirector:
    assert BRIGHTDATA_ENABLED, "Bright Data creds missing"
    proxy = f"http://{BRD_CUSTOMER}:{BRD_PASSWORD}@{BRD_HOST}:{BRD_PORT}"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'https': proxy, 'http': proxy}),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
    )
    opener.addheaders = [(k, v) for k, v in HEADERS.items()]
    return opener

def fetch_via_brightdata(url: str) -> str | None:
    if not BRIGHTDATA_ENABLED:
        return None
    try:
        opener = build_brightdata_opener()
        req = urllib.request.Request(url, headers=HEADERS)
        raw = opener.open(req, timeout=BRIGHTDATA_TIMEOUT_S).read()
        return raw.decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, Exception) as e:
        print(f"[brightdata] Error for {url}: {e}")
        return None

def fetch_page_html(url: str) -> tuple[str | None, str]:
    """
    Zwraca (html, source), gdzie source ∈ {"requests","brightdata",""}.
    Najpierw próbuje requests, potem Bright Data; jeśli oba padną → (None, "").
    """
    html = fetch_via_requests(url)
    if html:
        return html, "requests"
    html = fetch_via_brightdata(url)
    if html:
        return html, "brightdata"
    return None, ""

# -------------------- MAIN --------------------
def scrape_links_to_jsonl():
    # wczytaj URL-e z CSV (pierwsza kolumna; pomiń nagłówek "URL" jeśli jest)
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        urls = [row[0] for row in csv.reader(f) if row and row[0].strip()]
    if urls and urls[0].strip().lower() == "url":
        urls = urls[1:]

    if not urls:
        print("[main] Brak URL-i w links_to_scrap.csv")
        return

    processed = 0
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as out:
        for i, url in enumerate(urls, 1):
            html, source = fetch_page_html(url)
            if not html:
                print(f"[main] Failed to fetch (both methods): {url}")
                continue

            data_text = extract_details(html)

            # spróbuj sparsować
            try:
                data_obj = json.loads(data_text)
            except json.JSONDecodeError:
                data_obj = {"raw": data_text}

            record = {
                "url": url,
                "fetch_source": source,  # info diagnostyczne: skąd się udało ściągnąć
                "mode": MODE,            # speaker/company
                "data": data_obj
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            processed += 1

            print(f"[main] {processed}/{len(urls)} OK via {source}: {url}")
            time.sleep(SLEEP_BETWEEN_REQ)

    print(f"[main] Done. Wrote {processed} lines to {OUTPUT_JSONL}")

if __name__ == "__main__":
    scrape_links_to_jsonl()
