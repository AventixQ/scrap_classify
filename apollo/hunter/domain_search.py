import csv
import os
from pyhunter import PyHunter

hunter = PyHunter('c98232d4704c8830cffa582ab001957d2a526c0d')

input_file = "to_find_domain.csv"
output_file = "result_domain.csv"

if not os.path.exists(input_file):
    print(f"Plik {input_file} nie istnieje. Upewnij się, że plik znajduje się w katalogu roboczym.")
    exit()

with open(input_file, "r", encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    rows = list(reader)

with open(output_file, "w", encoding="utf-8", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, reader.fieldnames)
    writer.writeheader()

    for row in rows:
        read = row['name']
        x = hunter.domain_search(company=read,limit=1)
        email = x.get("emails", [])[0].get("value") if x.get("emails") else None
        print(read, email)
        row["email"] = email
        writer.writerow(row)
        csvfile.flush()


