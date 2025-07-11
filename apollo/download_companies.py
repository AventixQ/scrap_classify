import requests
import csv
import os
from dotenv import load_dotenv
import time
import json

load_dotenv()

API_KEY = os.getenv("APOLLO_API_KEY")

#url = "https://api.apollo.io/api/v1/mixed_companies/search?account_label_ids[]=67c8648c86bd160021ef8b86"
#url = "https://api.apollo.io/api/v1/mixed_companies/search?organization_num_employees_ranges[]=11%2C20&organization_num_employees_ranges[]=201%2C999999&organization_locations[]=netherlands"
url = "https://api.apollo.io/api/v1/mixed_companies/search?organization_num_employees_ranges[]=21%2C200&organization_locations[]=netherlands"

headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
    "accept": "application/json",
    "Cache-Control": 'no-cache'
}

response = requests.post(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    total_entries = data.get("pagination", {}).get("total_entries", 0)
    total_pages = data.get("pagination", {}).get("total_pages", 0)

    print(f"Total entries: {total_entries}")
    print(f"Total pages: {total_pages//10}")
    #print(response.json())
else: print("Ooopss")

page = 1
page_size = 100
filename = "companies_data.csv"
categories = ['name', 'domain', 'organization_revenue', 'organization_city', 'organization_country', 
              'website_url', 'linkedin_url', 'twitter_url', 'facebook_url', 'founded_year', 'market_cap', 'phone', 'alexa_ranking']

with open(filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=categories)
    writer.writeheader()

    while True:
        url_with_params = f"{url}&page={page}&per_page={page_size}"
        response = requests.post(url_with_params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            #print(data)
            companies = data.get("accounts", []) + data.get("organizations", []) # accounts

            if not companies:
                print("No more companies to fetch.")
                break

            for company in companies:
                row = {
                    'name': company.get('name', ''),
                    'domain': company.get('primary_domain', ''),
                    'organization_revenue': company.get('organization_revenue', ''),
                    'organization_city': company.get('organization_city', ''),
                    'organization_country': company.get('organization_country', ''),
                    'website_url': company.get('website_url', ''),
                    'linkedin_url': company.get('linkedin_url', ''),
                    'twitter_url': company.get('twitter_url', ''),
                    'facebook_url': company.get('facebook_url', ''),
                    'founded_year': company.get('founded_year', ''),
                    'market_cap': company.get('market_cap', ''),
                    'phone': company.get('sanitized_phone', ''),
                    'alexa_ranking': company.get('alexa_ranking', ''),
                    #'organization_employee_count': company.get('organization_num_employees', '')
                }
                writer.writerow(row)

            print(f"Page {page} processed.")
            page += 1
            
            if page > 500:
                print("Reached page limit. Stopping...")
                break
        else:
            print(f"Error fetching page {page}: {response.status_code}")
            if response.status_code == 429:
                print("Rate limit exceeded. Waiting...")
                time.sleep(600)
            elif response.status_code == 422:
                print("Error 422: Unprocessable Entity")
                break
            else:
                break

print(f"Saved company data to {filename}")
