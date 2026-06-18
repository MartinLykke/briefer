import requests

for table_id in ["EJ131", "EJEN77", "EJEN88"]:
    r = requests.get(f"https://api.statbank.dk/v1/tableinfo/{table_id}?lang=da&format=JSON", timeout=10)
    print(f"\n=== {table_id} (status {r.status_code}) ===")
    if r.status_code != 200:
        continue
    data = r.json()
    for var in data.get("variables", []):
        print(f"  Variabel: {var['id']} — {var['text']}")
        for val in var.get("values", [])[:30]:
            print(f"    {val['id']!r:20} {val['text']}")
