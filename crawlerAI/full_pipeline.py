#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os
import re
import csv
import sys
import time
import json
import ssl
import argparse
import urllib.parse
import urllib.request
from typing import Optional, Tuple, List, Set, Deque
from collections import deque

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# --- Selenium (opcjonalne) ---
SELENIUM_AVAILABLE = True
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.common.exceptions import WebDriverException
    # Użycie webdriver-manager jeśli dostępny (opcjonalnie)
    try:
        from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
        HAVE_WDM = True
    except Exception:
        HAVE_WDM = False
except Exception:
    SELENIUM_AVAILABLE = False
    HAVE_WDM = False

# ------------------- ENV / CONST -------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

EXTRACTED_LINKS_CSV = "extracted_links.csv"
RESULTS_CSV = "results_for_extracted_links.csv"

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
}

REQUEST_TIMEOUT_S = 15
BD_TIMEOUT_S = 60

# Bright Data Web Unlocker
BRD_CUSTOMER = os.getenv("BRD_CUSTOMER")
BRD_PASSWORD = os.getenv("BRD_PASSWORD")
BRD_HOST     = os.getenv("BRD_HOST", "brd.superproxy.io")
BRD_PORT     = os.getenv("BRD_PORT", "33335")
BRIGHTDATA_ENABLED = bool(BRD_CUSTOMER and BRD_PASSWORD)

# ------------------- utils -------------------

def host_of(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""

def normalize_abs(base: str, href: str) -> str:
    try:
        return urllib.parse.urljoin(base, href)
    except Exception:
        return href

# ------------------- Fetchers (requests / selenium / brightdata) -------------------

def fetch_via_requests(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS_HTTP, timeout=REQUEST_TIMEOUT_S)
        r.raise_for_status()
        # odfiltrowanie podejrzanie małych odpowiedzi
        text = r.text or ""
        if not text.strip():
            return None
        return text
    except requests.RequestException:
        return None

class LazySelenium:
    """Tworzy pojedynczą instancję drivera, żyjącą przez cały run."""
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def ensure(self) -> Optional[webdriver.Chrome]:
        if not SELENIUM_AVAILABLE:
            return None
        if self.driver is not None:
            return self.driver
        try:
            opts = ChromeOptions()
            if self.headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument(f"--user-agent={HEADERS_HTTP['User-Agent']}")
            if HAVE_WDM:
                path = ChromeDriverManager().install()  # type: ignore
                self.driver = webdriver.Chrome(path, options=opts)
            else:
                # Zakłada, że chromedriver jest w PATH
                self.driver = webdriver.Chrome(options=opts)
            self.driver.set_page_load_timeout(30)
            return self.driver
        except Exception:
            self.driver = None
            return None

    def get_html(self, url: str) -> Optional[str]:
        drv = self.ensure()
        if drv is None:
            return None
        try:
            drv.get(url)
            time.sleep(1.0)
            html = drv.page_source
            return html if html and html.strip() else None
        except WebDriverException:
            return None

    def close(self):
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

LAZY_SELENIUM = LazySelenium(headless=True)

def build_brightdata_opener() -> urllib.request.OpenerDirector:
    assert BRIGHTDATA_ENABLED, "Bright Data creds missing (BRD_CUSTOMER/BRD_PASSWORD)"
    proxy = f"http://{BRD_CUSTOMER}:{BRD_PASSWORD}@{BRD_HOST}:{BRD_PORT}"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'https': proxy, 'http': proxy}),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
    )
    opener.addheaders = [(k, v) for k, v in HEADERS_HTTP.items()]
    return opener

def fetch_via_brightdata(url: str) -> Optional[str]:
    if not BRIGHTDATA_ENABLED:
        return None
    try:
        opener = build_brightdata_opener()
        req = urllib.request.Request(url, headers=HEADERS_HTTP)
        raw = opener.open(req, timeout=BD_TIMEOUT_S).read()
        html = raw.decode("utf-8", errors="ignore")
        return html if html.strip() else None
    except Exception:
        return None


def get_html_with_fallback(url: str) -> Tuple[Optional[str], str]:
    """Zwraca (html, source): source in {requests, selenium, brightdata, ""}
    Kolejność:
      1) requests+bs4
      2) selenium (jeden driver przez cały run)
      3) brightdata (jeśli skonfigurowane)
    """
    # 1) requests
    html = fetch_via_requests(url)
    if html:
        return html, "requests"
    # 2) selenium
    html = LAZY_SELENIUM.get_html(url)
    if html:
        return html, "selenium"
    # 3) brightdata
    html = fetch_via_brightdata(url)
    if html:
        return html, "brightdata"
    return None, ""

# ------------------- Link discovery (BFS) -------------------

def extract_links(base_url: str, html: str) -> List[str]:
    out: Set[str] = set()
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        absu = normalize_abs(base_url, href)
        out.add(absu)
    return list(out)


def bfs_collect_links(start_url: str, max_depth: int, same_host_only: bool = True) -> Set[str]:
    visited: Set[str] = set()
    collected: Set[str] = set()
    start_host = host_of(start_url)

    q: Deque[Tuple[str, int]] = deque([(start_url, 0)])

    while q:
        url, depth = q.popleft()
        if url in visited:
            continue
        visited.add(url)

        html, src = get_html_with_fallback(url)
        if not html:
            continue

        links = extract_links(url, html)
        for u in links:
            if same_host_only and host_of(u) != start_host:
                continue
            if u not in collected:
                collected.add(u)
            if depth + 1 <= max_depth and u not in visited:
                q.append((u, depth + 1))

        # delikatne tempo, żeby nie zalać strony
        time.sleep(0.2)

    return collected

# ------------------- LLM (gpt-4o-mini) -------------------

def llm_summarize_html(page_html: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = (
        "Przeczytaj poniższy HTML strony i wyciągnij najważniejsze informacje (jeśli się da): "
        "tytuł, opis, dane kontaktowe (email/telefon/adres), linki do sociali. "
        "Zwróć odpowiedź w czystym JSON z kluczami: title, description, emails, phones, address, socials, notes.\n\n"
        "HTML:\n" + page_html[:120000]
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""

# ------------------- CSV helpers -------------------

def write_extracted_links_csv(links: List[str], outfile: str = EXTRACTED_LINKS_CSV) -> int:
    uniq = sorted(set(links))
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["URL"])  # nagłówek
        for u in uniq:
            w.writerow([u])
    return len(uniq)


def read_links_csv(infile: str = EXTRACTED_LINKS_CSV) -> List[str]:
    out: List[str] = []
    with open(infile, "r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0] == "URL":
                continue
            out.append(row[0])
    return out


def append_result_row(url: str, source: str, model_output: str, outfile: str = RESULTS_CSV) -> None:
    new_file = not os.path.exists(outfile)
    with open(outfile, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["URL", "fetch_source", "model_output"])  # nagłówek
        w.writerow([url, source, model_output])

# ------------------- Orkiestracja -------------------

def main():
    ap = argparse.ArgumentParser(description="Prosty deep-scraper z fallbackiem (requests → selenium → brightdata)")
    ap.add_argument("--base-url", required=True, help="Punkt startowy do skanowania")
    ap.add_argument("--depth", type=int, default=1, help="Głębokość BFS (0 = tylko strona startowa)")
    ap.add_argument("--match-key", required=True, help="Substring, który musi wystąpić w URL (np. 'bewertung/info_')")
    ap.add_argument("--same-domain", action="store_true", help="Ogranicz do tej samej domeny (domyślnie TAK)")
    ap.add_argument("--no-llm", action="store_true", help="Nie odpalaj LLM po zebraniu linków")

    args = ap.parse_args()

    if not OPENAI_API_KEY and not args.no_llm:
        sys.exit("Brak OPENAI_API_KEY w środowisku.")

    same_host_only = True if args.same_domain else True  # default True

    # 1) Deep scrape linków
    print(f"[discover] Start BFS: depth={args.depth} base={args.base_url}")
    all_links = bfs_collect_links(args.base_url, max_depth=args.depth, same_host_only=same_host_only)
    print(f"[discover] Zebrano {len(all_links)} linków (przed filtrem)")

    # 2) Filtrowanie po match-key
    key = args.match_key.strip()
    matched = [u for u in all_links if key in u]
    print(f"[filter] Po kluczu '{key}' zostało {len(matched)} linków")

    # 3) Zapis extracted_links.csv
    count = write_extracted_links_csv(matched, EXTRACTED_LINKS_CSV)
    if count == 0:
        print("[done] Brak dopasowanych linków → kończę.")
        LAZY_SELENIUM.close()
        return
    print(f"[write] Zapisano {count} linków do {EXTRACTED_LINKS_CSV}")

    if args.no_llm:
        LAZY_SELENIUM.close()
        return

    # 4) Dla każdego linka: pobierz HTML (fallback) → LLM → zapisz CSV
    links_for_scrape = read_links_csv(EXTRACTED_LINKS_CSV)
    for i, url in enumerate(links_for_scrape, 1):
        html, src = get_html_with_fallback(url)
        if not html:
            print(f"[scrape] ({i}/{len(links_for_scrape)}) brak HTML: {url}")
            append_result_row(url, "", "")
            continue
        try:
            out = llm_summarize_html(html)
        except Exception as e:
            out = json.dumps({"error": str(e)})
        append_result_row(url, src, out)
        print(f"[scrape] ({i}/{len(links_for_scrape)}) via {src}: {url}")
        time.sleep(0.6)

    print(f"[done] Wyniki zapisane do {RESULTS_CSV}")
    LAZY_SELENIUM.close()


if __name__ == "__main__":
    main()
