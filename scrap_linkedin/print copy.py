import json
from bs4 import BeautifulSoup

file_path = "strona.html"
with open(file_path, "r", encoding="utf-8") as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, "html.parser")

companies = []

for li in soup.find_all("li", class_="reusable-search__result-container"):
    company_data = {
        "name": "Not found",
        "link": "Not found",
        "industry": "Not found",
        "headquarters": "Not found",
        "followers": "Not found"
    }

    name_tag = li.find("span", class_="entity-result__title-text")
    if name_tag:
        company_data["name"] = name_tag.get_text(strip=True)

    link_tag = li.find("a", href=True)
    if link_tag:
        company_data["link"] = link_tag["href"].split("?")[0]

    info_tag = li.find("div", class_="entity-result__primary-subtitle")
    if info_tag:
        parts = info_tag.get_text(strip=True).split("•")
        company_data["industry"] = parts[0].strip() if len(parts) > 0 else "Not found"
        company_data["headquarters"] = parts[1].strip() if len(parts) > 1 else "Not found"

    followers_tag = li.find("div", class_="entity-result__secondary-subtitle")
    if followers_tag:
        followers_text = followers_tag.get_text(strip=True)
        if "followers" in followers_text:
            company_data["followers"] = followers_text.replace(" followers", "")

    companies.append(company_data)

print(companies)
