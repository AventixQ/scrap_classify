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

import os, re, ssl, urllib.request, urllib.parse, gspread
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import local
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# -------------------- LOAD ENV --------------------
load_dotenv()

# -------------------- CONFIG ----------------------
START_ROW           = 94      # jeśli A1 to nagłówek, zaczynamy od 2
END_ROW             = 98
BUCKET_SIZE         = 100
MAX_THREADS         = 5
MAX_TEXT_LEN        = 12000
REQUEST_TIMEOUT_S   = 60
LLM_PROMPT_TEMPLATE = "llm_prompt.txt"

SPREADSHEET_NAME    = "EBE26 - Oct - CFS / Visitors / Inbound - forms"
WORKSHEET_NAME      = "CFS classification"

# -------------------- GOOGLE SHEETS ----------------
def _mask(s: str | None) -> str | None:
    if not s:
        return None
    return s[:2] + "…" + s[-2:] if len(s) > 4 else "…"

print("[ENV] CREDS_FILE:", os.getenv("CREDS_FILE"))
print("[ENV] BRD_CUSTOMER:", _mask(os.getenv("BRD_CUSTOMER")))
print("[ENV] BRD_HOST:", os.getenv("BRD_HOST", "brd.superproxy.io"))
print("[ENV] OPENAI_API_KEY set?:", bool(os.getenv("OPENAI_API_KEY")))

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
print(f"[GS] Opened spreadsheet '{SPREADSHEET_NAME}' / worksheet '{sh.title}'")

# -------------------- OPENAI ----------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
VALID_LABELS = {"Shop", "Service Provider"}

def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

PROMPT_TEXT = load_prompt(LLM_PROMPT_TEMPLATE)

# -------------------- BRIGHT DATA ------------------
BRD_CUSTOMER = os.getenv("BRD_CUSTOMER")
BRD_PASSWORD = os.getenv("BRD_PASSWORD")
BRD_HOST     = os.getenv("BRD_HOST", "brd.superproxy.io")
BRD_PORT     = os.getenv("BRD_PORT", "33335")
assert BRD_CUSTOMER and BRD_PASSWORD, "Brak BRD_CUSTOMER/BRD_PASSWORD w .env"

# -------------------- HELPERS ----------------------
_tls = local()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

COOKIE_NOISE = (
    "cookie", "gdpr", "consent", "We use cookies", "Używamy plików cookie",
    "Wir verwenden Cookies", "Usamos cookies", "Wij gebruiken cookies", "RODO"
)

def normalize_domain(raw: str) -> str:
    """Akceptuje wpisy typu 'https://site.com/path', zwraca 'site.com'."""
    s = raw.strip()
    if not s:
        return ""
    # dopisz protokół jeśli jest brak, aby urlparse zadziałał
    if "://" not in s:
        s = "http://" + s
    try:
        p = urllib.parse.urlparse(s)
        host = p.netloc or p.path  # w razie 'http://example.com' albo 'example.com'
        # usuń port i leading 'www.'
        host = host.split("@")[-1].split(":")[0].strip().lstrip(".")
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return raw.strip()

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
    # Ten sam schemat logowania jak w Twoim teście
    proxy = f"http://{BRD_CUSTOMER}:{BRD_PASSWORD}@{BRD_HOST}:{BRD_PORT}"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'https': proxy, 'http': proxy}),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
    )
    opener.addheaders = [(k, v) for k, v in HEADERS.items()]
    return opener

def get_thread_opener() -> urllib.request.OpenerDirector:
    if not hasattr(_tls, "opener"):
        _tls.opener = build_opener()
    return _tls.opener

# -------------------- SCRAPE -----------------------
def scrape_domain(domain: str) -> tuple[str, str | None]:
    """
    Zwraca (plain_text, err_code).
    err_code == None  → OK
    err_code == str   → 'OpenError:...' / 'DecodeError:...' / 'NoContent'
    """
    url = "https://" + domain
    opener = get_thread_opener()
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with opener.open(req, timeout=REQUEST_TIMEOUT_S) as resp:
            raw = resp.read()
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

# -------------------- LLM --------------------------
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

# -------------------- WORKER -----------------------
def process_row(row_idx: int, raw_val: str) -> tuple[int, str]:
    dom = normalize_domain(raw_val)
    if not is_valid_domain(dom):
        print(f"[SKIP] row {row_idx}: not a valid domain -> '{raw_val}' -> '{dom}'")
        return row_idx, "Unscrapable"
    text, err = scrape_domain(dom)
    if err:
        print(f"[SCRAPE] row {row_idx} {dom}: {err}")
        return row_idx, "Unscrapable"
    label = classify_llm(text, dom)
    print(f"[OK] row {row_idx} {dom}: {label}")
    return row_idx, label

# -------------------- SAFE UPDATE ------------------
def safe_update(range_name: str, values: list[list[str]]):
    """Nie wysyłaj pustych aktualizacji."""
    if not values or all((not v or not (v[0] or "").strip()) for v in values):
        print(f"[SKIP] Empty update for {range_name}")
        return
    sh.update(values=values, range_name=range_name)
    print(f"[GS] Updated {range_name} with {len(values)} rows")

# -------------------- MAIN LOOP --------------------
print("[INIT] START_ROW:", START_ROW, "END_ROW:", END_ROW, "BUCKET_SIZE:", BUCKET_SIZE)

for start in range(START_ROW, END_ROW + 1, BUCKET_SIZE):
    end = min(start + BUCKET_SIZE - 1, END_ROW)
    rng_a = f"A{start}:A{end}"
    rows_a = sh.get(rng_a)
    print(f"[READ] {rng_a}: got {len(rows_a)} rows total")

    # przygotuj listę (row_index, cell_value) tylko dla niepustych A
    domains = [(i, r[0].strip()) for i, r in enumerate(rows_a, start=start) if r and r[0].strip()]
    print(f"[WORK] Non-empty A-cells in {rng_a}: {len(domains)}")

    if not domains:
        # nic nie robimy – i nie czyścimy kolumny B
        continue

    # Przetwarzanie równoległe
    results: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        futs = {ex.submit(process_row, idx, val): idx for idx, val in domains}
        for fut in as_completed(futs):
            idx = futs[fut]
            try:
                ridx, label = fut.result()
            except Exception as e:
                ridx, label = idx, "Unclear"
                print(f"[WORKER] Exception: row={idx} err={e}")
            results[ridx] = label

    # Pobierz istniejące B, aby nie kasować wartości tam, gdzie A jest puste
    rng_b = f"B{start}:B{end}"
    existing_b = sh.get(rng_b)  # może być [] albo lista o długości <= bucket
    # Zbuduj wartości do zapisu: tylko nadpisujemy te wiersze, które przetworzyliśmy
    col_b: list[list[str]] = []
    bucket_len = end - start + 1
    for offset in range(bucket_len):
        ridx = start + offset
        if ridx in results:
            col_b.append([results[ridx]])
        else:
            # zachowaj istniejące (jeśli jest), w przeciwnym razie puste
            if offset < len(existing_b) and existing_b[offset]:
                col_b.append([existing_b[offset][0]])
            else:
                col_b.append([""])

    safe_update(rng_b, col_b)

print("[DONE] All buckets processed.")
