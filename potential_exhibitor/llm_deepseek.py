import json
from scrap import scrape_deep_description
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

load_dotenv()

# Wczytaj model DeepSeek-R1 z Hugging Face
model_name = "deepseek-ai/DeepSeek-R1"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)

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

        # Tokenizacja promptu i generowanie odpowiedzi
        inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
        outputs = model.generate(**inputs, max_length=512, num_return_sequences=1)

        # Dekodowanie odpowiedzi
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        try:
            return json.loads(response_text)
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

# Przykład użycia
domain = "decathlon.com"
result = evaluate_exhibitor(
    domain=domain,
    description=scrape_deep_description(domain),
)

print(json.dumps(result, indent=2))