import requests
from bs4 import BeautifulSoup
import gspread
import os
import time
from urllib.parse import urlparse

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("Classify company").worksheet("to_classify")

start_value = 1
end_value = 6000

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

domain_resellers = ["godaddy.com", "sedo.com", "dan.com", "namecheap.com"]

death_keywords = [
    "buy this domain", "domain for sale", "this domain is for sale", "expired domain", 
    "this site can’t be reached", "for inquiries contact", "parking page", "available for purchase",
    "403 forbidden", "not found", "page not found", "error 404"
]

def get_website_status(url):
    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        final_url = response.url
        parsed_original = urlparse(url)
        parsed_final = urlparse(final_url)
        final_domain = parsed_final.netloc.lower()  # Prawidłowe pobranie finalnej domeny

        if response.status_code in [404, 410] or not response.text.strip():
            return "dead"
        elif response.status_code in [403, 429]:
            return "unknown"
        elif response.status_code >= 500:
            return "dead"

        redirected = parsed_original.netloc != parsed_final.netloc

        # Sprawdzenie, czy domena końcowa należy do resellerów domen lub zawiera frazy sprzedaży
        if any(reseller in final_domain for reseller in domain_resellers) or "forsale" in final_url:
            return "dead"

        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=" ").strip().lower()
        
        # Sprawdzenie słów kluczowych wskazujących na "dead"
        if any(keyword in text for keyword in death_keywords):
            return "dead"

        if redirected:
            original_domain_parts = parsed_original.netloc.split('.')[-2:]
            final_domain_parts = parsed_final.netloc.split('.')[-2:]
            
            # Jeśli zmiana dotyczy tylko TLD (.de -> .com), traktujemy jako alive
            if original_domain_parts[0] == final_domain_parts[0]:
                return "alive"
            return f"forward: {final_domain}"
        
        # Domyślnie nie zakładamy, że strona jest alive, jeśli nie spełnia warunków powyżej
        return "alive" if text else "unknown"
    except requests.exceptions.RequestException:
        return "unknown"

for i in range(start_value, end_value+1):
    time.sleep(2)
    name = sh.acell("A"+str(i)).value
    url = "http://"+str(name)
    try:
        status = get_website_status(url)
        sh.update_acell("B"+str(i), status)
    except requests.exceptions.RequestException as e:
        sh.update_acell("B"+str(i), "unknown")