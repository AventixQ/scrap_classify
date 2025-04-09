import requests
from bs4 import BeautifulSoup
import csv
from urllib.parse import urlparse

def extract_domain(url):
    """Extracts domain from a URL (e.g., 'canon.de' from 'https://canon.de')"""
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "") if parsed.netloc else ""

def scrape_omr_exhibitor(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        company_name = url.split('/')[-1].replace('-', ' ').title().replace('Gmbh', 'GmbH').replace('Co Kg', 'Co KG')

        domain = ""
        domain_link = soup.find('a', href=lambda x: x and 'http' in x and not 'omr.com' in x)
        if domain_link:
            domain = extract_domain(domain_link['href'])

        about = ""
        about_section = soup.find('div', class_=lambda x: x and 'about' in x.lower()) or \
                       soup.find('p', class_=lambda x: x and 'description' in x.lower()) or \
                       soup.find('meta', attrs={'name': 'description'})
        if about_section:
            about = about_section.get_text(strip=True) if about_section.name != 'meta' else about_section.get('content', '')

        return {
            'Company Name': company_name,
            'Domain': domain,
            'About': about[:500]
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    input_file = 'links.csv'
    output_file = 'omr_exhibitors.csv'

    with open(input_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    data = []
    for url in urls:
        print(f"Scraping: {url}")
        result = scrape_omr_exhibitor(url)
        if result:
            data.append(result)

    if data:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Company Name', 'Domain', 'About'], delimiter=';')
            writer.writeheader()
            writer.writerows(data)
        print(f"Saved {len(data)} entries to {output_file}")
    else:
        print("No data scraped.")

if __name__ == '__main__':
    main()