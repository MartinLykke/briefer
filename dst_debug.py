import requests

# Søg efter tabeller med "ejendom" eller "pris" i navnet
r = requests.get("https://api.statbank.dk/v1/tables?lang=da&format=JSON", timeout=10)
print("Status:", r.status_code)
tables = r.json()

keywords = ["ejendom", "bolig", "pris", "køb", "salg"]
for t in tables:
    text = (t.get("text", "") + t.get("id", "")).lower()
    if any(k in text for k in keywords):
        print(f"{t['id']:15} {t['text']}")
