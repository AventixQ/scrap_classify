from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import csv

import re

service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Działa w tle, jeśli nie chcesz okna przeglądarki
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

def extract_followers(text):
    # Znalezienie słowa "FOLLOWERS" i pobranie liczby poniżej
    match = re.search(r'FOLLOWERS\s+([\d,\s]+)', text)

    if match:
        # Usuwamy spacje i przecinki, aby dostać czystą liczbę
        followers = match.group(1).replace(",\n", "").replace("\n", "")
        return int(followers)  # Konwersja na liczbę
    else:
        return "Nie znaleziono liczby followersów"

def get_followers_instastatistics(username):

    # Uruchomienie przeglądarki
    driver = webdriver.Chrome(service=service, options=options)
    
    url = f"https://instastatistics.com/#!/{username}"
    driver.get(url)
    time.sleep(8)  # Czekamy, aż dane się załadują

    full_text = driver.find_element(By.TAG_NAME, "body").text
    print(full_text)

    driver.quit()
    return extract_followers(full_text)

input_file = "to_scrap.csv"  # Plik wejściowy z username
output_file = "result.csv"  # Plik wynikowy

# Wczytujemy użytkowników
df = pd.read_csv(input_file, header=None, names=["username"])

# 📌 Otwieramy plik CSV do zapisu wyników
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=";")
    writer.writerow(["username", "followers"])  # Nagłówki

    # 📌 Pętla przez użytkowników
    for index, row in df.iterrows():
        username = row["username"]
        print(f"Scrapuję: {username}...")

        try:
            followers = get_followers_instastatistics(username)  # Wyciągamy liczbę followersów
        except Exception as e:
            followers = f"ERROR: {e}"

        # 📌 Zapisujemy wynik
        writer.writerow([username, followers])
        f.flush()

        print(f"✔ {username}: {followers} followersów zapisano!")

print("\n✅ Wszystkie dane zapisane do result.csv")
