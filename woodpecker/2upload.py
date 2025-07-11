import requests
import pandas as pd
from dotenv import load_dotenv
import os
import time
import re

load_dotenv()
API_TOKEN = os.getenv("WOODPECKER_API_KEY")

OUTPUT_FILE = "woodpecker_bounced_emails.csv"
BASE_URL = "https://api.woodpecker.co/rest/v2/inbox/messages"
PER_PAGE = 50
HEADERS = {
    "x-api-key": API_TOKEN
}
STATUS = ["BOUNCED","OPT_OUT"]

def get_messages(cursor=None,status=None):
    if cursor:
        url = f"{BASE_URL}?per_page={PER_PAGE}&next_page_cursor={cursor}"
    else:
        url = f"{BASE_URL}?per_page={PER_PAGE}"
    if status: url += f'&prospect_status={status}'

    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"GET request failed: {response.status_code}, {response.text}")

def extract_email_from_html(html):
    if not html:
        return None
    # Spróbuj znaleźć pierwszy email (pasujący do wzoru z przykładów)
    match = re.search(r'[\w\.-]+@[\w\.-]+', html)
    return match.group(0) if match else None

def save_to_csv(data, is_first_batch=False):
    mode = 'w' if is_first_batch else 'a'
    header = is_first_batch
    df = pd.DataFrame(data)
    with open(OUTPUT_FILE, mode, newline='', encoding='utf-8') as f:
        df.to_csv(f, header=header, index=False)
        f.flush()
        os.fsync(f.fileno())

if __name__ == "__main__":
    next_cursor = None
    page = 1
    first_batch = True

    try:
        for status in STATUS:    
            while True:
                print(f"📥 Przetwarzam stronę {page}...")
                data = get_messages(next_cursor,status)

                messages = data.get("content", [])
                if not messages:
                    print("✅ Brak kolejnych wiadomości.")
                    break

                results = []
                for msg in messages:
                    html = msg.get("body", {}).get("html", "")
                    email = extract_email_from_html(html)
                    if email:
                        results.append({
                            "stamp": msg.get("stamp"),
                            "campaign_name": msg.get("campaign", {}).get("name"),
                            "bounced_email": email,
                            "status": status
                        })

                print(f"✅ Pobrano {len(results)} rekordów z tej strony.")

                if results:
                    save_to_csv(results, is_first_batch=first_batch)
                    first_batch = False
                #print("🧪 Klucze w odpowiedzi:", data.keys())
                #print("📦 Surowa odpowiedź:", data)

                next_cursor = data.get("pagination", {}).get("next_page_cursor")
                #print(next_cursor)
                if not next_cursor:
                    print("🏁 Zakończono pobieranie – brak kolejnych stron.")
                    break

                page += 1
                time.sleep(0.5)

            print(f"📄 Gotowe! Dane zapisane do pliku: {OUTPUT_FILE}")

    except Exception as e:
        print("❌ Błąd:", e)
