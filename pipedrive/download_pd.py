import requests
import pandas as pd
from dotenv import load_dotenv
import os
load_dotenv()

API_TOKEN = os.getenv("PD_API_KEY")
BASE_URL = 'https://api.pipedrive.com/v1/deals?filter_id=142'
PARAMS = {
    'api_token': API_TOKEN,
    'limit': 100,
    'start': 0
}

all_deals = []
has_more_items = True

while has_more_items:
    response = requests.get(BASE_URL, params=PARAMS)
    data = response.json()

    if not data['success']:
        print("Błąd API:", data)
        break

    deals = data['data']
    if deals:
        for deal in deals:
            # Rozpakuj niektóre pola
            flat_deal = {
                'id': deal.get('id'),
                'title': deal.get('title'),
                'value': deal.get('value'),
                'currency': deal.get('currency'),
                'status': deal.get('status'),
                'add_time': deal.get('add_time'),
                'update_time': deal.get('update_time'),
                'stage_id': deal.get('stage_id'),
                'pipeline_id': deal.get('pipeline_id'),
                'owner_name': deal.get('owner_name'),
                'person_name': deal.get('person_id', {}).get('name') if isinstance(deal.get('person_id'), dict) else None,
                'org_name': deal.get('org_id', {}).get('name') if isinstance(deal.get('org_id'), dict) else None,
                'person_email': deal.get('person_id', {}).get('email')[0].get('value') if isinstance(deal.get('person_id'), dict) and deal['person_id'].get('email') else None,
                'org_address': deal.get('org_id', {}).get('address') if isinstance(deal.get('org_id'), dict) else None,
                'lost_reason': deal.get('lost_reason'),
                'close_time': deal.get('close_time'),
                'won_time': deal.get('won_time'),
                'first_won_time': deal.get('first_won_time'),
            }
            all_deals.append(flat_deal)

    pagination = data.get('additional_data', {}).get('pagination', {})
    has_more_items = pagination.get('more_items_in_collection', False)
    PARAMS['start'] = pagination.get('next_start', 0)

# Zapisz do CSV
df = pd.DataFrame(all_deals)
df.to_csv('pipedrive_deals_clean.csv', index=False)
print("Zapisano do 'pipedrive_deals_clean.csv'")

