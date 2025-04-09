import re
from urllib.parse import urlparse

def extract_domain(url):
    cleaned_url = re.split(r'[;?#]', url)[0]
    parsed = urlparse(cleaned_url)
    if not parsed.scheme:
        parsed = urlparse('http://' + cleaned_url)
    
    domain = parsed.netloc
    
    domain_parts = domain.split('.')
    if len(domain_parts) > 2:
        if domain_parts[-2] in ['co', 'com', 'gov', 'edu', 'org', 'net'] and len(domain_parts) > 2:
            domain = '.'.join(domain_parts[-3:])
        else:
            domain = '.'.join(domain_parts[-2:])
    
    return domain

urls = [
    "https://www.caissaps.com/recruitment",
    "https://about.mattel.com",
    "https://en.wikipedia.org/wiki/Sunvalley_Group;Sunvalley",
    "http://sub.domain.co.uk",
    "https://example.com",
    "www.test.com",
    "blog.something.org"
]

#for url in urls:
#    print(f"{url} -> {extract_domain(url)}")