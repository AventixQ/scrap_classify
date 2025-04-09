import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from llm import evaluate_exhibitor

def scrape_deep_description(domain: str) -> str:
    """Scrapes the website description using Selenium."""
    url = f"https://{domain}"
    try:
        driver.get(url)
        time.sleep(3)
        return driver.find_element(By.TAG_NAME, 'body').text[:1000]
    except (TimeoutException, WebDriverException):
        return ""

def evaluate_alexa_rank(alexa_rank: str) -> int:
    rank_mapping = {"1-10": 1, "11-50": 2, "51-200": 5, "201-500": 7, "201+": 8, "501+": 10}
    return rank_mapping.get(alexa_rank, 0)

def evaluate_revenue(revenue: int) -> int:
    try:
        revenue = int(revenue)
        if revenue >= 1000000: return 10
        if revenue >= 300000: return 8
        if revenue >= 100000: return 7
        if revenue >= 50000: return 4
        if revenue >= 5000: return 3
        return 1
    except:
        return 0

def is_scraping_failed(reasons: str) -> bool:
    errors = {"access_denied", "no_description", "access_blocked", "error_message"}
    return any(error in reasons.lower() for error in errors)

def process_csv(input_path: str, output_path: str):
    """Processes CSV and saves results."""
    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        reader = csv.DictReader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter=';')
        writer.writerow(['domain', 'llm_score', 'alexa_score', 'revenue', 'total_score', 'reasons', 'exhibitor_type'])
        outfile.flush()
        
        for row in reader:
            try:
                domain = row['domain']
                description = scrape_deep_description(domain)
                llm_result = evaluate_exhibitor(domain, description) if description else {"score": -1, "reasons": ["no_description"], "exhibitor_type": ""}
                
                reasons_str = "_".join(llm_result.get('reasons', []))
                llm_score = -1 if is_scraping_failed(reasons_str) else llm_result.get('score', 0)
                alexa_score = evaluate_alexa_rank(row.get('alexa_rank', ''))
                revenue_score = evaluate_revenue(row.get('revenue', ''))
                
                sufix_points = 60 + (10 if alexa_score > 0 else 0) + (10 if revenue_score > 0 else 0)
                total_score = -1 if llm_score == -1 else round((llm_score + alexa_score + revenue_score) * 100 / sufix_points, 2)
                
                writer.writerow([domain, llm_score, alexa_score, revenue_score, total_score, reasons_str, llm_result.get('exhibitor_type', 'N/A')])
                print(f"Done for {domain}")
                outfile.flush()
            except Exception as e:
                print(f"Error for {domain}: {str(e)}")

if __name__ == "__main__":
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(10)
    
    try:
        process_csv('input.csv', 'output.csv')
    finally:
        driver.quit()
