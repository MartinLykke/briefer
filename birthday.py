import os
import json as json_module
import requests
from datetime import date, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BIRTHDAYS = [
    ("Rikke",  date(1997, 11, 15)),
    ("Aya",    date(2025,  5, 29)),
    ("Farmor", date(1900,  9,  1)),  # år ukendt
    ("Farfar", date(1900,  5, 25)),  # år ukendt
]

DANISH_MONTHS = [
    "", "januar", "februar", "marts", "april", "maj", "juni",
    "juli", "august", "september", "oktober", "november", "december",
]


def build_tasks_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("tasks", "v1", credentials=creds)


def create_gift_task(tasks_service, name, birthday):
    due_date = birthday - timedelta(days=3)
    tasks_service.tasks().insert(
        tasklist="@default",
        body={
            "title": f"Køb gave til {name}",
            "due": due_date.strftime("%Y-%m-%dT00:00:00.000Z"),
        },
    ).execute()
    print(f"Oprettet task: Køb gave til {name} (forfald {due_date})")


def check_birthdays(tasks_service):
    today = date.today()
    messages = []

    for name, bday in BIRTHDAYS:
        this_year = bday.replace(year=today.year)
        if this_year < today:
            this_year = bday.replace(year=today.year + 1)

        days_until = (this_year - today).days

        if days_until == 0:
            if bday.year != 1900:
                age = today.year - bday.year
                body = f"Det er {name}s {age}-årsdag i dag 🎂"
            else:
                body = f"Det er {name}s fødselsdag i dag 🎂"
            messages.append((f"Tillykke til {name}!", body))

        elif days_until == 3:
            messages.append(("Husk:", f"{name}s fødselsdag om 3 dage · {this_year.day}. {DANISH_MONTHS[this_year.month]}"))

        elif days_until == 7:
            messages.append(("Husk:", f"{name}s fødselsdag om en uge · {this_year.day}. {DANISH_MONTHS[this_year.month]}"))

        elif days_until == 14:
            create_gift_task(tasks_service, name, this_year)

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
    tasks_service = build_tasks_service()
    messages = check_birthdays(tasks_service)

    if not messages:
        print("Ingen fødselsdagspåmindelser i dag.")
        return

    for title, body in messages:
        send_notification(title, body)
        print(f"Sendt: {title} — {body}")


if __name__ == "__main__":
    main()
