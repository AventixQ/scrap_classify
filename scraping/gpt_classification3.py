from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_prompt(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
prompt = load_prompt('sp_shop_prompt.txt')

def classify(text):
    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0,
    messages=[
        {"role": "system", "content": prompt},
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