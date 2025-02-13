import pandas as pd
import re

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_regex, str(email)))

df = pd.read_csv('all_berlin.csv', sep=';')

df = df.drop_duplicates(subset='e-mail')

df = df[df['e-mail'].apply(is_valid_email)]

df.to_csv('all_berlin_clean.csv', index=False)

max_rows = 99999
for i, chunk in enumerate(range(0, len(df), max_rows)):
    chunk_df = df.iloc[chunk:chunk + max_rows]
    chunk_df.to_csv(f'all_berlin_clean_part_{i + 1}.csv', index=False)

print("Duplikaty zostały usunięte, niepoprawne e-maile odfiltrowane, a plik został podzielony na części.")

print("Duplikaty zostały usunięte, a wynik zapisano w pliku.")
