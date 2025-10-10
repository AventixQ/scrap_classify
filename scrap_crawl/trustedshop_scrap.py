import requests
from bs4 import BeautifulSoup
import re
import csv
import concurrent.futures
import time

page_num = 1
max_page = 15

base_url = "https://www.trustedshops.de/shops/karneval_kostume/?page="
CSV_FILE_NAME = 'result.csv'

def get_page(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas pobierania {url}: {e}")
        return None

def find_links_in_page(page_html):
    soup = BeautifulSoup(page_html, 'html.parser')
    pattern = r'https://www.trustedshops.de/bewertung/info_[a-zA-Z0-9]+'
    links = set(re.findall(pattern, str(soup)))
    return links

def scrape_company_data(page_html, page_url):
    soup = BeautifulSoup(page_html, 'html.parser')
    
    domain = phone = address = contacts = description = ''
    
    # Domena firmy
    domain_tag = soup.find('a', class_='companyHeader_companyLogoLinkWrapper__hLXvD')
    if domain_tag and domain_tag.has_attr('href'):
        domain = domain_tag['href'].replace('//', '')

    # Telefon firmy
    phone_tag = soup.find('a', class_='contactInfo_companyContactDetailLink__OzJ99', href=lambda x: x and 'tel:' in x)
    if phone_tag:
        phone = phone_tag.text

    # Adres firmy
    address_container = soup.find('div', class_='contactInfo_companyOrgName__HK12P')
    if address_container:
        address = address_container.parent.get_text(separator=' ', strip=True)

    # Osoby kontaktowe
    legal_contacts_section = soup.find('h5', class_='contactInfo_legalHeadline__dkozH', string='Vertreten durch')
    if legal_contacts_section:
        contacts_tag = legal_contacts_section.find_next_sibling('span', class_='contactInfo_legalInfoText__D83Rl')
        if contacts_tag:
            contacts = contacts_tag.get_text(strip=True, separator=', ')

    # Opis firmy
    description_tag = soup.find('div', class_='companyDetails_companyDescription__rruNt')
    if description_tag and description_tag.span:
        description = description_tag.span.text

    data = [page_url, domain, phone, address, contacts, description]
    cleaned_data = [str(item).replace('\n', ' ').replace('\r', '').strip() for item in data]
    return cleaned_data

def crawl_trusted_shops():
    with open(CSV_FILE_NAME, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['Page URL', 'Domain', 'Phone', 'Address', 'Contact person', 'About'])

    def process_page_links(page_url):
        print(f"Pobieranie linków ze strony: {page_url}")
        page_html = get_page(page_url)
        if not page_html:
            return []
        return find_links_in_page(page_html)

    def process_company_profile(link):
        print(f"  -> Przetwarzanie profilu: {link}")
        company_page_html = get_page(link)
        if company_page_html:
            return scrape_company_data(company_page_html, link)
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        all_links = set()
        list_pages_urls = [f"{base_url}{page}" for page in range(page_num, max_page + 1)]
        
        future_to_url = {executor.submit(process_page_links, url): url for url in list_pages_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            links = future.result()
            all_links.update(links)
        
        print(f"\nZnaleziono łącznie {len(all_links)} unikalnych profili do przetworzenia.\n")
        
        future_to_link = {executor.submit(process_company_profile, link): link for link in all_links}
        
        for future in concurrent.futures.as_completed(future_to_link):
            company_data = future.result()
            if company_data:
                with open(CSV_FILE_NAME, 'a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(company_data)
                print(f"     Zapisano dane dla: {company_data[1]}")


    print(f"\nZakończono pracę. Dane zostały zapisane w pliku {CSV_FILE_NAME}.")

crawl_trusted_shops()