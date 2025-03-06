from openai import OpenAI
import json
from scrap import scrape_deep_description

client = OpenAI(api_key="KEY")


def load_prompt_from_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def evaluate_exhibitor(domain: str, description: str) -> dict:
    prompt_template = load_prompt_from_file("prompt.txt")
    if description:
        prompt = prompt_template.format(
            domain=domain,
            description=description if description else "N/A"
        )
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}
    else:
        response_str = '''
            {
              "score": -1,
              "reasons": ["no_description"],
              "exhibitor_type": ""
            }
            '''
        try:
            response_dict = json.loads(response_str)
            return response_dict
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {str(e)}"}



'''
domain = "decathlon.com"
result = evaluate_exhibitor(
    domain=domain,
    description=scrape_deep_description(domain),
    revenue="6862000,00",
    alexa_rank="53504"
)

print(json.dumps(result, indent=2))
'''