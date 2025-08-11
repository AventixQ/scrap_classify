# pipeline.py
import os
import re
import csv
import json
import time
import argparse
import asyncio
from typing import List, Dict, Any, Union

from dotenv import load_dotenv
from openai import OpenAI
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
import requests

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LINKS_CSV = "links_to_scrap.csv"
EXTRACTED_JSONL = "extracted_data.jsonl"
SPEAKERS_CSV = "speakers.csv"
COMPANIES_CSV = "companies.csv"

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

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

# -------------------
# Helpers
# -------------------
def url_matches(url: str, base_url: str, match_keys: List[str], match_regex: Union[str, None]) -> bool:
    if match_regex:
        return re.search(match_regex, url) is not None
    if match_keys:
        return any(k.strip() and (k.strip() in url) for k in match_keys)
    # fallback – tak jak wcześniej
    return base_url.rstrip("/") in url

# -------------------
# KROK 1: CRAWLER
# -------------------
async def save_links_to_csv(links: List[str], links_csv: str) -> None:
    with open(links_csv, mode='w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["URL"])
        for u in links:
            w.writerow([u])

async def crawl_and_save_links(base_url: str, links_csv: str, match_keys: List[str], match_regex: Union[str, None],
                               max_depth: int = 2) -> int:
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=max_depth, include_external=False),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(base_url, config=config)
        all_urls = [r.url for r in results]
        filtered = [r for r in results if url_matches(r.url, base_url, match_keys, match_regex)]
        links = [r.url for r in filtered]

        await save_links_to_csv(links, links_csv)
        print(f"[crawl] Crawled: {len(all_urls)} | Filtered: {len(links)} | Saved -> {links_csv}")
        if match_regex:
            print(f"[crawl] Used regex filter: {match_regex}")
        elif match_keys:
            print(f"[crawl] Used keys: {match_keys}")
        else:
            print(f"[crawl] Used base_url containment filter.")
        return len(links)

# -------------------
# KROK 2: SCRAPE + GPT
# -------------------
def fetch_page_html(url: str) -> Union[str, None]:
    try:
        r = requests.get(url, headers=HEADERS_HTTP, timeout=15)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"[scrape] Error fetching {url}: {e}")
        return None

def extract_details(page_html: str, mode: str, client: OpenAI) -> str:
    prompt = PROMPT_SPEAKER if mode == "speaker" else PROMPT_COMPANY
    full_prompt = f"{prompt}\nHTML:\n{page_html[:127000]}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.2
    )
    return resp.choices[0].message.content

def scrape_links_from_csv_to_jsonl(links_csv: str, out_jsonl: str, mode: str, delay_sec: float = 2.5) -> int:
    client = OpenAI(api_key=OPENAI_API_KEY)

    with open(links_csv, "r", encoding="utf-8") as f:
        urls = [row[0] for row in csv.reader(f) if row and row[0] != "URL"]

    if not urls:
        print("[scrape] No URLs to process.")
        return 0

    processed = 0
    with open(out_jsonl, "a", encoding="utf-8") as out:
        for i, url in enumerate(urls, 1):
            html = fetch_page_html(url)
            if not html:
                print(f"[scrape] Skipping (no html): {url}")
                continue

            data_text = extract_details(html, mode, client)
            try:
                data_obj = json.loads(data_text)
            except json.JSONDecodeError:
                data_obj = {"raw": data_text}

            out.write(json.dumps({"url": url, "data": data_obj}, ensure_ascii=False) + "\n")
            out.flush()
            processed += 1

            print(f"[scrape] {processed}/{len(urls)}: {url}")
            time.sleep(delay_sec)

    print(f"[scrape] Completed. Wrote {processed} lines to {out_jsonl}")
    return processed

# -------------------
# KROK 3: JSONL -> CSV
# (regexy jak u Ciebie; bez zmian logiki)
# -------------------
def extract_and_save_to_csv(input_jsonl_filename: str, output_csv_filename: str, mode: str = "speaker") -> None:
    mode = mode.lower().strip()
    if mode not in {"speaker", "company"}:
        raise ValueError("mode must be 'speaker' or 'company'")

    fenced_block_regex = re.compile(r"```(?:\s*json)?\s*(\{.*?\})\s*```", re.S | re.I)

    sp_company_name      = re.compile(r'"Company\s+Name"\s*:\s*"([^"]*)"', re.I)
    sp_company_domain    = re.compile(r'"Company\s+Domain"\s*:\s*"([^"]*)"', re.I)
    sp_first             = re.compile(r'"Speaker\s+First\s+name"\s*:\s*"([^"]*)"', re.I)
    sp_last              = re.compile(r'"Speaker\s+Last\s+name"\s*:\s*"([^"]*)"', re.I)
    sp_position          = re.compile(r'"Speaker\s+position"\s*:\s*"([^"]*)"', re.I)
    sp_topic             = re.compile(r'"Topic\s+of\s+talk"\s*:\s*"([^"]*)"', re.I)
    sp_description       = re.compile(r'"Description\s+of\s+talk"\s*:\s*"([^"]*)"', re.I)
    sp_language          = re.compile(r'"Language"\s*:\s*"([^"]*)"', re.I)
    sp_datehour          = re.compile(r'"Date\s+and\s+hour"\s*:\s*"([^"]*)"', re.I)

    co_company_name      = re.compile(r'"Company\s+Name"\s*:\s*"([^"]*)"', re.I)
    co_company_domain    = re.compile(r'"Company\s+Domain"\s*:\s*"([^"]*)"', re.I)
    co_email             = re.compile(r'"Email"\s*:\s*(?:"([^"]*)"|([^,\n}]+))', re.I)
    co_phone             = re.compile(r'"Phone\s+Number"\s*:\s*(?:"([^"]*)"|([^,\n}]+))', re.I)
    co_address           = re.compile(r'"Address"\s*:\s*"([^"]*)"', re.I)
    co_hall              = re.compile(r'"Hall\s+Number"\s*:\s*"([^"]*)"', re.I)
    co_stand             = re.compile(r'"Stand\s+Number"\s*:\s*"([^"]*)"', re.I)
    co_description       = re.compile(r'"Description"\s*:\s*"([^"]*)"', re.I)
    co_linkedin          = re.compile(r'"Linkedin\s+link"\s*:\s*"([^"]*)"', re.I)

    def pick_group(m):
        if not m:
            return ""
        last = m.lastindex or 0
        for i in range(1, last + 1 if last else 2):
            val = m.group(i) if i <= last else m.group(1)
            if val:
                return val.strip()
        return ""

    def extract_speaker(data_string: str):
        m = fenced_block_regex.search(data_string)
        payload = m.group(1) if m else data_string
        return {
            "Company Name":        pick_group(sp_company_name.search(payload)),
            "Company Domain":      pick_group(sp_company_domain.search(payload)),
            "Speaker First name":  pick_group(sp_first.search(payload)),
            "Speaker Last name":   pick_group(sp_last.search(payload)),
            "Speaker position":    pick_group(sp_position.search(payload)),
            "Topic of talk":       pick_group(sp_topic.search(payload)),
            "Description of talk": pick_group(sp_description.search(payload)),
            "Language":            pick_group(sp_language.search(payload)),
            "Date and hour":       pick_group(sp_datehour.search(payload)),
        }

    def extract_company(data_string: str):
        m = fenced_block_regex.search(data_string)
        payload = m.group(1) if m else data_string
        return {
            "Company Name":   pick_group(co_company_name.search(payload)),
            "Company Domain": pick_group(co_company_domain.search(payload)),
            "Email":          pick_group(co_email.search(payload)),
            "Phone Number":   pick_group(co_phone.search(payload)),
            "Address":        pick_group(co_address.search(payload)),
            "Hall Number":    pick_group(co_hall.search(payload)),
            "Stand Number":   pick_group(co_stand.search(payload)),
            "Description":    pick_group(co_description.search(payload)),
            "Linkedin link":  pick_group(co_linkedin.search(payload)),
        }

    speaker_header = [
        "URL","Company Name","Company Domain","Speaker First name","Speaker Last name",
        "Speaker position","Topic of talk","Description of talk","Language","Date and hour"
    ]
    company_header = [
        "URL","Company Name","Company Domain","Email","Phone Number",
        "Address","Hall Number","Stand Number","Description","Linkedin link"
    ]
    header = speaker_header if mode == "speaker" else company_header

    with open(output_csv_filename, mode='w', newline='', encoding='utf-8') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(header)

        with open(input_jsonl_filename, 'r', encoding='utf-8') as in_file:
            for line in in_file:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                url = item.get("url", "")
                data_field: Any = item.get("data", "")

                if isinstance(data_field, dict) and "raw" not in data_field:
                    data_string = json.dumps(data_field, ensure_ascii=False)
                elif isinstance(data_field, dict) and "raw" in data_field:
                    data_string = str(data_field.get("raw", ""))
                else:
                    data_string = str(data_field)

                extracted = extract_speaker(data_string) if mode == "speaker" else extract_company(data_string)
                row = [url] + [extracted.get(col, "") for col in header[1:]]
                writer.writerow(row)

    print(f"[to_csv] Zapisano dane do pliku {output_csv_filename}")

# -------------------
# Orkiestracja
# -------------------
def run_pipeline(base_url: str, mode: str, match_keys: List[str], match_regex: Union[str, None], max_depth: int):
    links_found = asyncio.run(crawl_and_save_links(base_url, LINKS_CSV, match_keys, match_regex, max_depth=max_depth))
    if links_found == 0:
        print("[pipeline] Brak linków po crawl — kończę.")
        return

    processed = scrape_links_from_csv_to_jsonl(LINKS_CSV, EXTRACTED_JSONL, mode=mode, delay_sec=2.5)
    if processed == 0:
        print("[pipeline] Nic nie zescrapowano — kończę.")
        return

    out_csv = SPEAKERS_CSV if mode == "speaker" else COMPANIES_CSV
    extract_and_save_to_csv(EXTRACTED_JSONL, out_csv, mode=mode)

# -------------------
# CLI
# -------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="End-to-end crawl -> scrape -> JSONL -> CSV")
    ap.add_argument("--base-url", required=True, help="Punkt startowy crawl4ai")
    ap.add_argument("--mode", choices=["speaker","company"], default="speaker", help="Tryb ekstrakcji danych")
    ap.add_argument("--match-key", action="append", default=[],
                    help="Substring do dopasowania URL (możesz podać wiele razy lub po przecinku).")
    ap.add_argument("--match-regex", default=None, help="Regex do filtrowania URL-i (zamiast --match-key).")
    ap.add_argument("--max-depth", type=int, default=2, help="Głębokość BFS dla crawl4ai")

    args = ap.parse_args()
    if not OPENAI_API_KEY:
        raise SystemExit("Brak OPENAI_API_KEY w środowisku.")

    # pozwól na listę po przecinku w jednym --match-key
    keys: List[str] = []
    for k in args.match_key:
        keys.extend([p.strip() for p in k.split(",") if p.strip()])

    run_pipeline(args.base_url, args.mode, keys, args.match_regex, args.max_depth)
