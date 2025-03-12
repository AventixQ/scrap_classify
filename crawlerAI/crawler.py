import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

# Wczytanie klucza API z pliku .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicjalizacja klienta OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

BASE_URL = "https://www.eurocis-tradefair.com/en/Exhibitors_Products/Exhibitor_Index_A-Z_1"

async def extract_details(page_html):
    """Użycie GPT-4o mini do ekstrakcji szczegółowych danych."""
    prompt = f"""
    Extract the following details from the given HTML:
    - Company Name
    - Company Domain
    - Phone Number
    - Address
    - Hall Number
    - Stand Number
    - Description
    Provide the data in JSON format.
    HTML:
    {page_html}
    """
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",  # lub gpt-4o-mini
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    return response.choices[0].message.content

async def main():
    # Konfiguracja głębokości crawlowania i strategii scrapowania
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=6, 
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(BASE_URL, config=config)
        print(f"Crawled {len(results)} pages in total")

        exhibitor_data = []
        
        # Filtrowanie stron zawierających określony wzorzec w URL
        filtered_results = [result for result in results if 
                            "https://www.eurocis-tradefair.com/vis/v1/en/exhprofiles" in result.url]
        
        print(f"Filtered {len(filtered_results)} pages in total")
        i=0
        for result in filtered_results:
            data = await extract_details(result.html)
            exhibitor_data.append({
                "url": result.url,
                "data": data
            })
            i+=1
            print(f"Done for {i}.")

        
        # Zapisz wyniki do pliku JSON
        import json
        with open("exhibitors_data.json", "w", encoding="utf-8") as f:
            json.dump(exhibitor_data, f, indent=4, ensure_ascii=False)
        
        print("Data saved to exhibitors_data.json")

if __name__ == "__main__":
    asyncio.run(main())
