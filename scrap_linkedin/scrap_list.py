import time
import random
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import re

def configure_browser():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def human_like_delay(min=1, max=3):
    time.sleep(random.uniform(min, max))

def login_to_linkedin(driver, email, password):
    driver.get('https://www.linkedin.com/login')
    human_like_delay(2, 4)

    driver.find_element(By.ID, 'username').send_keys(email)
    human_like_delay(0.5, 1.5)
    driver.find_element(By.ID, 'password').send_keys(password)
    human_like_delay(0.5, 1.5)
    driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    human_like_delay(5, 8)

def scroll_page(driver):
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 2)")
        human_like_delay(1, 2)

def extract_info(text):
    location_pattern = re.compile(r'^(.*?),\s*([A-Za-z]{2,})')
    followers_pattern = re.compile(r'(\d+[MK]?)\s*followers', re.IGNORECASE)
    
    location_match = location_pattern.search(text)
    location = f"{location_match.group(1)}, {location_match.group(2)}" if location_match else None
    
    followers_match = followers_pattern.search(text)
    followers = followers_match.group(1) if followers_match else None
    
    return location, followers

def scrape_companies(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    companies = []
    
    for li in soup.find_all('li', class_='PIWlapGAIcVqrZohmVZiFemJDDEyWPYQcSQg'):
        try:
            # DONE
            link_tag = li.find('a', {'data-test-app-aware-link': True})
            link = link_tag['href'].split('?')[0] if link_tag else ""
            
            # DONE
            name_tag = li.find('span', class_=lambda c: c and "FPSHHibWFTuBCJQYAPkjKHeFSbyLortOc" in c)
            name = name_tag.get_text(strip=True) if name_tag else ""
            
            industry, hq = "", ""
            info_tag = li.find(lambda tag: tag.name=='div' and '•' in tag.get_text(strip=True))
            if info_tag:
                parts = [part.strip() for part in info_tag.get_text(strip=True).split('•')]
                if parts:
                    industry = parts[0]
                    if len(parts) > 1:
                        hq = parts[1]
            industry = industry[len(name):].strip()
            hq, followers = extract_info(hq)
            
            
            companies.append({
                'name': name,
                'link': link,
                'industry': industry,
                'headquarters': hq,
                'followers': followers
            })
            
        except Exception as e:
            print(f"Error parsing company: {e}")

    return companies

def save_companies_page(companies, csv_writer, csvfile):
    for company in companies:
        csv_writer.writerow(company)
        csvfile.flush()

def scrape_pagination(driver, start_url, csv_filename):
    driver.get(start_url)
    human_like_delay(3, 5)
    
    all_companies = []
    page_number = 1
    # Otwieramy plik CSV raz i zapisujemy nagłówki
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'link', 'industry', 'headquarters', 'followers']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        csv_writer.writeheader()
        csvfile.flush()
        
        while True:
            print(f"Processing page {page_number}...")
            scroll_page(driver)
            human_like_delay(2, 4)
            
            companies = scrape_companies(driver)
            save_companies_page(companies, csv_writer, csvfile)
            print(f"Found {len(companies)} companies on this page")
            
            try:
                next_button = driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                if "disabled" in next_button.get_attribute("class"):
                    print("Reached last page")
                    break
                
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                human_like_delay(1, 2)
                next_button.click()
                page_number += 1
                human_like_delay(4, 7)
                
            except NoSuchElementException:
                print("No more pages found")
                break


def save_to_csv(companies, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'link', 'industry', 'headquarters', 'followers']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)
    print(f"Data saved to {filename}")

def main():
    driver = configure_browser()
    try:
        login_to_linkedin(driver, 'aventix.jj@gmail.com', '22668fed')
        
        search_url = (
            "https://www.linkedin.com/search/results/companies/"
            "?companyHqGeo=%5B%22101282230%22%5D&companySize=%5B%22I%22%5D&"
            "industryCompanyVertical=%5B%22116%22%5D&origin=FACETED_SEARCH&sid=!k%40"
        )
        
        scrape_pagination(driver, search_url, 'companies.csv')
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()