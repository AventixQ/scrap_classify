from transformers import pipeline
import gspread
import time
import os

gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))

##############################################################
################## Choose your google sheet ##################
##############################################################
##################### Available sheets: ######################
####### BigData | Ex-visitors | K5_DMEXCO | SP | TOP10 #######
################## BerlinTOP | Brand_Retail ##################
##############################################################
#sh = gc.open("EBE25-Matrix").worksheet("BigData")
#sh = gc.open("EBE25-Matrix-BigData").worksheet("BigData")
#sh = gc.open("Test EBE25 - Visitors export").worksheet("COMBINE")
sh = gc.open("POSITION_CLASSIFICATION").worksheet("position_once_more")
##############################################################
start_cell = 1
end_cell = 10000
##############################################################
##############################################################

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=0)

categories = ["e-commerce", "marketing", "sales", "product", "engeneering & technical",
              "finance & accounting", "human resources & hr", "legal & law",
              "operations", "consulting", "other", "ceo & founder & owner", "graphics & design"] #marketing sales e-commerce

def classify_lvl(position):
        if any(word in position for word in ["head", "lead", "director", "chief"]) and not "service" in position:
            category = "lead/head/director"
        elif any(word in position for word in ["owner", "ceo", "founder", "vp", "partner", "vice", "cfo"]) and not "service" in position:
            category = "owner/ceo/founder/vp"
        elif any(word in position for word in ["manager", "management", "pm"]):
            category = "manager"
        elif any(word in position for word in ["intern", "junior", "entry", "student", "trainee"]):
            category = "entry lvl"
        elif any(word in position for word in ["senior", "principal", "expert", "specialist", "scrum"]):
            category = "senior/expert/specialist"
        elif any(word in position for word in ["assistant", "assist", "mid"]):
            category = "mid"
        else:
            category=''
        return category

def classify_position(position):
        if any(word in position for word in ["owner", "ceo", "founder"]):
            predicted_category = "ceo & founder & owner"
            confidence_score=1
        elif any(word in position for word in ["e-commerce", "ecommerce"]):
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
        elif any(word in position for word in ["sales", "sdr"]):
            predicted_category = "sales"
            confidence_score=1
        elif any(word in position for word in ["operations"]):
            predicted_category = "operations"
            confidence_score=1
        elif any(word in position for word in ["it", "engineer", "enginereeing", "techical", "computer", "scientist"]):
            predicted_category = "engeneering & technical"
            confidence_score=1
        elif any(word in position for word in ["artist", "design", "3d", "2d", "photo"]):
            predicted_category = "graphics & design"
            confidence_score=1
        elif any(word in position for word in ["finance", "accounting"]):
            predicted_category = "finance & accounting"
            confidence_score=1
        elif any(word in position for word in ["consultant", "advisor", "coach", "instructor"]):
            predicted_category = "consulting"
            confidence_score=1
        else:
            result = classifier(str(position), candidate_labels=categories)
            predicted_category = result['labels'][0]
            confidence_score = result['scores'][0]
        return predicted_category, confidence_score

def classify_google_sheet(sheet, start_row, end_row):
    range_data = sheet.get(f"A{start_row}:A{end_row}")

    batch_size = 20
    updates_predicted = []
    updates_lvl = []
    row_indices = []
    time.sleep(2)  # To avoid API limits, just in case
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

classify_google_sheet(sh,start_cell,end_cell)