"""
LLM-only domain classifier

ENV:
  CREDS_FILE       – ścieżka do json-creds Google Service Account
  OPENAI_API_KEY   – klucz do OpenAI
FILES:
  llm_prompt.txt   – prompt z placeholderem {content}
"""

import os, re, time, requests, gspread
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------- CONFIG ----------
START_ROW          = 15600
END_ROW            = 25299
BUCKET_SIZE        = 100
MAX_THREADS        = 5
REQUEST_TIMEOUT    = 10
SELENIUM_WAIT      = 10
MAX_TEXT_LEN       = 12000
# ---------- PROMPT ----------
LLM_PROMPT_TEMPLATE = "llm_prompt.txt"

# ---------- GOOGLE SHEETS ----------
gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE26 - Visitors classification").worksheet("All visitors companies")

# ---------- OPENAI ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- SELENIUM (współdzielony, z lockiem) ----------
chrome_opts = Options()
chrome_opts.add_argument("--disable-gpu")
chrome_opts.add_argument("--no-sandbox")
chrome_opts.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_opts)
driver_lock = Lock()

# ---------- HELPERS ----------
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}

def is_valid_domain(domain: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$", domain))

COOKIE_NOISE = (
    "cookie", "gdpr", "consent", "We use cookies", "Używamy plików cookie",
    "Wir verwenden Cookies", "Usamos cookies", "Wij gebruiken cookies"
)

def strip_cookie_noise(text: str) -> str:
    if not text:
        return text
    parts = text.splitlines()
    head = "\n".join(parts[:30])
    if any(w.lower() in head.lower() for w in COOKIE_NOISE):
        return "\n".join(parts[30:])
    return text

# --- SCRAPER ---
def scrape_domain(domain: str) -> tuple[str, str | None]:
    """
    Zwraca (plain_text, err_code).
    err_code == None  → OK
    err_code == str   → 'HTTP_403' / 'Cloudflare/Captcha' / 'NoContent' / ...
    """
    url  = "https://" + domain
    text = ""
    err  = None

    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            page_text = soup.get_text(" ").strip()
            cf_markers = ("Attention Required", "Cloudflare", "Verify you are human", "captcha")
            deny_markers = ("Access Denied", "blocked")
            if any(m.lower() in page_text.lower() for m in cf_markers) or any(m.lower() in page_text.lower() for m in deny_markers):
                err = "Cloudflare/Captcha"
            else:
                text = page_text
        else:
            err = f"HTTP_{r.status_code}"
    except requests.RequestException:
        err = "REQ_ERROR"

    if not text and err is None:
        try:
            with driver_lock:
                driver.set_page_load_timeout(REQUEST_TIMEOUT + 6)
                driver.get(url)
                time.sleep(SELENIUM_WAIT)
                html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ").strip()
            if not text:
                err = "NoContent"
        except Exception:
            err = "SeleniumFail"

    if text:
        text = strip_cookie_noise(text)

    return text, err

VALID_LABELS = {"Shop", "Service Provider"}

def load_prompt(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def classify_llm(text: str, domain: str) -> str:
    if not text:
        return "Unscrapable"
    prompt = load_prompt(LLM_PROMPT_TEMPLATE)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content":
            f'''
            Categorize {domain} using the plain text scrapped below:
            {text[:MAX_TEXT_LEN]}
            '''
                }
            ],
            temperature=0.0,
        )
        out = (resp.choices[0].message.content or "").strip()
        if out not in VALID_LABELS:
            first = out.splitlines()[0].strip()
            return first #if first in VALID_LABELS else "Unclear"
        return out
    except Exception as e:
        print(f"Exception :/ {e}")
        return "Unclear"

# --- WORKER (scrape + LLM) ---
def process_row(row_idx: int, domain: str) -> tuple[int, str]:
    """
    Zwraca: (index_wiersza, etykieta_do_kolumny_B)
    """
    if not is_valid_domain(domain):
        return row_idx, "Unscrapable"

    text, err = scrape_domain(domain)
    if err:
        return row_idx, "Unscrapable"

    label = classify_llm(text, domain)
    print(f"{domain}: {label}")
    return row_idx, label

# ---------- MAIN LOOP ----------
for start in range(START_ROW, END_ROW + 1, BUCKET_SIZE):
    end = min(start + BUCKET_SIZE - 1, END_ROW)
    rows = sh.get(f"A{start}:A{end}")
    domains = [(i, r[0].strip()) for i, r in enumerate(rows, start=start) if r and r[0].strip()]

    results: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        futs = {ex.submit(process_row, idx, dom): idx for idx, dom in domains}
        for fut in as_completed(futs):
            idx = futs[fut]
            try:
                ridx, label = fut.result()
            except Exception as e:
                ridx, label = idx, "Unclear"
                print(f"Exception :/ {e}")
            results[ridx] = label

    bucket_len = end - start + 1
    col_b = []
    for offset in range(bucket_len):
        ridx = start + offset
        col_b.append([results.get(ridx, "")])

    sh.update(values=col_b, range_name=f"B{start}:B{end}")

driver.quit()
