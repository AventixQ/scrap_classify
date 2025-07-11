import requests
import csv
from dotenv import load_dotenv
import os
from hunter.hunter_email_finder import email_find_verify
import time
import json

load_dotenv()

API_KEY = os.getenv("APOLLO_API_KEY")

url = "https://api.apollo.io/api/v1/mixed_people/search?label_ids[]=684acfc9d92f8500217099ef"

## Poprzednie url do wglądu
#url = "https://api.apollo.io/api/v1/mixed_people/search?person_locations[]=europe&organization_locations[]=europe&prospected_by_current_team[]=no&contact_email_status[]=verified&organization_num_employees_ranges[]=11%2C500&person_seniorities[]=c_suite&person_seniorities[]=partner&person_seniorities[]=owner&person_seniorities[]=vp&person_seniorities[]=head&person_seniorities[]=director&person_seniorities[]=founder&person_department_or_subdepartments[]=c_suite&person_department_or_subdepartments[]=master_marketing&person_department_or_subdepartments[]=master_sales&q_organization_keyword_tags[]=ecommerce&q_organization_keyword_tags[]=commerce&organization_industry_tag_ids[]=5567cd4773696439b10b0000&organization_industry_tag_ids[]=5567cd467369644d39040000"
#url = "https://api.apollo.io/api/v1/mixed_people/search?person_locations[]=europe&organization_locations[]=europe&prospected_by_current_team[]=no&contact_email_status[]=verified&organization_num_employees_ranges[]=11%2C500&person_seniorities[]=c_suite&person_seniorities[]=partner&person_seniorities[]=owner&person_seniorities[]=vp&person_seniorities[]=head&person_seniorities[]=director&person_seniorities[]=founder&person_department_or_subdepartments[]=c_suite&person_department_or_subdepartments[]=master_marketing&person_department_or_subdepartments[]=master_sales&person_not_titles[]=account%20manager&person_not_titles[]=seo&person_not_titles[]=digital&person_not_titles[]=cfo"
#url = "https://api.apollo.io/api/v1/mixed_people/search?contact_email_status[]=verified&label_ids[]=680107e77f60710019850ad3person_locations[]=europe"
#url = "https://api.apollo.io/api/v1/mixed_people/search?person_titles[]=sales%20development%20representative&organization_locations[]=berlin"
#url = "https://api.apollo.io/api/v1/mixed_people/search?person_locations[]=berlin&prospected_by_current_team[]=no"
#url = "https://api.apollo.io/api/v1/mixed_people/search?person_locations[]=berlin&contact_email_status[]=verified&organization_ids[]=672b3e612fc02401b0d7bc9f"

#ALL to scrap
#url = "https://api.apollo.io/api/v1/mixed_people/search?person_locations[]=berlin&organization_locations[]=&contact_email_status[]=verified"

#ALL ID BERLIN merge scrap
#url = "https://api.apollo.io/api/v1/mixed_people/search?person_locations[]=berlin&label_ids[]=6798a306622f6f02d170098a"

#URL for TOTAL: mixed_people
#URL for Net New: mixed_people with prospected_by_current_team[]=no
#URL for Saved: contacts ???
#url = 'https://api.apollo.io/api/v1/mixed_people/search?person_seniorities[]=owner&person_seniorities[]=c_suite&person_seniorities[]=director&person_seniorities[]=vp&person_seniorities[]=founder&person_seniorities[]=partner&person_seniorities[]=head&person_locations[]=hamburg&contact_email_status[]=verified&prospected_by_current_team[]=no'

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
else: print("Ooopss")

#HUNTER FINDER
def email_finder(email,organization_name,first_name,last_name):
    email_hunter, confidence_score, status = email_find_verify(organization_name,first_name,last_name)
    if email == '': email = email_hunter
    #time.sleep(0.15)
    return email_hunter, confidence_score, status

#page = 1594
page = 1
page_size = 100

with_hunter = False

filename = "contacts_data.csv"
categories = ['first_name', 'last_name', 'organization_name', 'title', 'linkedin_url', 'city', 'country', 'email', 'phone', 'confidence score', 'mail_status']

tab_of_rows = {}

with open(filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=categories)
    writer.writeheader()

    #APOLLO FINDER
    while True:
        url_with_params = f"{url}&page={page}&per_page={page_size}"
        
        response = requests.post(url_with_params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get("contacts", []) #contacts for labels | people for other (w tym te dziwne labels)
            
            if not contacts:
                print("Nothing here")
                break

            for contact in contacts:
                email = ''
                first_name = contact.get('first_name', '')
                last_name = contact.get('last_name', '')
                #organization_name = contact.get('organization_name', '')

                organization = contact.get('organization', {})  # Pobierz słownik organization lub pusty słownik, jeśli go brak
                organization_name = organization.get('name', '')  # Pobierz name z organization lub pusty string, jeśli brak
                
                title = contact.get('title', '')
                linkedin_url = contact.get('linkedin_url', '')
                city = contact.get('city', '')
                country = contact.get('country', '')
                #email = contact.get('email', '')
                phone = contact.get('sanitized_phone', '')
                confidence_score = -1
                status = "not_in_hunter"
                
                if with_hunter:
                    try:
                        email, confidence_score, status = email_finder(email,organization_name,first_name,last_name)
                    except:
                        confidence_score = -1
                        status = "not_in_hunter"
                        email = ''

                row = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'organization_name': organization_name,
                    'title': title,
                    'linkedin_url': linkedin_url,
                    'city': city,
                    'country': country,
                    'phone': phone,
                    'email': email,
                    'confidence score': confidence_score,
                    'mail_status': status,
                }
                #url_input = f"https://api.apollo.io/api/v1/contacts?first_name={first_name}&last_name={last_name}&organization_name={organization_name}&title={title}&email={email}&label_names[]=EBE25%20-%20Berlin%20all%20API%20add"
                writer.writerow(row)
                #response_input = requests.post(url_input, headers=headers)

            total_pages = data.get("pagination", {}).get("total_pages", 0)
            print(f"Page {page} processed.")
            page += 1
            #page_size = 100
            if page == 501:
                #id = "6798e15508b8e002ceff8fd1"
                #print("Page limit 500 achived. Aborting...")
                #page = 1
                #url_with_params = 
                break
        else:
            print(f"Error during reading {page}: {response.status_code}")
            if response.status_code == 429:
                print("Waiting....")
                time.sleep(600)
            elif response.status_code == 422:
                print(f"Downgrade to {page_size - 1}")
                # Zapisz odpowiedź do pliku JSON i zakończ działanie
                error_data = {
                    "page": page,
                    "error": "422 Unprocessable Entity",
                    "response": response.json()
                }
                #with open(f"error_page_{page}.json", "w", encoding="utf-8") as error_file:
                #    json.dump(error_data, error_file, ensure_ascii=False, indent=4)
                #print(f"Error 422 occurred. Response saved to error_page_{page}.json.")
                if(page_size > 1):
                    page_size -= 1
                else:
                    print("Too low page size")
                    break
            else: continue

print(f"Saved in file {filename}")
