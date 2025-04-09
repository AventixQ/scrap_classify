import re


def is_non_company_domain(domain):
    non_company_domains = [
        'wikipedia.org', 'gov.uk', 'fandom.com', 'crunchbase.com',
        'zoominfo.com', 'instagram.com', 'facebook.com', 'twitter.com', 'youtube.com', 'wipo.int', 'census.gov',
        'international.gc.ca', 'commerce.gov', 'uschamber.com', 'rocketreach.co', 'shopify.com',
        'finalfantasyxiv.com', 'europa.eu', 'ebay.com', 'spotify.com', 'northdata.com',
        'wiktionary.org', 'pinterest.com', 'github.io', 'join.com', 'trustpilot.com',
        'instagram.com', 'reddit.com', 'dot.gov', 'insideretail.com.au', 'insideretail.com',
        'amazon.com', 'bloomberg', 'brandfetch.com', 'clutch.co', 'creditsafe.com', 'dhl.com',
        'dnb.com', 'emis.com', 'github.com', 'glassdoor.com', 'google.com', 'indeed.com',
        'leadiq.com', 'lusha.com', 'pitchbook.com', 'researchgate.net', 'sciencedirect.com',
        'signalhire.com', 'stackexchange.com', 'theorg.com', 'ufficiocamerale.it', 'x.com',
        'xing.com', 'yelp.com', 'unglobalcompact.org', 'upwork.com', 'stackoverflow.com', 'tudublin.ie'
    ]
    
    for non_company in non_company_domains:
        if domain.endswith(non_company):
            return True
    
    patterns = [
        r'find-and-update\.company-information\.service\.gov\.uk',
    ]
    
    for pattern in patterns:
        if re.search(pattern, domain):
            return True
    
    return False

#print(is_non_company_domain("veepee.fr"))
#print(is_non_company_domain("mattel.com"))
#print(is_non_company_domain("wikipedia.org"))
#print(is_non_company_domain("find-and-update.company-information.service.gov.uk"))