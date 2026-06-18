import requests, json

r = requests.get("https://api.statbank.dk/v1/tableinfo/EJDPRI?lang=da&format=JSON", timeout=10)
print("Status:", r.status_code)
data = r.json()
for var in data.get("variables", []):
    print(f"\nVariabel: {var['id']} — {var['text']}")
    for val in var.get("values", [])[:20]:
        print(f"  {val['id']!r:30} {val['text']}")
