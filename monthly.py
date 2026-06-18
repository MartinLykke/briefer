import os
import json as json_module
import requests
from datetime import datetime

DST_API = "https://api.statbank.dk/v1/data"
BASELINE_QUARTER = "2025K4"  # Nærmeste kvartal til 01-01-2026


def get_house_prices():
    payload = {
        "table": "EJDPRI",
        "format": "JSON",
        "variables": [
            {"code": "EJENDOMSTYPE", "values": ["Parcel/rækkehuse"]},
            {"code": "OMRAADE", "values": ["Rudersdal"]},
            {"code": "Tid", "values": ["*"]},
        ],
    }
    r = requests.post(DST_API, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()

    rows = {row["key"][2]: int(row["value"]) for row in data["data"] if row["value"] not in (None, "", ".")}

    sorted_quarters = sorted(rows.keys())
    latest_quarter = sorted_quarters[-1]
    latest_price = rows[latest_quarter]

    baseline_price = rows.get(BASELINE_QUARTER)

    return latest_quarter, latest_price, baseline_price


def send_notification(title, body):
    topic = os.environ["NTFY_TOPIC"]
    payload = json_module.dumps(
        {"topic": topic, "title": title, "message": body},
        ensure_ascii=False,
    ).encode("utf-8")
    requests.post(
        "https://ntfy.sh/",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=10,
    )


def main():
    quarter, latest, baseline = get_house_prices()

    quarter_pretty = quarter.replace("K", ". kvartal ")

    if baseline:
        pct = round((latest - baseline) / baseline * 100, 1)
        sign = "+" if pct >= 0 else ""
        body = (
            f"Gennemsnitspris (Rudersdal): {latest:,} kr/m²\n"
            f"Ændring siden jan 2026: {sign}{pct}%\n"
            f"Seneste data: {quarter_pretty}"
        ).replace(",", ".")
    else:
        body = (
            f"Gennemsnitspris (Rudersdal): {latest:,} kr/m²\n"
            f"Seneste data: {quarter_pretty}"
        ).replace(",", ".")

    send_notification("Huspriser Birkerød", body)
    print(f"Sendt:\n{body}")


if __name__ == "__main__":
    main()
