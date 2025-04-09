import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def get_about_page_url(domain: str) -> str:
    """Znajduje URL strony 'About' na podstawie homepage."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://www.google.com/',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        response = requests.get(f"https://{domain}", headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        about_keywords = ['about', 'story', 'company', 'mission', 'team', 'nas', 'o-nas']
        links = soup.find_all('a', href=True)

        for link in links:
            href = link['href'].lower()
            text = link.get_text().lower()

            if any(kw in href for kw in about_keywords) or any(kw in text for kw in about_keywords):
                about_url = urljoin(f"https://{domain}", link['href'])

                if 'facebook' not in about_url and 'linkedin' not in about_url:
                    return about_url

        return None
    except Exception as e:
        print(f"Błąd szukania strony About dla {domain}: {str(e)}")
        return None

def scrape_deep_description(domain: str) -> str:
    """Pobiera treść ze strony About (jeśli istnieje), w przeciwnym razie z homepage."""
    try:
        about_url = get_about_page_url(domain)
        target_url = about_url if about_url else f"https://{domain}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://www.google.com/',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        response = requests.get(target_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        content = soup.find('article') or soup.find('main') or soup.body

        for element in content.find_all(['nav', 'footer', 'script', 'style']):
            element.decompose()

        elements = content.find_all(['h1', 'h2', 'h3', 'p', 'ul'])
        text = '\n'.join([elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)])

        return text  # Ogranicz do 2000 znaków

    except Exception as e:
        print(f"Błąd deep scrapingu dla {domain}: {str(e)}")
        return ""


# Test
#description = scrape_deep_description("sap.com")
#print(description)