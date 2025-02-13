import requests
from bs4 import BeautifulSoup
import gspread
from gpt_classification3 import classify
import os
import time

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))

##############################################################
################## Choose your google sheet ##################
##############################################################
sh = gc.open("SP-SHOPS_CLASSIFICATION_2").worksheet("company_ok")
##############################################################
start_value = 1
end_value = 20000
##############################################################
##############################################################

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

for i in range(start_value, end_value+1):
    time.sleep(2)
    name = sh.acell("a"+str(i)).value
    #print(name)

    url = "http://"+str(name)
    try:
        response = requests.get(url, headers=headers, timeout=4)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text(separator=" ").strip()
            clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

            response = classify(clean_text)
            #print(response)
            sh.update_acell("b"+str(i),response)
        else:
            print(f"Cannot download site. Code: {response.status_code}")
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error: {err} (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except: print("Tell me why...")
