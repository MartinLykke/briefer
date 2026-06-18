import os
import io
import csv
import json as json_module
import requests

BASELINE_MONTH = "2026M01"


def get_house_prices():
    payload = {
        "table": "EJ131",
        "format": "CSV",
        "variables": [
            {"code": "REGION", "values": ["084"]},
            {"code": "EJENDOMSKATE", "values": ["0111"]},
            {"code": "BNØGLE", "values": ["3"]},
            {"code": "Tid", "values": ["*"]},
        ],
    }
    r = requests.post("https://api.statbank.dk/v1/data", json=payload, timeout=30)
    if not r.ok:
        print("DST fejl:", r.status_code, r.text)
    r.raise_for_status()

    reader = csv.DictReader(io.StringIO(r.text), delimiter=";")
    rows = {}
    for row in reader:
        tid = row.get("TID", row.get("tid", ""))
        val = row.get("INDHOLD", row.get("indhold", "")).strip().replace(".", "")
        if tid and val and val not in ("", "."):
            try:
                rows[tid] = int(val)
            except ValueError:
                pass

    latest_month = sorted(rows.keys())[-1]
    latest_price = rows[latest_month]
    baseline_price = rows.get(BASELINE_MONTH)

    return latest_month, latest_price, baseline_price


def format_month(m):
    months = ["jan", "feb", "mar", "apr", "maj", "jun",
              "jul", "aug", "sep", "okt", "nov", "dec"]
    year, num = m.split("M")
    return f"{months[int(num) - 1]} {year}"


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
    latest_month, latest, baseline = get_house_prices()

    price_mio = latest / 1000
    lines = [f"Enfamiliehuse (Region Hoved.): {price_mio:.1f} mio. kr"]

    if baseline:
        pct = round((latest - baseline) / baseline * 100, 1)
        sign = "+" if pct >= 0 else ""
        lines.append(f"Siden jan 2026: {sign}{pct}%")

    lines.append(f"Seneste data: {format_month(latest_month)}")

    body = "\n".join(lines)
    send_notification("Huspriser Birkerød", body)
    print(f"Sendt:\n{body}")


if __name__ == "__main__":
    main()
