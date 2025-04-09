from scrap_site import search_site
from clean_domain import extract_domain
from remove_not_company_pages import is_non_company_domain
import csv
import time

INPUT = "input.csv"
OUTPUT = "output.csv"

def company_domain(company: str) -> str:
    return f"\"{company}\" company site -site:linkedin.com"

def company_linkedin(company: str) -> str:
    return f"{company} site:linkedin.com"

companies = []
with open(INPUT,'r') as input:
    csvreader = csv.reader(input, delimiter=";")
    for row in csvreader:
        companies.append(row[0])
with open(OUTPUT, 'w', newline="", encoding="utf-8") as output:
    writer = csv.writer(output,delimiter=";")
    writer.writerow(["name", "link","domain", "head", "snippet"])
    for company in companies:
        try:
            result = search_site(company_domain(company), 1)[0]
        except IndexError:
            writer.writerow([company,result[1]])
            continue
        domain = extract_domain(result[1])
        if is_non_company_domain(domain):
            writer.writerow([company,result[1]])
        else:
            writer.writerow([company,result[1],domain,result[0],result[2]])
        output.flush()
        time.sleep(0.5)



