import re
import csv
import json

def extract_and_save_to_csv(input_json_filename, output_csv_filename):
    with open(input_json_filename, 'r', encoding='utf-8') as file:
        data_json = json.load(file)

    company_name_regex = r'"Company Name":\s*"([^"]+)"'
    company_domain_regex = r'"Company Domain":\s*"([^"]+)"'
    email_number_regex = r'"Email":\s*([^,]+)'
    phone_number_regex = r'"Phone Number":\s*([^,]+)'
    address_regex = r'"Address":\s*"([^"]+)"'
    hall_number_regex = r'"Hall Number":\s*"([^"]+)"'
    stand_number_regex = r'"Stand Number":\s*"([^"]+)"'
    description_regex = r'"Description":\s*"([^"]+)"'
    linkedin_regex = r'"Linkedin link":\s*"([^"]+)"'

    def extract_data(data_string):
        company_name = re.search(company_name_regex, data_string)
        company_domain = re.search(company_domain_regex, data_string)
        email_number = re.search(email_number_regex, data_string)
        phone_number = re.search(phone_number_regex, data_string)
        address = re.search(address_regex, data_string)
        hall_number = re.search(hall_number_regex, data_string)
        stand_number = re.search(stand_number_regex, data_string)
        description = re.search(description_regex, data_string)
        linkedin = re.search(linkedin_regex, data_string)

        return {
            "Company Name": company_name.group(1) if company_name else None,
            "Company Domain": company_domain.group(1) if company_domain else None,
            "Email": email_number.group(1) if email_number else None,
            "Phone Number": phone_number.group(1) if phone_number else None,
            "Address": address.group(1) if address else None,
            "Hall Number": hall_number.group(1) if hall_number else None,
            "Stand Number": stand_number.group(1) if stand_number else None,
            "Description": description.group(1) if description else None,
            "Linkedin link": linkedin.group(1) if linkedin else None
        }

    header = ["URL", "Company Name", "Company Domain",'Email', "Phone Number", "Address", "Hall Number", "Stand Number", "Description", "Linkedin link"]

    with open(output_csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for item in data_json:
            url = item["url"]
            data = item["data"]
            extracted_data = extract_data(data)
            row = [url] + [extracted_data[key] for key in header[1:]]
            writer.writerow(row)

    print(f"Zapisano dane do pliku {output_csv_filename}")

extract_and_save_to_csv('extracted_data.json', 'excel_data.csv')
