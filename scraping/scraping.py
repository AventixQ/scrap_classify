import requests
from bs4 import BeautifulSoup
import gspread
from gpt_classification import classify
import os

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE25-Matrix").sheet1

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

start_value = 2
end_value = 7

for i in range(start_value, end_value+1):
    name = sh.acell("c"+str(i)).value
    #print(name)

    url = "http://"+name

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text(separator=" ").strip()
        clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

        response = classify(clean_text)
        #print(response)
        sh.update_acell("g"+str(i),response)

    else:
        print(f"Nie udało się pobrać strony. Kod statusu: {response.status_code}")
