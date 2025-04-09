from bs4 import BeautifulSoup
import json

file_path = "linkedin_page.html"
with open(file_path, "r", encoding="utf-8") as file:
    html_content = file.read()

def extract_information(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    company_info = {
        "Description": "Not found",
        "Website": "Not found",
        "Industry": "Not found",
        "Company size": "Not found",
        "Followers": "Not found",
    }

    description_tag = soup.find("h2", string=lambda t: t and "Overview" in t)
    if description_tag:
        description_link = description_tag.find_next("p")
        if description_link:
            company_info["Description"] = " ".join(description_link.get_text(strip=True).split())


    website_tag = soup.find("h3", string=lambda t: t and "Website" in t)
    if website_tag:
        website_link = website_tag.find_next("a", href=True)
        if website_link and "http" in website_link["href"]:
            company_info["Website"] = website_link["href"]

    industry_tag = soup.find("h3", string=lambda t: t and "Industry" in t)
    if industry_tag:
        industry_value = industry_tag.find_next("dd")
        if industry_value:
            company_info["Industry"] = industry_value.get_text(strip=True)

    company_size_tag = soup.find("h3", string=lambda t: t and "Company size" in t)
    if company_size_tag:
        company_size_value = company_size_tag.find_next("dd")
        if company_size_value:
            company_info["Company size"] = company_size_value.get_text(strip=True)

    top_card_section = soup.find("div", class_="org-top-card-summary-info-list")
    if top_card_section:
        info_items = top_card_section.find_all("div", class_="org-top-card-summary-info-list__info-item")
        for item in info_items:
            text = item.get_text(strip=True)
            if "followers" in text:
                company_info["Followers"] = text
            elif "," in text:
                company_info["Headquarters"] = text


    return json.dumps(company_info, indent=4)

#with open("linkedin_page.html", "r", encoding="utf-8") as file:
#    html_content = file.read()

#result = extract_information(html_content)
