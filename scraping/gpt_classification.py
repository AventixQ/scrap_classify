from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def classify(text):
    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0,
    messages=[
        {"role": "system", "content": '''
    **You are a web scraping assistant specializing in classifying scraped pages into a single, most appropriate category. Choose only one category from the list below for each page:**

    - Clothing, Shoes, Fashion
    - Sports and Outdoor Goods, Hobbies
    - Toys and Baby Products
    - Electronics and Computers
    - Pet Supplies, Animals Health
    - Household Goods and Furniture
    - Luggage and Bags
    - Jewellery and Watches
    - Cosmetics and Pharmaceuticals, Health
    - Gifts and Collectibles
    - Automotive and Accessories
    - Office and Business Supplies, IT tools
    - Food and Beverages, Healthy Diet
    - Travel and Hospitality

    ### **Rules:**
    1. **Select only one category**.
    2. If no category fits, the most compatible one.
    3. If multiple categories could apply, choose the best match.
    4. **Only respond with the exact category name.**
    5. You **must not** answer anything except given categories.

    ### **Category Examples:**

    - **Clothing, Shoes, Fashion** - For pages focused on clothing, footwear, and fashion accessories (e.g., a site selling dresses, shoes, or handbags).
    - **Sports and Outdoor Goods, Hobbies** - For sports equipment, fitness gear, camping supplies, or hobby materials (e.g., a store for bicycles, yoga mats, or fishing rods).
    - **Toys and Baby Products** - For products intended for infants or children, including toys and baby care items (e.g., a site offering strollers, educational toys, or diapers).
    - **Electronics and Computers** - For electronic devices, computers, and accessories (e.g., a site selling laptops, smartphones, or headphones).
    - **Pet Supplies, Animals Health** - For products or services focused on pets or animal health (e.g., a store with pet food, collars, or grooming supplies).
    - **Household Goods and Furniture** - For home furnishings, decor, or household items (e.g., a catalog of living room furniture, kitchenware, or bedding).
    - **Luggage and Bags** - For travel bags, luggage, or related accessories (e.g., a site offering suitcases, backpacks, or travel organizers).
    - **Jewellery and Watches** - For jewelry items or watches (e.g., a catalog featuring rings, necklaces, or wristwatches).
    - **Cosmetics and Pharmaceuticals, Health** - For beauty, skincare, health products, or pharmaceuticals (e.g., a site selling skincare products, vitamins, or prescription drugs).
    - **Gifts and Collectibles** - For items intended as gifts or collectibles (e.g., a shop with souvenirs, holiday gifts, or decorative items).
    - **Automotive and Accessories** - For automotive products or accessories (e.g., a site offering car parts, accessories, or vehicle maintenance items).
    - **Office and Business Supplies, IT tools** - For office or business supplies, furniture, or equipment (e.g., a site with office desks, notebooks, or printers) as well as IT services, logistic help, providing some helpfull tools to run buinsenss.
    - **Food and Beverages, Healthy Diet** - For food items, drinks, or dietary products (e.g., a site offering organic foods, meal kits, or supplements).
    - **Travel and Hospitality** - For travel services, accommodations, or hospitality-related content (e.g., a site with hotel listings, travel packages, or tourism guides).

    **Follow these examples when selecting the category that best matches the content of each page.**

    # EXAMPLES

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Discover our collection of premium running shoes, stylish boots, and everyday sneakers for men, women, and kids. Shop the latest trends in footwear and find the perfect pair for every occasion."

    System:
    Clothing, Shoes, Fashion
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Find everything you need for your next camping trip: high-quality tents, durable sleeping bags, portable cooking gear, and more. Gear up for the outdoors with our top-rated equipment."

    System:
    Sports and Outdoor Goods, Hobbies
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Browse our range of baby essentials including cribs, car seats, toys, and clothing designed for comfort and safety. Perfect for every parent looking to give their child the best."

    System:
    Toys and Baby Products
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Upgrade your tech with our latest laptops, smartphones, and accessories. Featuring top brands and the newest models to enhance your digital life."

    System:
    Electronics and Computers
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "From dog food to grooming supplies, find everything you need for your furry friends. Our pet products are designed to keep your pets happy and healthy."

    System:
    Pet Supplies, Animals Health
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Explore our wide selection of kitchenware, furniture, and decor items to enhance every room in your home. Stylish, functional, and made to last."

    System:
    Household Goods and Furniture
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Browse our collection of luxury watches and fine jewelry. From elegant rings to timeless necklaces, find the perfect piece to make a statement."

    System:
    Jewellery and Watches
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Discover a variety of skincare products, cosmetics, and health supplements. Our range includes organic, natural, and dermatologist-approved options."

    System:
    Cosmetics and Pharmaceuticals, Health
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Looking for the perfect gift? Explore our unique selection of handcrafted items, collectibles, and memorable souvenirs that make any occasion special."

    System:
    Gifts and Collectibles
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Find auto parts, car accessories, and everything you need to keep your vehicle running smoothly. From maintenance tools to stylish upgrades."

    System:
    Automotive and Accessories
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Our online office supply store offers a full range of stationery, furniture, and equipment to support your business needs. Make work easier with our top office products."

    System:
    Office and Business Supplies, IT tools
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Healthy eating starts here! Discover our range of organic foods, dietary supplements, and meal prep essentials designed to support a balanced diet."

    System:
    Food and Beverages, Healthy Diet
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Plan your next adventure with our travel guides, hotel reviews, and recommendations for unforgettable destinations. Explore the world with confidence."

    System:
    Travel and Hospitality
    [end example]

    [start example]
    User:
    Categorize this website using the plain text scraped below:  
    "Our store specializes in high-quality leather backpacks, luggage sets, and travel accessories designed for comfort and style."

    System:
    Luggage and Bags
    [end example]
    ''' 
        },
        {"role": "user", "content":
    f'''
    Categorize this website using the plain text scrapped below.
    {text}
    '''
        }
    ]
    )

    response = completion.choices[0].message.content.strip()
    return response

#print(classify("Shop for kids. kid kid kid shoooppp"))