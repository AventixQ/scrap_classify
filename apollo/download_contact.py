import requests
from dotenv import load_dotenv
import os
load_dotenv()

API_KEY = os.getenv("APOLLO_API_KEY")

url = "https://api.apollo.io/api/v1/contacts/search"

headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
    "accept": "application/json",
    "Cache-Control": 'no-cache'
}

payload = {
    "query": "Software Engineer",
    "page": 1,
    "per_page": 100
}

response = requests.post(url, headers=headers, json=payload)

if response.status_code == 200:
    data = response.json()
    contacts = data.get("contacts", [])
    #print(contacts)

    for contact in contacts:
        first_name = contact.get("first_name", "N/A")
        last_name = contact.get("last_name", "N/A")
        company_name = contact.get("organization_name", "N/A")
        print(f"{first_name} {last_name} - {company_name}")
else:
    print(f"Request failed with status code: {response.status_code}")
    print(f"Response: {response.text}")
