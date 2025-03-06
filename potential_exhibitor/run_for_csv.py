import csv
from llm_deepseek import evaluate_exhibitor
from scrap import scrape_deep_description
import json


def evaluate_alexa_rank(alexa_rank: str) -> int:
    """Ocena Alexa Rank w skali 0-10"""
    try:
        rank = int(alexa_rank.replace(',', ''))
        if rank <= 10000: return 10
        if rank <= 100000: return 8
        if rank <= 500000: return 6
        if rank <= 1000000: return 4
        return 2
    except:
        return 0  # Dla braku danych lub błędów


def evaluate_revenue(revenue: int) -> int:
    """Ocena przychodów w skali 0-10"""
    try:
        revenue = int(revenue)
        if revenue >= 10000000: return 10
        if revenue >= 1000000: return 8
        if revenue >= 500000: return 5
        return 3
    except:
        return 0  # Dla braku danych lub błędów

def is_scraping_failed(reasons: str) -> bool:
    """Sprawdza, czy reasons zawiera oznaczenia błędów scrapingu."""
    scraping_errors = {"access_denied", "no_description_available", "access_blocked", "no_description_provided", "error_message", "no_relevant_description_provided", "no_description"}
    return any(error in reasons.lower() for error in scraping_errors)


def process_csv(input_path: str, output_path: str):
    """Przetwarza plik CSV i zapisuje wyniki."""
    with (
        open(input_path, 'r', encoding='utf-8') as infile,
        open(output_path, 'w', encoding='utf-8', newline='') as outfile
    ):
        reader = csv.DictReader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter=';')

        # Nowe nagłówki z dodatkowymi kolumnami
        writer.writerow([
            'domain',
            'llm_score',
            'alexa_score',
            'revenue',
            'total_score',
            'reasons',
            'exhibitor_type'
        ])
        outfile.flush()

        for row in reader:
            try:
                domain = row['domain']
                description = scrape_deep_description(domain)
                if description == "":
                    llm_result = '''
                    {
                      "score": -1,
                      "reasons": ["no_description"],
                      "exhibitor_type": ""
                    }
                    '''
                    llm_result = json.loads(llm_result)
                else:
                    # Pobierz i ocenij dane
                    llm_result = evaluate_exhibitor(
                        domain=domain,
                        description=description
                    )
                reasons = llm_result.get('reasons', [])
                reasons_str = ",".join(reasons).replace(" ", "_")

                if is_scraping_failed(reasons_str):
                    llm_score = -1
                else:
                    llm_score = llm_result.get('score', 0)

                alexa_score = evaluate_alexa_rank(row.get('alexa_rank', ''))
                revenue_score = evaluate_revenue(row.get('revenue', ''))

                sufix_points = 60

                if alexa_score > 0: sufix_points += 10
                if revenue_score > 0: sufix_points += 10
                if llm_score == -1: total_score = -1
                else:
                    total_score = llm_score + alexa_score + revenue_score
                    total_score = round(total_score * 100 / sufix_points,2)

                # Formatowanie reasons
                reasons_str = ",".join(llm_result.get('reasons', [])).replace(" ", "_")

                writer.writerow([
                    domain,
                    llm_score,
                    alexa_score,
                    revenue_score,
                    total_score,
                    reasons_str,
                    llm_result.get('exhibitor_type', 'N/A')
                ])
                print(f"Done for {domain}")
                outfile.flush()

            except Exception as e:
                print(f"Error for {domain}: {str(e)}")


if __name__ == "__main__":
    process_csv('input.csv', 'output.csv')