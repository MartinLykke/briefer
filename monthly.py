import os
import io
import csv
import json as json_module
import requests



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

    sorted_months = sorted(rows.keys())
    latest_month = sorted_months[-1]
    latest_price = rows[latest_month]

    year, num = latest_month.split("M")
    same_month_last_year = f"{int(year) - 1}M{num}"
    price_last_year = rows.get(same_month_last_year)

    return latest_month, latest_price, price_last_year


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
    latest_month, latest, price_last_year = get_house_prices()

    price_mio = latest / 1000
    lines = [f"Enfamiliehuse (Reg. Hoved.): {price_mio:.1f} mio. kr"]

    if price_last_year:
        pct = round((latest - price_last_year) / price_last_year * 100, 1)
        sign = "+" if pct >= 0 else ""
        last_year_mio = price_last_year / 1000
        lines.append(f"År-til-år: {sign}{pct}% (fra {last_year_mio:.1f} mio.)")

    lines.append(f"Data: {format_month(latest_month)}")

    body = "\n".join(lines)
    send_notification("Huspriser Birkerød", body)
    print(f"Sendt:\n{body}")


if __name__ == "__main__":
    main()
