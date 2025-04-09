import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

output_file = "exhibitors_data.json"
final_data_file = "result.csv"

BASE_URL = "https://omr.com/en/events/festival/exhibitors/"

prompt_exhibit = '''
Extract the following details from the given HTML:
    - Company Name
    - Company Domain
    - Phone Number
    - Address
    - Hall Number
    - Stand Number
    - Description
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
    {prompt_exhibit}
    Provide the data in JSON format.
    HTML:
    {page_html}
    """
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    return response.choices[0].message.content

async def main():
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=4, 
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(BASE_URL, config=config)
        print(f"Crawled {len(results)} pages in total")

        exhibitor_data = []
        
        filtered_results = [result for result in results if 
                            "https://omr.com/en/events/festival/exhibitors/" in result.url]
        
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

        
        import json
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(exhibitor_data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())