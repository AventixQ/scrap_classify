import os
import asyncio
import csv
from dotenv import load_dotenv
from openai import AsyncOpenAI
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
import json

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

output_file = "exhibitors_data.json"
final_data_file = "result.csv"
links_to_scrap_file = "links_to_scrap.csv"  # Plik CSV z linkami do scrapowania

BASE_URL = "https://www.omt.de/experte/"

prompt_exhibit = '''
Extract the following details from the given HTML:
    - Company Name
    - Company Domain
    - Email
    - Phone Number
    - Address
    - Hall Number
    - Stand Number
    - Description
    - Linkedin link
'''

prompt_speaker = '''
Extract the following details from the given HTML:
    - Company Name
    - Company Domain
    - Speaker First name
    - Speaker Last name
    - Speaker position
    - Topic of talk
    - Description of talk
    - Language
    - Date and hour
'''

async def extract_details(page_html):
    """Użycie GPT-4o mini do ekstrakcji szczegółowych danych."""
    prompt = f"""
    {prompt_speaker}
    Provide the data in JSON format.
    HTML:
    {page_html[:127000]}
    """
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    return response.choices[0].message.content

async def save_links_to_csv(links):
    """Zapisz zebrane linki do pliku CSV."""
    with open(links_to_scrap_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["URL"])
        for link in links:
            writer.writerow([link])

async def main():
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2, 
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(BASE_URL, config=config)
        print(f"Crawled {len(results)} pages in total")

        # Filtruj wyniki i zbierz linki
        filtered_results = [result for result in results if 
                            "https://www.omt.de/experte/" in result.url]
        
        print(f"Filtered {len(filtered_results)} pages in total")

        # Zapisz linki do CSV
        links = [result.url for result in filtered_results]
        await save_links_to_csv(links)
        print(f"Saved {len(links)} links to {links_to_scrap_file}")

        exhibitor_data = []
        i = 0
        for result in filtered_results:
            data = await extract_details(result.html)
            exhibitor_data.append({
                "url": result.url,
                "data": data
            })
            i += 1
            print(f"Done for {i}.")
            
            # Flush do pliku JSON
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(exhibitor_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
