import csv
import os
from hunter_email_finder import email_find_verify

input_file = "combined_unique.csv"
output_file = "combined_result.csv"

if not os.path.exists(input_file):
    print(f"Plik {input_file} nie istnieje. Upewnij się, że plik znajduje się w katalogu roboczym.")
    exit()

with open(input_file, "r", encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    rows = list(reader)
    #print(rows)

fieldnames = reader.fieldnames + ['email', 'confidence_score', 'mail_status']

with open(output_file, "w", encoding="utf-8", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        first_name = row["first_name"].strip()
        last_name = row["last_name"].strip()
        organization_name = row["organization_name"].strip()
        print(first_name, last_name, organization_name)

        if first_name and last_name and organization_name:
            email, confidence_score, mail_status = email_find_verify(organization_name, first_name, last_name)
            row["email"] = email
            row["confidence_score"] = confidence_score
            row["mail_status"] = mail_status
        else:
            row["email"] = ""
            row["confidence_score"] = ""
            row["mail_status"] = ""

        writer.writerow(row)
        csvfile.flush()
        print(f"{row['first_name']} {row['last_name']} {row['email']} done.")

print(f"Uzupełniony plik został zapisany jako {output_file}.")
