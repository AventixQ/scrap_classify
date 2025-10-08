import os
import re
import time
import json

import gspread
from transformers import pipeline
import torch
from dotenv import load_dotenv

load_dotenv()

# =================== CONFIG ===================
SHEET_NAME  = "EBE26 - London Expo"
WORKSHEET   = "Position2"
START_ROW   = 1
END_ROW     = 1442
BATCH_SIZE  = 500
MIN_SCORE   = 0.55
CACHE_PATH  = os.getenv("CLASSIFY_CACHE_JSON", "classify_cache.json")
# ==============================================

# ---------- Google Sheets ----------
gc = gspread.service_account(filename=os.getenv("CREDS_FILE"))
sh = gc.open(SHEET_NAME).worksheet(WORKSHEET)

# ---------- Device pick ----------
def pick_device_for_pipeline():
    if torch.cuda.is_available():
        return 0
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return -1

device = pick_device_for_pipeline()

# ---------- Pipeline ----------
pipe_kwargs = {}
if device == 0:  # CUDA
    pipe_kwargs["torch_dtype"] = torch.float16

classifier = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
    device=device,
    hypothesis_template="This text is about {}.",
    **pipe_kwargs
)

# ---------- Kategorie (spójne nazwy) ----------
CATEGORIES = [
    "c-suite",
    "e-commerce",
    "marketing",
    "sales",
    "product",
    "engineering & technical",
    "finance & accounting",
    "human resources & hr",
    "legal & law",
    "operations",
    "consulting",
    "graphics & design",
    "other",
]

# ---------- Pomocnicze ----------
def normalize_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())

def has_product_owner(t: str) -> bool:
    return re.search(r"\bproduct\s+owner\b", t, re.IGNORECASE) is not None

def is_fake_owner(t: str) -> bool:
    # np. process/data/design/test/service owner — nie C-suite
    return re.search(r"\b(process|data|design|test|service)\s+owner\b", t, re.IGNORECASE) is not None

def looks_vp(t: str) -> bool:
    # precyzyjny VP (nie łapie 'service/device/advice')
    if re.search(r"\b(e|s)?vp\b", t, re.IGNORECASE):
        return True
    return re.search(r"\bvice\s+president\b", t, re.IGNORECASE) is not None

# ---------- Regex helpers + reguły ----------
def w(words):
    return re.compile(r"(?:^|[^a-zA-Z])(" + "|".join(words) + r")(?:[^a-zA-Z]|$)", re.IGNORECASE)

# C-suite core (z wykluczeniem 'product owner' przez negative lookbehind-like check w logice)
RX_CSUITE_TOP = re.compile(
    r"(?:(?<!product\s)owner|co[-\s]?founder|founder|\bceo\b|president|chairman|"
    r"\bcfo\b|\bcoo\b|\bcmo\b|\bcso\b|\bcto\b|\bcio\b|chief\s+[a-z])\b",
    re.IGNORECASE
)

# e-commerce – tylko prawdziwe trafienia
RX_ECOM = re.compile(r"(^|[^a-zA-Z])e[-\s]?commerce([^a-zA-Z]|$)|(^|[^a-zA-Z])ecommerce([^a-zA-Z]|$)", re.IGNORECASE)

# Customer Success i Support
RX_CUSTOMER_SUCCESS = re.compile(r"\bcustomer\s+success\b|\b(cs)\s*(manager|lead|head)?\b", re.IGNORECASE)
RX_SUPPORT = re.compile(r"\bcustomer\s+(support|service)\b|\bhelp[\s-]?desk\b|\b(call|contact)\s*center\b", re.IGNORECASE)

# DevRel / Advocate
RX_DEVREL = re.compile(r"\bdeveloper\s+(advocate|evangelist)\b|\bdevrel\b", re.IGNORECASE)

# Sales Engineer / Pre-sales
RX_PRE_SALES = re.compile(r"\b(pre[-\s]?sales|sales\s+engineer|solutions?\s+engineer)\b", re.IGNORECASE)

# Solutions Architect (bez 'sales')
RX_SOL_ARCH = re.compile(r"\b(solutions?|software|cloud|data)\s+architect\b", re.IGNORECASE)

# Project/Program/Technical PM
RX_TPM = re.compile(r"\b(technical\s+program\s+manager|tpm)\b", re.IGNORECASE)
RX_IT_PM = re.compile(r"\b(it|software|digital)\s+project\s+manager\b", re.IGNORECASE)
RX_PROJ_MGR = re.compile(r"\bproject\s+manager\b", re.IGNORECASE)

# QA software vs QA operations
RX_QA_SW = re.compile(r"\b(qA|sdet|test(ing)?|automation)\b", re.IGNORECASE)
RX_QA_OPS = re.compile(r"\b(quality\s+assurance|quality\s+manager|iso|production|factory|warehouse)\b", re.IGNORECASE)

# Analityka marketingowa
RX_MKT_ANALYTICS = re.compile(r"\b(seo|sem|ppc|campaign|crm|growth|performance)\b", re.IGNORECASE)

# Operations rozszerzone
RX_OPS_EXTRA = re.compile(r"\b(procurement|purchasing|supply\s*chain|logistics?|warehouse|fulfillment|inventory)\b", re.IGNORECASE)

# HR rozszerzone
RX_HR_EXTRA = re.compile(
    r"\b(talent\s+acquisition|recruit(er|ing)|people\s+partner|hrbp|payroll|comp(ensation)?\s*&?\s*ben(efits)?|"
    r"learning\s*&?\s*development|employer\s+branding)\b",
    re.IGNORECASE
)

# Legal/Compliance
RX_LEGAL = re.compile(r"\b(attorney|lawyer|legal|paralegal|counsel|solicitor|notary|regulatory)\b", re.IGNORECASE)
RX_COMPLIANCE = re.compile(r"\b(compliance|aml|kyc|gdpr|dpo|privacy|data\s+protection)\b", re.IGNORECASE)

# Sales Ops / RevOps / CRM / Salesforce dev
RX_SALES_OPS = re.compile(r"\b(revops|revenue\s+operations|sales\s+ops?|crm\s+manager)\b", re.IGNORECASE)
RX_SFDC_DEV  = re.compile(r"\bsalesforce\s+(admin|developer|architect)\b", re.IGNORECASE)

# Ogólne reguły (po wyższych priorytetach)
RULES = [
    # marketing
    (w([r"marketing", r"content", r"media", r"social", r"performance\s+marketing",
        r"growth\s+marketing", r"copywriter", r"brand(?:ing)?"]), "marketing"),

    # HR
    (w([r"\bhr\b", r"human\s+resources", r"people\s+ops?", r"talent"]), "human resources & hr"),

    # product
    (w([r"product\s+(manager|owner|designer|lead|head)", r"\bpo\b(?!\w)", r"\bpm\b(?!.?s\b)"]), "product"),

    # sales / bizdev
    (w([r"sales", r"\bsdr\b", r"business\s+development", r"account\s+exec", r"bdm"]), "sales"),

    # operations (ogólne)
    (w([r"operations?", r"ops\b", r"back\s*office", r"office\s+manager"]), "operations"),

    # engineering & technical (ogólne)
    (w([r"\bit\b", r"engineer", r"developer", r"devops?", r"data\s+scientist", r"ml\s+engineer", r"qa\b",
        r"tester", r"scientist", r"software", r"frontend", r"backend", r"full[-\s]?stack", r"cloud", r"erp", r"sap", r"technology"]),
     "engineering & technical"),

    # graphics & design
    (w([r"artist", r"design", r"\bux\b", r"\bui\b", r"3d", r"2d", r"photo", r"graphic", r"designer"]),
     "graphics & design"),

    # finance & accounting
    (w([r"finance", r"accounting", r"controller", r"analyst\s+finance"]), "finance & accounting"),

    # consulting / advisory
    (w([r"consultant", r"advisor", r"coach", r"instructor", r"trainer"]), "consulting"),
]

# ---------- LEVEL RULES ----------
def classify_level(title: str) -> str:
    t = normalize_title(title)

    # Asystenci CEO nie są C-suite
    if re.search(r"\b(executive\s+assistant|assistant\s+to\s+the\s+ceo|office\s+of\s+the\s+ceo)\b", t, re.IGNORECASE):
        return "mid"

    if not has_product_owner(t) and not is_fake_owner(t):
        if RX_CSUITE_TOP.search(t):
            return "c-suite"
    if looks_vp(t):
        return "executive"

    for rx, lvl in [
        (w([r"\bhead\b", r"lead", r"director"]), "lead/head/director"),
        (w([r"manager", r"management", r"\bpm\b(?!.?s\b)", r"project\s+manager"]), "manager"),
        (w([r"intern", r"junior", r"entry", r"student", r"trainee", r"graduate", r"apprentice"]), "entry lvl"),
        (w([r"senior", r"principal", r"expert", r"specialist", r"master"]), "senior/expert/specialist"),
        (w([r"assistant", r"assist", r"\bmid\b"]), "mid"),
    ]:
        if rx.search(t):
            return lvl
    return ""

# ---------- Kategoryzacja (reguły -> cache -> model) ----------
_cache: dict[str, tuple[str, float]] = {}

def load_cache():
    global _cache
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                _cache = json.load(f)
    except Exception:
        _cache = {}

def save_cache():
    try:
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False)
        os.replace(tmp, CACHE_PATH)
    except Exception:
        pass

load_cache()

def classify_rule_based(title: str) -> str | None:
    t = normalize_title(title)

    # 0) twarde wykluczenia owner-a (process/data/design/test/service owner != C-suite)
    fake_owner = is_fake_owner(t)

    # 1) Customer Success (zanim support/service)
    if RX_CUSTOMER_SUCCESS.search(t):
        return "sales"

    # 2) E-commerce (ściśle)
    if RX_ECOM.search(t):
        return "e-commerce"

    # 3) DevRel → marketing
    if RX_DEVREL.search(t):
        return "marketing"

    # 4) Sales Engineer / Pre-sales → sales
    if RX_PRE_SALES.search(t):
        return "sales"

    # 5) Solutions Architect (bez sales) → engineering & technical
    if RX_SOL_ARCH.search(t):
        return "engineering & technical"

    # 6) QA rozróżnienie
    if RX_QA_SW.search(t):
        return "engineering & technical"
    if RX_QA_OPS.search(t) and not RX_QA_SW.search(t):
        return "operations"

    # 7) Project/Program Manager rozróżnienia
    if RX_TPM.search(t) or RX_IT_PM.search(t):
        return "engineering & technical"
    if RX_PROJ_MGR.search(t):
        return "operations"

    # 8) HR/Legal/Compliance rozszerzone
    if RX_HR_EXTRA.search(t):
        return "human resources & hr"
    if RX_LEGAL.search(t) or RX_COMPLIANCE.search(t):
        return "legal & law"

    # 9) Sales Ops / RevOps / CRM / Salesforce
    if RX_SALES_OPS.search(t):
        return "sales"
    if RX_SFDC_DEV.search(t):
        return "engineering & technical"

    # 10) Support/Service/Helpdesk → operations (po Success)
    if RX_SUPPORT.search(t):
        return "operations"

    # 11) Analytics – marketingowy kontekst → marketing, inaczej tech
    if "analyst" in t or "analytics" in t:
        if RX_MKT_ANALYTICS.search(t):
            return "marketing"
        return "engineering & technical"

    # 12) Rozszerzone operations
    if RX_OPS_EXTRA.search(t):
        return "operations"

    # 13) Executive/C-suite (kategoria), z wykluczeniem Product Owner i fake owner
    if not has_product_owner(t) and not fake_owner:
        if RX_CSUITE_TOP.search(t) or looks_vp(t):
            return "c-suite"

    # 14) Ogólne reguły na końcu
    for rx, cat in RULES:
        if rx.search(t):
            return cat

    return None

def classify_position(title: str) -> tuple[str, float]:
    t_norm = normalize_title(title)
    if not t_norm:
        return "", 0.0

    # 1) reguły (z wyjątkami)
    cat = classify_rule_based(t_norm)
    if cat is not None:
        return cat, 1.0

    # 2) cache
    if t_norm in _cache:
        return _cache[t_norm]

    # 3) model (fallback)
    out = classifier(t_norm, candidate_labels=CATEGORIES)
    predicted = out["labels"][0]
    score = float(out["scores"][0])
    if score < MIN_SCORE:
        predicted = "other"

    _cache[t_norm] = (predicted, score)
    return predicted, score

# ---------- Pętla po Google Sheet ----------
def classify_google_sheet(sheet, start_row, end_row):
    range_data = sheet.get(f"A{start_row}:A{end_row}")

    updates_predicted = []
    updates_lvl = []
    row_indices = []

    print(f"Start: rows {start_row}..{end_row} | device={device}", flush=True)
    time.sleep(0.5)

    for i, row in enumerate(range_data, start=start_row):
        position = row[0] if row else ""
        if not position:
            continue

        predicted_category, confidence_score = classify_position(position)
        lvl_category = classify_level(position)

        print(f"[{time.strftime('%H:%M:%S')}] row {i}: {position} -> {predicted_category} ({confidence_score:.2f}) | lvl={lvl_category}", flush=True)

        updates_predicted.append([predicted_category])
        updates_lvl.append([lvl_category])
        row_indices.append(i)

        if len(updates_predicted) >= BATCH_SIZE:
            sheet.update(range_name=f"B{row_indices[0]}:B{row_indices[-1]}", values=updates_predicted)
            sheet.update(range_name=f"C{row_indices[0]}:C{row_indices[-1]}", values=updates_lvl)
            save_cache()
            updates_predicted.clear()
            updates_lvl.clear()
            row_indices.clear()

    if updates_predicted:
        sheet.update(range_name=f"B{row_indices[0]}:B{row_indices[-1]}", values=updates_predicted)
        sheet.update(range_name=f"C{row_indices[0]}:C{row_indices[-1]}", values=updates_lvl)
        save_cache()

    print("Done.", flush=True)

# ✅ Start
if __name__ == "__main__":
    classify_google_sheet(sh, START_ROW, END_ROW)
