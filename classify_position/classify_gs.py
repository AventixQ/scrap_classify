from transformers import pipeline
import gspread
import time
import os

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))

# Wybierz odpowiedni arkusz Google Sheet
sh = gc.open("POSITION_CLASSIFICATION").worksheet("position_once_more")

start_cell = 1
end_cell = 10000

# ✅ NOWY model zero-shot (DeBERTa v3)
classifier = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
    device="mps"  # Jeśli masz Maca z MPS. Użyj -1 dla CPU, 0 dla GPU.
)

categories = ["e-commerce", "marketing", "sales", "product", "engeneering & technical",
              "finance & accounting", "human resources & hr", "legal & law",
              "operations", "consulting", "other", "ceo & founder & owner", "graphics & design"]

def classify_lvl(position):
    position = position.lower()
    if any(word in position for word in ["head", "lead", "director", "chief"]) and "service" not in position:
        return "lead/head/director"
    elif any(word in position for word in ["owner", "ceo", "founder", "vp", "partner", "vice", "cfo"]) and "service" not in position:
        return "owner/ceo/founder/vp"
    elif any(word in position for word in ["manager", "management", "pm"]):
        return "manager"
    elif any(word in position for word in ["intern", "junior", "entry", "student", "trainee"]):
        return "entry lvl"
    elif any(word in position for word in ["senior", "principal", "expert", "specialist", "scrum"]):
        return "senior/expert/specialist"
    elif any(word in position for word in ["assistant", "assist", "mid"]):
        return "mid"
    else:
        return ''

def classify_position(position):
    position_lower = position.lower()
    if any(word in position_lower for word in ["owner", "ceo", "founder"]):
        return "ceo & founder & owner", 1
    elif any(word in position_lower for word in ["e-commerce", "ecommerce"]):
        return "e-commerce", 1
    elif any(word in position_lower for word in ["marketing", "content", "media", "creative"]):
        return "marketing", 1
    elif any(word in position_lower for word in ["hr", "human", "people"]):
        return "human resources & hr", 1
    elif "product" in position_lower:
        return "product", 1
    elif any(word in position_lower for word in ["sales", "sdr", "business development"]):
        return "sales", 1
    elif "operations" in position_lower:
        return "operations", 1
    elif any(word in position_lower for word in ["it", "engineer", "enginereeing", "techical", "computer", "scientist"]):
        return "engeneering & technical", 1
    elif any(word in position_lower for word in ["artist", "design", "3d", "2d", "photo"]):
        return "graphics & design", 1
    elif any(word in position_lower for word in ["finance", "accounting"]):
        return "finance & accounting", 1
    elif any(word in position_lower for word in ["consultant", "advisor", "coach", "instructor"]):
        return "consulting", 1
    else:
        result = classifier(position, candidate_labels=categories)
        predicted_category = result['labels'][0]
        confidence_score = result['scores'][0]
        return predicted_category, confidence_score

def classify_google_sheet(sheet, start_row, end_row):
    range_data = sheet.get(f"A{start_row}:A{end_row}")
    batch_size = 200
    updates_predicted = []
    updates_lvl = []
    row_indices = []

    time.sleep(3)  # Zabezpieczenie na limity API

    for i, row in enumerate(range_data, start=start_row):
        position = row[0] if row else None
        if not position:
            continue

        predicted_category, confidence_score = classify_position(position)
        lvl_category = classify_lvl(position)

        print(f"{position} -> {predicted_category} ({confidence_score:.2f})")

        updates_predicted.append([predicted_category])
        updates_lvl.append([lvl_category])
        row_indices.append(i)

        if len(updates_predicted) == batch_size:
            sheet.update(range_name=f"B{row_indices[0]}:B{row_indices[-1]}", values=updates_predicted)
            sheet.update(range_name=f"C{row_indices[0]}:C{row_indices[-1]}", values=updates_lvl)
            updates_predicted.clear()
            updates_lvl.clear()
            row_indices.clear()

    if updates_predicted:
        sheet.update(range_name=f"B{row_indices[0]}:B{row_indices[-1]}", values=updates_predicted)
        sheet.update(range_name=f"C{row_indices[0]}:C{row_indices[-1]}", values=updates_lvl)

# ✅ Start klasyfikacji
classify_google_sheet(sh, start_cell, end_cell)
