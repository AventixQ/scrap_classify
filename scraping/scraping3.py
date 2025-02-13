import requests
from bs4 import BeautifulSoup
import gspread
from gpt_classification3 import classify
import os
import time

# Initialize Google Sheets
gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("SP-SHOPS_CLASSIFICATION").worksheet("company_ok")

# Configuration
start_value = 1
end_value = 11000
bucket_size = 500
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

for bucket_start in range(start_value, end_value + 1, bucket_size):
    bucket_end = min(bucket_start + bucket_size - 1, end_value)

    # Read a range of rows from Google Sheets
    names = sh.get(f"A{bucket_start}:A{bucket_end}")

    for index, row in enumerate(names, start=bucket_start):
        name = row[0] if row else None

        if not name:
            print(f"Row {index}: No name provided")
            sh.update_acell(f"B{index}", "No name")
            continue

        url = "http://" + str(name)
        try:
            response = requests.get(url, headers=headers, timeout=4)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                text = soup.get_text(separator=" ").strip()
                clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

                classification = classify(clean_text)
                sh.update_acell(f"B{index}", classification)
            elif response.status_code == 403:
                soup = BeautifulSoup(response.content, "html.parser")
                text = soup.get_text(separator=" ").strip()
                clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

                classification = classify(clean_text)
                sh.update_acell(f"B{index}", f"HTTP {response.status_code}")
            else:
                #sh.update_acell(f"B{index}", f"HTTP {response.status_code}")
                print(f"Row {index}: Cannot download site. Code: {response.status_code}")

        except requests.exceptions.SSLError:
            #sh.update_acell(f"B{index}", "SSL Error")
            print(f"Row {index}: SSL certificate error")

        except Exception as e:
            #sh.update_acell(f"B{index}", "Other")
            print(f"Row {index}: Unknown error: {e}")
