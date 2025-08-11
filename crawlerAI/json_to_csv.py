import re
import csv
import json

def extract_and_save_to_csv(input_jsonl_filename, output_csv_filename, mode="speaker"):
    mode = mode.lower().strip()
    if mode not in {"speaker", "company"}:
        raise ValueError("mode must be 'speaker' or 'company'")

    # --- REGEX: fenced ```json ... ``` (łapie spacje/nowe linie, warianty '``` json')
    fenced_block_regex = re.compile(r"```(?:\s*json)?\s*(\{.*?\})\s*```", re.S | re.I)

    # --- REGEXY DLA SPEAKER ---
    sp_company_name      = re.compile(r'"Company\s+Name"\s*:\s*"([^"]*)"', re.I)
    sp_company_domain    = re.compile(r'"Company\s+Domain"\s*:\s*"([^"]*)"', re.I)
    sp_first             = re.compile(r'"Speaker\s+First\s+name"\s*:\s*"([^"]*)"', re.I)
    sp_last              = re.compile(r'"Speaker\s+Last\s+name"\s*:\s*"([^"]*)"', re.I)
    sp_position          = re.compile(r'"Speaker\s+position"\s*:\s*"([^"]*)"', re.I)
    sp_topic             = re.compile(r'"Topic\s+of\s+talk"\s*:\s*"([^"]*)"', re.I)
    sp_description       = re.compile(r'"Description\s+of\s+talk"\s*:\s*"([^"]*)"', re.I)
    sp_language          = re.compile(r'"Language"\s*:\s*"([^"]*)"', re.I)
    sp_datehour          = re.compile(r'"Date\s+and\s+hour"\s*:\s*"([^"]*)"', re.I)

    # --- REGEXY DLA COMPANY ---
    co_company_name      = re.compile(r'"Company\s+Name"\s*:\s*"([^"]*)"', re.I)
    co_company_domain    = re.compile(r'"Company\s+Domain"\s*:\s*"([^"]*)"', re.I)
    # email/phone mogą być w cudzysłowie lub bez (do przecinka/końca wiersza)
    co_email             = re.compile(r'"Email"\s*:\s*(?:"([^"]*)"|([^,\n}]+))', re.I)
    co_phone             = re.compile(r'"Phone\s+Number"\s*:\s*(?:"([^"]*)"|([^,\n}]+))', re.I)
    co_address           = re.compile(r'"Address"\s*:\s*"([^"]*)"', re.I)
    co_hall              = re.compile(r'"Hall\s+Number"\s*:\s*"([^"]*)"', re.I)
    co_stand             = re.compile(r'"Stand\s+Number"\s*:\s*"([^"]*)"', re.I)
    co_description       = re.compile(r'"Description"\s*:\s*"([^"]*)"', re.I)
    co_linkedin          = re.compile(r'"Linkedin\s+link"\s*:\s*"([^"]*)"', re.I)

    def pick_group(m):
        if not m:
            return ""
        # zwróć pierwszą niepustą grupę
        for i in range(1, m.lastindex + 1 if m.lastindex else 1):
            val = m.group(i)
            if val is not None:
                return val.strip()
        return ""

    def extract_speaker(data_string: str):
        m = fenced_block_regex.search(data_string)
        payload = m.group(1) if m else data_string

        return {
            "Company Name":        pick_group(sp_company_name.search(payload)),
            "Company Domain":      pick_group(sp_company_domain.search(payload)),
            "Speaker First name":  pick_group(sp_first.search(payload)),
            "Speaker Last name":   pick_group(sp_last.search(payload)),
            "Speaker position":    pick_group(sp_position.search(payload)),
            "Topic of talk":       pick_group(sp_topic.search(payload)),
            "Description of talk": pick_group(sp_description.search(payload)),
            "Language":            pick_group(sp_language.search(payload)),
            "Date and hour":       pick_group(sp_datehour.search(payload)),
        }

    def extract_company(data_string: str):
        m = fenced_block_regex.search(data_string)
        payload = m.group(1) if m else data_string

        return {
            "Company Name":   pick_group(co_company_name.search(payload)),
            "Company Domain": pick_group(co_company_domain.search(payload)),
            "Email":          pick_group(co_email.search(payload)),
            "Phone Number":   pick_group(co_phone.search(payload)),
            "Address":        pick_group(co_address.search(payload)),
            "Hall Number":    pick_group(co_hall.search(payload)),
            "Stand Number":   pick_group(co_stand.search(payload)),
            "Description":    pick_group(co_description.search(payload)),
            "Linkedin link":  pick_group(co_linkedin.search(payload)),
        }

    speaker_header = [
        "URL",
        "Company Name",
        "Company Domain",
        "Speaker First name",
        "Speaker Last name",
        "Speaker position",
        "Topic of talk",
        "Description of talk",
        "Language",
        "Date and hour",
    ]

    company_header = [
        "URL",
        "Company Name",
        "Company Domain",
        "Email",
        "Phone Number",
        "Address",
        "Hall Number",
        "Stand Number",
        "Description",
        "Linkedin link",
    ]

    header = speaker_header if mode == "speaker" else company_header

    with open(output_csv_filename, mode='w', newline='', encoding='utf-8') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(header)

        # JSONL: czytamy linia po linii
        with open(input_jsonl_filename, 'r', encoding='utf-8') as in_file:
            for line in in_file:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue  # pomiń uszkodzone linie

                url = item.get("url", "")
                data_field = item.get("data", "")

                # data może być dict z "raw" albo stringiem/innym dict
                if isinstance(data_field, dict):
                    data_string = data_field.get("raw", "")
                    if not data_string:
                        data_string = json.dumps(data_field, ensure_ascii=False)
                else:
                    data_string = str(data_field)

                if mode == "speaker":
                    extracted = extract_speaker(data_string)
                else:
                    extracted = extract_company(data_string)

                row = [url] + [extracted.get(col, "") for col in header[1:]]
                writer.writerow(row)

    print(f"Zapisano dane do pliku {output_csv_filename}")

# Prelegenci:
extract_and_save_to_csv('extracted_data.jsonl', 'speakers.csv', mode='speaker')

# Firmy:
# extract_and_save_to_csv('extracted_data.jsonl', 'companies.csv', mode='company')
