"""
LLM-only classifier + Bright Data Web Unlocker (urllib) + parallel GS write

ENV:
  CREDS_FILE            – ścieżka do json-creds Google Service Account
  OPENAI_API_KEY        – klucz do OpenAI

  # Bright Data – Web Unlocker (używamy dokładnie Twojego schematu)
  BRD_CUSTOMER
  BRD_PASSWORD
  BRD_UNBLOCKER_ZONE    – np. web_unlocker1 (opcjonalnie, nie używamy w loginie)
  BRD_HOST=brd.superproxy.io
  BRD_PORT=33335
"""

import os, re, time, random, ssl, urllib.request, gspread
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import local
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------- CONFIG ----------
START_ROW          = 2
END_ROW            = 600
BUCKET_SIZE        = 100
MAX_THREADS        = 5
MAX_TEXT_LEN       = 12000
REQUEST_TIMEOUT_S  = 60
LLM_PROMPT_TEMPLATE = "llm_prompt.txt"

# ---------- GOOGLE SHEETS ----------
gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE26 - Linkedin Connections - K5 Group").worksheet("All_companies")

# ---------- OPENAI ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
VALID_LABELS = {"Shop", "Service Provider"}

def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

PROMPT_TEXT = load_prompt(LLM_PROMPT_TEMPLATE)

# ---------- BRIGHT DATA (dokładnie jak w Twoim działającym teście) ----------
BRD_CUSTOMER = os.getenv("BRD_CUSTOMER")
BRD_PASSWORD = os.getenv("BRD_PASSWORD")
BRD_HOST     = os.getenv("BRD_HOST", "brd.superproxy.io")
BRD_PORT     = os.getenv("BRD_PORT", "33335")
assert BRD_CUSTOMER and BRD_PASSWORD, "Brak BRD_CUSTOMER/BRD_PASSWORD w .env"

# ---------- HELPERS ----------
_tls = local()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

COOKIE_NOISE = (
    "cookie", "gdpr", "consent", "We use cookies", "Używamy plików cookie",
    "Wir verwenden Cookies", "Usamos cookies", "Wij gebruiken cookies", "RODO"
)

def is_valid_domain(domain: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$", domain))

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = soup.get_text(separator="\n", strip=True).splitlines()
    head = "\n".join(lines[:50]).lower()
    if any(w.lower() in head for w in COOKIE_NOISE):
        lines = lines[50:]
    out = "\n".join(l for l in (s.strip() for s in lines) if l)
    return out

def build_opener() -> urllib.request.OpenerDirector:
    # NIE ZMIENIAMY SCHEMATU LOGOWANIA – jak w Twoim teście
    proxy = f"http://{BRD_CUSTOMER}:{BRD_PASSWORD}@{BRD_HOST}:{BRD_PORT}"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'https': proxy, 'http': proxy}),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
    )
    # globalne nagłówki dla tego opener-a
    opener.addheaders = [(k, v) for k, v in HEADERS.items()]
    return opener

def get_thread_opener() -> urllib.request.OpenerDirector:
    # thread-local opener (bez współdzielenia jednego obiektu między wątkami)
    if not hasattr(_tls, "opener"):
        _tls.opener = build_opener()
    return _tls.opener

# --- SCRAPE ---
def scrape_domain(domain: str) -> tuple[str, str | None]:
    """
    Zwraca (plain_text, err_code).
    err_code == None  → OK
    err_code == str   → 'HTTP_xxx' / 'OpenError' / 'DecodeError' / 'NoContent'
    """
    url = "https://" + domain
    opener = get_thread_opener()
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        raw = opener.open(req, timeout=REQUEST_TIMEOUT_S).read()
    except Exception as e:
        return "", f"OpenError:{e}"

    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        return "", f"DecodeError:{e}"

    text = html_to_text(html)
    if not text:
        return "", "NoContent"
    return text, None

# --- LLM ---
def classify_llm(text: str, domain: str) -> str:
    if not text:
        return "Unscrapable"
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT_TEXT},
                {"role": "user", "content": f"Categorize {domain} using the plain text scraped below:\n{text[:MAX_TEXT_LEN]}"},
            ],
            temperature=0.0,
        )
        out = (resp.choices[0].message.content or "").strip()
        if out not in VALID_LABELS:
            first = out.splitlines()[0].strip()
            out = first if first in VALID_LABELS else "Unclear"
        return out
    except Exception as e:
        print(f"[LLM] Exception: {e}")
        return "Unclear"

# --- WORKER ---
def process_row(row_idx: int, domain: str) -> tuple[int, str]:
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
                print(f"[WORKER] Exception: {e}")
            results[ridx] = label

    # Zapis bucketu do kolumny B
    bucket_len = end - start + 1
    col_b = []
    for offset in range(bucket_len):
        ridx = start + offset
        col_b.append([results.get(ridx, "")])

    sh.update(values=col_b, range_name=f"B{start}:B{end}")
