import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
API_TOKEN = os.getenv("WOODPECKER_API_KEY")

BASE_URL = 'https://api.woodpecker.co/rest/v1/prospects'
PER_PAGE = 1000
STOP_DATE = '2025-03-01T00:00:00+0000'
all_data = []
page = 0

while True:
    url = f'{BASE_URL}?per_page={PER_PAGE}&page={page}'
    headers = {
        'x-api-key': API_TOKEN
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Błąd API: {response.status_code}")
        break

    data = response.json()

    if not isinstance(data, list) and (len(data) == 0 or len(data)==1):
        print(f"Koniec danych na stronie {page}")
        break
    if isinstance(data, list):
        df = pd.DataFrame(data)
        df['last_contacted'] = pd.to_datetime(df['last_contacted'], errors='coerce', utc=True)  # Konwersja na datetime
        df = df[df['last_contacted'] >= pd.to_datetime(STOP_DATE)]

        all_data.append(df)
        print(f"Done for page {page}")

    page += 1

final_df = pd.concat(all_data, ignore_index=True)

final_df.to_csv('woodpecker_replied_prospects_after_march_2025.csv', index=False)
print("✅ Zapisano dane do 'woodpecker_replied_prospects_after_march_2025.csv'")
