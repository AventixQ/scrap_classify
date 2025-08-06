import os, random, requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import urllib.request
import ssl

load_dotenv()

BRD_CUSTOMER = os.getenv("BRD_CUSTOMER")
BRD_PASSWORD = os.getenv("BRD_PASSWORD")
BRD_ZONE     = os.getenv("BRD_UNBLOCKER_ZONE", "web_unlocker1")
BRD_HOST     = os.getenv("BRD_HOST", "brd.superproxy.io")
BRD_PORT     = os.getenv("BRD_PORT", "33335")

assert BRD_CUSTOMER and BRD_PASSWORD, "Brak BRD_CUSTOMER/BRD_PASSWORD w .env"

session_id = str(random.randrange(10**7, 10**8-1))
username   = f"{BRD_CUSTOMER}"
proxy = f"http://{username}:{BRD_PASSWORD}@{BRD_HOST}:{BRD_PORT}"
proxies = {"http": proxy, "https": proxy}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

url = "https://www.zalando.pl/"

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({'https': proxy, 'http': proxy}),
    urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
)

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = soup.get_text(separator="\n", strip=True).splitlines()
    head = "\n".join(lines[:50]).lower()
    cookie_words = ("cookie", "gdpr", "consent", "rodo")
    if any(w in head for w in cookie_words):
        lines = lines[50:]
    out = "\n".join(l for l in (s.strip() for s in lines) if l)
    return out

try:
    html = opener.open(url, timeout=60).read().decode("utf-8", errors="ignore")
    text = html_to_text(html)
    print(text[:2000])
except Exception as e:
    print(f"Error: {e}")