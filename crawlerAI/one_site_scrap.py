import os
import csv
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

INPUT_CSV = "links_to_scrap.csv"  # Plik CSV z linkami (każdy link w nowym wierszu)
OUTPUT_JSON = "extracted_data.json"

def extract_details(page_html):
    """Użycie GPT-4o mini do ekstrakcji szczegółowych danych."""
    prompt = f"""
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
    HTML:
    {page_html[:127000]}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    return response.choices[0].message.content

def fetch_page_html(url):
    """ Pobiera stronę w postaci HTML. """
    try:
        response = requests.get(url, headers=headers,timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def scrape_links():
    urls = []
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        urls = [row[0] for row in reader if row]  # Pobieranie URL-i z pliku
    
    extracted_data = []
    
    for i, url in enumerate(urls, start=1):
        html_content = fetch_page_html(url)
        if html_content:
            data = extract_details(html_content)
            extracted_data.append({"url": url, "data": data})
            #print(html_content)
            
            with open(OUTPUT_JSON, "a", encoding="utf-8") as f:
                json.dump({"url": url, "data": data}, f, indent=4, ensure_ascii=False)
                f.write(",\n")  # Dodanie nowej linii do JSON
                f.flush()  # Wymuszenie zapisu na dysk
            print(f"Processed {i}/{len(urls)}: {url}")
            time.sleep(3)
        else:
            print(f"Failed to fetch: {url}")
    
    print("Scraping completed.")

if __name__ == "__main__":
    scrape_links()