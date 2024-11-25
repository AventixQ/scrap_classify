from transformers import pipeline
import gspread
import time
import os

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open("EBE25-Matrix").worksheet("BigData")

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=0)

categories = ["e-commerce", "marketing", "sales", "product", "engeneering & technical",
              "finance & accounting", "human resources & hr", "legal & law",
              "operations", "consulting", "other", "ceo & founder & owner", "graphics & design"]

def classify_lvl(position):
        if any(word in position for word in ["owner", "ceo", "founder", "vp", "partner", "vice"]):
            category = "owner/ceo/founder/vp"
        elif "manager" in position:
            category = "manager"
        elif any(word in position for word in ["head", "lead", "director"]):
            category = "lead/head/director"
        elif any(word in position for word in ["intern", "junior", "entry", "student", "trainee", "associate"]):
            category = "entry lvl"
        elif any(word in position for word in ["senior", "principal", "expert"]):
            category = "senior/expert"
        elif any(word in position for word in ["assistant", "assist", "mid"]):
            category = "mid"
        else:
            category=''
        return category

def classify_position(position):
        if any(word in position for word in ["owner", "ceo", "founder"]):
            predicted_category = "ceo & founder & owner"
            confidence_score=1
        elif "e-commerce" in position:
            predicted_category = "e-commerce"
            confidence_score=1
        elif any(word in position for word in ["marketing", "content", "media", "creative"]):
            predicted_category = "marketing"
            confidence_score=1
        elif any(word in position for word in ["hr", "human", "people"]):
            predicted_category = "human resources & hr"
            confidence_score=1
        elif "product" in position:
            predicted_category = "product"
            confidence_score=1
        elif "sales" in position:
            predicted_category = "sales"
            confidence_score=1
        elif "operation" in position:
            predicted_category = "operations"
            confidence_score=1
        elif any(word in position for word in ["it", "engineer", "enginereeing", "techical", "computer", "scientist"]):
            predicted_category = "engeneering & technical"
            confidence_score=1
        elif any(word in position for word in ["artist", "design", "3d", "2d", "photo"]):
            predicted_category = "graphics & design"
            confidence_score=1
        elif "account" in position:
            predicted_category = "finance & accounting"
            confidence_score=1
        else:
            result = classifier(str(position), candidate_labels=categories)
            predicted_category = result['labels'][0]
            confidence_score = result['scores'][0]
        return predicted_category, confidence_score

def classify_google_sheet(sheet, start_row, end_row):
    
    for i in range(start_row, end_row + 1):
        position = sheet.acell("h"+str(i)).value
        if not position.strip():
            continue
        
        predicted_category, confidence_score = classify_position(position)
        lvl_category = classify_lvl(position)

        print(f"{position} -> {predicted_category} ({confidence_score:.2f})")

        sh.update_acell("j"+str(i),predicted_category)
        sh.update_acell("k"+str(i),confidence_score)
        sh.update_acell("i"+str(i),lvl_category)
        time.sleep(2) #1 for 2 columns, 2 for 3 columns

classify_google_sheet(sh,2,85)