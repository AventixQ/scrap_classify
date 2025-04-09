from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("CSE_ID")

def search_site(query: str, results_number = 5):
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

    try:
        result = service.cse().list(q=query, cx=CSE_ID, num=results_number).execute()
    except Exception as e:
        print(f"Błąd podczas wyszukiwania: {e}")
        return []
    
    all_results = []
    for item in result.get("items", []):
        title = item.get("title", "None")
        link = item.get("link", "None")
        snippet = item.get("snippet", "None")

        print(f"Title: {title}")
        print(f"Link: {link}")
        print(f"Snippet: {snippet}\n")

        all_results.append([title, link, snippet])
    return all_results

