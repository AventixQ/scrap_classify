import os
import json
import time
import re
from openai import OpenAI
from dotenv import load_dotenv
import gspread
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

MAX_THREADS = 25
START_ROW = 1
END_ROW = 3403
BUCKET_SIZE = 200

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sheet = gc.open("EBE26 - Similar to Braze").worksheet("Position")

def load_prompt():
    with open("prompt.txt", "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT = load_prompt()

CATEGORY_PATTERNS = [
    ("VP", re.compile(r"\bvp\b|\bvice president\b", re.IGNORECASE)),
    ("Co-Owner", re.compile(r"\bco[-\s]?owner\b", re.IGNORECASE)),
    ("Co-Founder", re.compile(r"\bco[-\s]?founder\b", re.IGNORECASE)),
    ("President", re.compile(r"\bpresident\b", re.IGNORECASE)),
    ("Owner", re.compile(r"\bowner\b", re.IGNORECASE)),
    ("Founder", re.compile(r"\bfounder\b", re.IGNORECASE)),
    ("CEO", re.compile(r"\b(ceo|chief executive officer)\b", re.IGNORECASE)),
    ("CMO", re.compile(r"\b(cmo|chief marketing officer)\b", re.IGNORECASE)),
    ("CMO", re.compile(r"\b(cso|chief strategy officer)\b", re.IGNORECASE)),
    ("COO", re.compile(r"\b(coo|chief operating officer)\b", re.IGNORECASE)),
    ("CGO", re.compile(r"\b(cgo|chief growth officer)\b", re.IGNORECASE)),
]

def detect_category(position: str) -> str:
    normalized = position.lower()
    if "product owner" in normalized:
        return None
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(position):
            return category
    return None

def query_llm(position: str) -> str:
    user_prompt = f"Categorize correctly this position: {position}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        return content.split()[0]
    except Exception as e:
        print(f"LLM error for position {position}: {e}")
        return "error"

def process_position(index: int, position: str) -> tuple[int, str]:
    if not position:
        return index, "empty"
    detected = detect_category(position)
    if detected:
        print(f"Detected directly for row {index}: {detected}")
        return index, detected
    result = query_llm(position)
    print(f"Processed row {index}: {result}")
    return index, result

for bucket_start in range(START_ROW, END_ROW + 1, BUCKET_SIZE):
    bucket_end = min(bucket_start + BUCKET_SIZE - 1, END_ROW)
    cell_range = f"A{bucket_start}:A{bucket_end}"
    rows = sheet.get(cell_range)
    
    positions = [(i + bucket_start, row[0].strip()) for i, row in enumerate(rows) if row and row[0].strip()]
    
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(process_position, idx, position): idx for idx, position in positions}
        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    result_list = [[""] for _ in range(bucket_end - bucket_start + 1)]
    for i in range(bucket_end - bucket_start + 1):
        row_idx = bucket_start + i
        result_list[i][0] = results.get(row_idx, "")

    update_range = f"B{bucket_start}:B{bucket_end}"
    sheet.update(update_range, result_list)

    print(f"Updated range {update_range}")
    time.sleep(1)
