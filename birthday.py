import os
import json as json_module
import requests
from datetime import date, timedelta

BIRTHDAYS = [
    ("Rikke", date(1997, 11, 15)),
    ("Aya",   date(2025,  5, 29)),
]

REMIND_AT_DAYS = [0, 3, 7]

DANISH_MONTHS = [
    "", "januar", "februar", "marts", "april", "maj", "juni",
    "juli", "august", "september", "oktober", "november", "december",
]


def check_birthdays():
    today = date.today()
    messages = []
    for name, bday in BIRTHDAYS:
        this_year = bday.replace(year=today.year)
        if this_year < today:
            this_year = bday.replace(year=today.year + 1)

        days_until = (this_year - today).days

        if days_until == 0:
            age = today.year - bday.year
            messages.append((f"Tillykke til {name}!", f"Det er {name}s {age}-årsdag i dag 🎂"))
        elif days_until == 3:
            messages.append(("Husk:", f"{name}s fødselsdag om 3 dage · {this_year.day}. {DANISH_MONTHS[this_year.month]}"))
        elif days_until == 7:
            messages.append(("Husk:", f"{name}s fødselsdag om en uge · {this_year.day}. {DANISH_MONTHS[this_year.month]}"))

    return messages


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
    messages = check_birthdays()
    if not messages:
        print("Ingen fødselsdagspåmindelser i dag.")
        return
    for title, body in messages:
        send_notification(title, body)
        print(f"Sendt: {title} — {body}")


if __name__ == "__main__":
    main()
