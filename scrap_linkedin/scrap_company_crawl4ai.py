import time
import random
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from print import extract_information

def configure_browser():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)  # Ustawienie timeoutu dla każdej strony
    return driver

def human_like_delay(min=1, max=3):
    time.sleep(random.uniform(min, max))

def login_to_linkedin(driver, email, password):
    try:
        driver.get('https://www.linkedin.com/login')
        human_like_delay(2, 4)
        driver.find_element(By.ID, 'username').send_keys(email)
        human_like_delay(0.5, 1.5)
        driver.find_element(By.ID, 'password').send_keys(password)
        human_like_delay(0.5, 1.5)
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()
        human_like_delay(5, 8)
    except WebDriverException as e:
        print(f"Login error: {e}")

def scroll_page(driver):
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 2)")
        human_like_delay(1, 2)

def extract_company_links(driver):
    company_links = []
    elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/company/')]")
    for element in elements:
        link = element.get_attribute("href")
        if link and "/about" not in link:
            company_links.append(link + "/about")
    return list(set(company_links))

def get_company_data(driver, url):
    try:
        driver.get(url)
        human_like_delay(3, 6)
        
        actions = webdriver.ActionChains(driver)
        for _ in range(3):
            actions.send_keys(Keys.PAGE_DOWN).perform()
            human_like_delay(1, 3)
        
        page_html = driver.page_source
        extracted_info = extract_information(page_html)
        print(f"Scraped data from {url}")
        return extracted_info
    
    except (TimeoutException, WebDriverException) as e:
        print(f"Error while scraping {url}: {e}")
        return None

def scrape_companies(driver, search_url, csv_filename):
    try:
        driver.get(search_url)
    except TimeoutException:
        print("Initial page load timed out. Retrying...")
        return
    
    human_like_delay(3, 5)
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['company_url', 'description', 'website', 'industry', 'company_size', 'followers', 'headquarters']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        csv_writer.writeheader()
        csvfile.flush()
        
        while True:
            try:
                current_url = driver.current_url
                print(current_url)
                company_links = extract_company_links(driver)
                print(f"Found {len(company_links)} company links.")
        
                for link in company_links:
                    if "https://www.linkedin.com/company/setup/new//about" not in link:
                        data_json = get_company_data(driver, link)
                        if not data_json:
                            continue
                        
                        try:
                            data_dict = eval(data_json)
                        except Exception as e:
                            print(f"Error parsing data from {link}: {e}")
                            continue
                        
                        cleaned_data = {key: str(value).encode('utf-8', 'ignore').decode('utf-8') for key, value in data_dict.items()}
                        
                        csv_writer.writerow({
                            'company_url': link,
                            'description': cleaned_data.get('Description', 'Not found'),
                            'website': cleaned_data.get('Website', 'Not found'),
                            'industry': cleaned_data.get('Industry', 'Not found'),
                            'company_size': cleaned_data.get('Company size', 'Not found'),
                            'followers': cleaned_data.get('Followers', 'Not found'),
                            'headquarters': cleaned_data.get('Headquarters', 'Not found')
                        })
                        csvfile.flush()
                        human_like_delay(2, 5)
                
                driver.get(current_url)
                scroll_page(driver)
                human_like_delay(1, 4)
                
                try:
                    next_button = driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                    if "disabled" in next_button.get_attribute("class"):
                        print("Reached last page")
                        break
                    next_button.click()
                    human_like_delay(3, 6)
                except NoSuchElementException:
                    print("No more pages found")
                    break
                
            except (TimeoutException, WebDriverException) as e:
                print(f"Error while processing: {e}")
                break

def main():
    driver = configure_browser()
    try:
        login_to_linkedin(driver, 'aventix.jj@gmail.com', '22668fed')
        time.sleep(60)
        search_url = "https://www.linkedin.com/search/results/companies/?companyHqGeo=%5B%22101282230%22%5D&companySize=%5B%22C%22%2C%22D%22%2C%22E%22%2C%22F%22%2C%22G%22%2C%22H%22%2C%22I%22%5D&industryCompanyVertical=%5B%22116%22%5D&origin=FACETED_SEARCH&page=71&sid=NR7"
        scrape_companies(driver, search_url, 'companies.csv')
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
